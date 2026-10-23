// Copyright 2026 Alokin LLC
// SPDX-License-Identifier: FCL-1.0-ALv2
import { flowStore } from '$lib/stores/flow.svelte'
import {
    startRun,
    getRunStatus,
    getRunStatusLight,
    getWorkflowRuns,
    runPartialWorkflow,
    validateGoogleAccessToken,
} from '$lib/utils/api'
import type { RunListItem } from '$lib/types/api_types/runSchemas'

type AlertColor = 'default' | 'success' | 'warning' | 'danger'

interface WorkflowExecutionOptions {
    onAlert: (message: string, color: AlertColor) => void
}

// ---------------------------------------------------------------------------
// Module-level reactive state — wrapped in an object so property mutations
// are valid (Svelte 5 disallows exporting reassignable $state bindings)
// ---------------------------------------------------------------------------

export const executionState = $state({
    isRunning: false,
    completionPercentage: 0,
    workflowRuns: [] as RunListItem[],
    isUpdatingStatus: false,
    currentRunId: null as string | null,
    loadedRunStatus: null as string | null,  // status of the currently loaded run on canvas
})

// Internal polling interval handle (active run — 1 s)
let statusIntervalHandle: ReturnType<typeof setInterval> | null = null

// Background trace polling handle (5 s, fires only when !isRunning)
let tracePollingHandle: ReturnType<typeof setInterval> | null = null

// Sidebar-only poller for RUNNING/PENDING runs in RunsOverviewSidebar (4 s)
let runsOverviewPollingHandle: ReturnType<typeof setInterval> | null = null

// Last options used — retained so polling can be restarted after a pause action
let lastOptions: WorkflowExecutionOptions | null = null

// When true, the "stop on paused task" logic is suppressed so the interval
// survives the first few polls after a pause action is submitted (the backend
// may still report PAUSED briefly before transitioning to RUNNING).
let isResuming = false

// Last run `version` seen by each poller. Each tick hits the lightweight
// heartbeat first and only fetches the heavy /status/ (with tasks) when the
// version changed — so a long-running node yields tiny polls instead of
// re-downloading the full task payload every interval. Reset per run start.
let lastPolledVersion = -1
let lastTracePolledVersion = -1

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function clearStatusInterval() {
    if (statusIntervalHandle !== null) {
        clearInterval(statusIntervalHandle)
        statusIntervalHandle = null
    }
}

function clearTraceInterval() {
    if (tracePollingHandle !== null) {
        clearInterval(tracePollingHandle)
        tracePollingHandle = null
    }
}

function clearRunsOverviewInterval() {
    if (runsOverviewPollingHandle !== null) {
        clearInterval(runsOverviewPollingHandle)
        runsOverviewPollingHandle = null
    }
}

function hasActiveRuns(): boolean {
    return executionState.workflowRuns.some(r => {
        const s = r.status?.toLowerCase()
        return s === 'running' || s === 'pending'
    })
}

// ---------------------------------------------------------------------------
// applyTasksToNodes — shared helper used by both pollers
// ---------------------------------------------------------------------------

// Mirrors Python's _field_name() in ask_node.py
function askModelSlug(model: string): string {
    return model.split('/').pop()!.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '')
}
function askFieldId(prefix: string, model: string): string {
    return `${prefix}_${askModelSlug(model)}`
}

function applyTasksToNodes(tasks: any[]): void {
    const nodes = flowStore.nodes

    // Index all tasks by node_id so we can look up inner subworkflow task errors
    const taskByNodeId: Record<string, any> = {}
    tasks.forEach((task: any) => { taskByNodeId[task.node_id] = task })

    tasks.forEach((task: any) => {
        const nodeId = task.node_id
        let node = nodes.find((n) => n.id === nodeId || n.data?.title === nodeId)
        if (!node) {
            const correspondingNodeId = Object.keys(flowStore.nodeConfigs).find(
                (key) => flowStore.nodeConfigs[key]?.title === nodeId
            )
            if (correspondingNodeId) {
                node = nodes.find((n) => n.id === correspondingNodeId)
            }
        }

        if (task.subworkflow_output) {
            Object.entries(task.subworkflow_output).forEach(([subNodeId, outputs]) => {
                const subNode = nodes.find(
                    (n) => n.id === subNodeId || n.data?.title === subNodeId
                )
                if (subNode) {
                    flowStore.updateNodeDataOnly(subNode.id, {
                        run: outputs,
                        taskStatus: 'COMPLETED',
                    })
                }
            })
        }

        if (node) {
            // For AskNodes, build run output from subworkflow_output filtered to model field IDs,
            // and collect errors from inner subworkflow tasks
            let subworkflow_errors: Record<string, string> | null = null
            let runData: Record<string, any> = task.outputs ?? {}

            if (node.type === 'AskNode') {
                const config = flowStore.nodeConfigs[node.id]
                const prefix: string = config?.output_key_prefix ?? 'ask'
                const models: Array<{ model: string }> = config?.models ?? []
                const errors: Record<string, string> = {}
                const successOutputs: Record<string, any> = {}

                for (const m of models) {
                    const fid = askFieldId(prefix, m.model)
                    const innerTask = taskByNodeId[fid]
                    if (innerTask?.error) {
                        errors[fid] = innerTask.error
                    } else if (task.subworkflow_output?.[fid] != null) {
                        successOutputs[fid] = task.subworkflow_output[fid]
                    }
                }

                if (Object.keys(errors).length > 0) subworkflow_errors = errors
                if (Object.keys(successOutputs).length > 0) runData = successOutputs
            }

            const hasSubworkflowErrors = subworkflow_errors !== null && Object.keys(subworkflow_errors).length > 0
            flowStore.updateNodeDataOnly(node.id, {
                run: runData,
                error: task.error ?? null,
                taskStatus: hasSubworkflowErrors ? 'FAILED' : task.status,
                subworkflow_output: task.subworkflow_output ?? null,
                ...(subworkflow_errors !== null ? { subworkflow_errors } : {}),
            })
        }
    })
}

// ---------------------------------------------------------------------------
// updateWorkflowStatus — poll run status and update node data
// ---------------------------------------------------------------------------

export async function updateWorkflowStatus(
    runID: string,
    options: WorkflowExecutionOptions
): Promise<void> {
    lastOptions = options
    clearStatusInterval()
    lastPolledVersion = -1

    statusIntervalHandle = setInterval(async () => {
        try {
            // Cheap heartbeat first; skip the heavy fetch if nothing changed.
            const light = await getRunStatusLight(runID)
            if (light.version === lastPolledVersion) return
            lastPolledVersion = light.version

            const statusResponse = await getRunStatus(runID)
            const tasks = statusResponse.tasks ?? []

            if (statusResponse.percentage_complete !== undefined) {
                executionState.completionPercentage = statusResponse.percentage_complete
            }

            const hasPausedTask = tasks.some((t: any) => t.status === 'PAUSED')
            const hasRunningTask = tasks.some((t: any) => t.status === 'RUNNING')
            const hasFailedTask = tasks.some((t: any) => t.status === 'FAILED')
            const hasPendingTask = tasks.some((t: any) => t.status === 'PENDING')

            applyTasksToNodes(tasks)

            // All tasks finished (no running, pending, or paused) — workflow is done
            // regardless of what run.status says (it may lag behind, e.g. still RUNNING
            // while the background resume task hasn't committed COMPLETED yet)
            const allTasksDone = tasks.length > 0 && !hasRunningTask && !hasPendingTask && !hasPausedTask

            if (hasPausedTask) {
                executionState.isRunning = true
                if (hasRunningTask) {
                    // Backend has picked up the action and is running again
                    isResuming = false
                } else if (!isResuming) {
                    // Genuinely paused with no running tasks and not mid-resume
                    options.onAlert('Workflow run paused for human intervention.', 'warning')
                    clearStatusInterval()
                }
                // If isResuming && !hasRunningTask: still waiting for backend — keep polling
            } else if (allTasksDone || statusResponse.status !== 'RUNNING') {
                isResuming = false
                executionState.isRunning = false
                executionState.completionPercentage = 0
                clearStatusInterval()

                // Immediately patch the local run status so the sidebar shows the
                // correct state before fetchWorkflowRuns() returns (the backend run
                // record can lag behind the task records by a few seconds).
                const immediateStatus = hasFailedTask ? 'FAILED' : 'COMPLETED'
                executionState.loadedRunStatus = immediateStatus
                executionState.workflowRuns = executionState.workflowRuns.map((r) =>
                    r.id === runID ? { ...r, status: immediateStatus } : r
                )

                fetchWorkflowRuns()

                // Ensure no nodes are left stuck in RUNNING/PENDING after the run ends.
                // This handles cases where the backend task list is empty or the task
                // node_id lookup failed (e.g. a Claude model error that terminates the run
                // before all task records are written).
                const runFailed = hasFailedTask || statusResponse.status === 'FAILED'
                flowStore.nodes.forEach((n) => {
                    const status = n.data?.taskStatus
                    if (status === 'RUNNING' || (runFailed && status === 'PENDING')) {
                        flowStore.updateNodeDataOnly(n.id, {
                            taskStatus: runFailed ? 'FAILED' : 'COMPLETED',
                        })
                    }
                })

                if (hasFailedTask) {
                    if (tasks.some((t: any) => t.status === 'COMPLETED')) {
                        options.onAlert('Workflow ran with some failed tasks.', 'warning')
                    } else {
                        options.onAlert('Workflow run failed.', 'danger')
                    }
                } else if (!hasPausedTask) {
                    options.onAlert('Workflow run completed.', 'success')
                }
            }

            // Only use this as a fallback stop if we have actual task data confirming
            // the run is done. Without this guard, an empty tasks array on the first
            // poll (tasks not yet written to DB) would kill the interval while the
            // run is still RUNNING in the backend.
            if (!isResuming && !hasRunningTask && (!hasPendingTask || hasPausedTask) &&
                (tasks.length > 0 || statusResponse.status !== 'RUNNING')) {
                clearStatusInterval()
            }
        } catch (err) {
            console.error('Error fetching workflow status:', err)
            // Unstick any nodes left in RUNNING state if polling itself failed.
            flowStore.nodes.forEach((n) => {
                if (n.data?.taskStatus === 'RUNNING') {
                    flowStore.updateNodeDataOnly(n.id, { taskStatus: 'FAILED', error: 'Status polling failed' })
                }
            })
            clearStatusInterval()
        }
    }, 1000)
}

// ---------------------------------------------------------------------------
// executeWorkflow
// ---------------------------------------------------------------------------

export async function executeWorkflow(
    inputValues: Record<string, any>,
    options: WorkflowExecutionOptions,
    parentRunId: string | null = null
): Promise<void> {
    const workflowId = flowStore.workflowID
    if (!workflowId) return

    const hasGoogleSheetsReadNode = flowStore.nodes.some((n) => n.type === 'GoogleSheetsReadNode')
    if (hasGoogleSheetsReadNode) {
        const response = await validateGoogleAccessToken()
        if (!response.is_valid) {
            window.open(`${window.location.origin}/google/auth`, '_blank')
            return
        }
    }

    try {
        flowStore.resetRun()
        executionState.isRunning = true
        executionState.loadedRunStatus = 'RUNNING'
        options.onAlert('Starting workflow run...', 'default')
        const result = await startRun(workflowId, inputValues, parentRunId, 'interactive')
        executionState.currentRunId = result.id
        await fetchWorkflowRuns()
        updateWorkflowStatus(result.id, options)
    } catch (err: any) {
        executionState.isRunning = false
        console.error('Error starting workflow run:', err)
        const errorDetail = err?.response?.data?.detail ?? err?.message ?? ''
        try {
            const parsed = JSON.parse(errorDetail)
            if (parsed.type === 'model_provider_error') {
                const colorMap: Record<string, AlertColor> = {
                    overloaded: 'warning',
                    rate_limit: 'warning',
                    context_length: 'danger',
                    auth: 'danger',
                    service_unavailable: 'warning',
                    unknown: 'danger',
                }
                const color = colorMap[parsed.error_type] ?? 'danger'
                options.onAlert(
                    `${(parsed.provider ?? '').toUpperCase()} Model Error: ${parsed.message}`,
                    color
                )
                return
            }
        } catch {
            // Not a JSON error
        }
        options.onAlert('Error starting workflow run.', 'danger')
    }
}

// ---------------------------------------------------------------------------
// stopWorkflow
// ---------------------------------------------------------------------------

export function startRunsOverviewPolling(): void {
    if (runsOverviewPollingHandle !== null) return // already running
    if (!hasActiveRuns()) return                   // nothing to poll

    runsOverviewPollingHandle = setInterval(async () => {
        if (executionState.isRunning) return       // active 1 s poller already handles it
        await updateRunStatuses()
        if (!hasActiveRuns()) {
            clearRunsOverviewInterval()
        }
    }, 4000)
}

export function stopRunsOverviewPolling(): void {
    clearRunsOverviewInterval()
}

export function stopWorkflow(options: WorkflowExecutionOptions): void {
    executionState.isRunning = false
    executionState.completionPercentage = 0
    clearStatusInterval()
    options.onAlert('Workflow run stopped.', 'warning')
}

// ---------------------------------------------------------------------------
// resumeWorkflowPolling — restart polling after a human pause action
// ---------------------------------------------------------------------------

export function resumeWorkflowPolling(): void {
    if (!executionState.currentRunId || !lastOptions) return
    isResuming = true
    executionState.isRunning = true
    updateWorkflowStatus(executionState.currentRunId, lastOptions)
}

// ---------------------------------------------------------------------------
// startTracePolling / stopTracePolling — keep a displayed trace fresh
// when another browser session updates it (e.g. via partial run).
// Fires every 5 s, but no-ops while an active run is already polling.
// ---------------------------------------------------------------------------

export function startTracePolling(): void {
    clearTraceInterval()
    lastTracePolledVersion = -1
    tracePollingHandle = setInterval(async () => {
        if (!executionState.currentRunId || executionState.isRunning) return
        try {
            // Heartbeat-gated: only re-pull tasks when the run actually changed.
            const light = await getRunStatusLight(executionState.currentRunId)
            if (light.version === lastTracePolledVersion) return
            lastTracePolledVersion = light.version
            const statusResponse = await getRunStatus(executionState.currentRunId)
            applyTasksToNodes(statusResponse.tasks ?? [])
        } catch (err) {
            console.error('Error polling trace:', err)
        }
    }, 5000)
}

export function stopTracePolling(): void {
    clearTraceInterval()
}

// ---------------------------------------------------------------------------
// loadRunIntoCanvas — apply a stored run's results to canvas nodes
// ---------------------------------------------------------------------------

export async function loadRunIntoCanvas(
    runId: string,
    options?: WorkflowExecutionOptions
): Promise<void> {
    // Stop any in-flight status polling immediately. Without this, the old run's
    // 1-second poller keeps calling applyTasksToNodes and overwrites the canvas
    // state of the newly-loaded run until the old run finishes.
    clearStatusInterval()
    isResuming = false
    executionState.isRunning = false
    executionState.completionPercentage = 0

    try {
        const statusResponse = await getRunStatus(runId)
        executionState.currentRunId = runId
        executionState.loadedRunStatus = statusResponse.status?.toUpperCase() ?? null

        const isActive = statusResponse.status === 'RUNNING' || statusResponse.status === 'PAUSED'
        if (isActive && options) {
            executionState.isRunning = true
            updateWorkflowStatus(runId, options)
        } else {
            applyTasksToNodes(statusResponse.tasks ?? [])
        }
    } catch (err) {
        console.error('Error loading run into canvas:', err)
    }
}

// ---------------------------------------------------------------------------
// fetchWorkflowRuns
// ---------------------------------------------------------------------------

export async function fetchWorkflowRuns(workflowId?: string): Promise<void> {
    const id = workflowId ?? flowStore.workflowID
    if (!id) return
    try {
        executionState.workflowRuns = await getWorkflowRuns(id)
        startRunsOverviewPolling()
    } catch (err) {
        console.error('Error fetching workflow runs:', err)
    }
}

// ---------------------------------------------------------------------------
// updateRunStatuses — refresh statuses for all in-progress runs
// ---------------------------------------------------------------------------

export async function updateRunStatuses(): Promise<void> {
    const workflowId = flowStore.workflowID
    if (!workflowId) return
    executionState.isUpdatingStatus = true
    try {
        const latestRuns = await getWorkflowRuns(workflowId)
        executionState.workflowRuns = latestRuns

        const updated = await Promise.all(
            latestRuns.map(async (run) => {
                const s = run.status?.toLowerCase()
                if (s === 'running' || s === 'pending') {
                    // Only `status` is used here — the lightweight heartbeat suffices.
                    const status = await getRunStatusLight(run.id)
                    return { ...run, status: status.status }
                }
                return run
            })
        )
        executionState.workflowRuns = updated
    } catch (err) {
        console.error('Error updating run statuses:', err)
    } finally {
        executionState.isUpdatingStatus = false
    }
}

// ---------------------------------------------------------------------------
// rerunWorkflow — re-execute the currently loaded run with its original inputs
// ---------------------------------------------------------------------------

export async function rerunWorkflow(options: WorkflowExecutionOptions): Promise<void> {
    const run = executionState.workflowRuns.find(r => r.id === executionState.currentRunId)
    if (!run?.initial_inputs) return
    await executeWorkflow(run.initial_inputs, options, executionState.currentRunId)
}

// ---------------------------------------------------------------------------
// continueFromNode — continue the currently loaded run, reusing completed node
// outputs as a cache. With nodeId = null the backend auto-detects all
// non-completed nodes and re-runs them. With a nodeId, that node and all its
// descendants re-run (even if completed); everything else stays cached.
// ---------------------------------------------------------------------------

export async function continueFromNode(
    nodeId: string | null,
    options: WorkflowExecutionOptions
): Promise<void> {
    const workflowId = flowStore.workflowID
    if (!workflowId || !executionState.currentRunId) return

    // Get initial inputs from the current loaded run, fall back to InputNode data.
    const currentRun = executionState.workflowRuns.find(r => r.id === executionState.currentRunId)
    let initialInputs: Record<string, any> = currentRun?.initial_inputs ?? {}
    if (Object.keys(initialInputs).length === 0) {
        const inputNode = flowStore.nodes.find(n => n.type === 'InputNode')
        if (inputNode?.data?.run) initialInputs = { [inputNode.id]: inputNode.data.run }
    }
    if (Object.keys(initialInputs).length === 0) {
        flowStore.setRunModalOpen(true)
        return
    }

    executionState.isRunning = true
    executionState.loadedRunStatus = 'RUNNING'
    options.onAlert(nodeId ? 'Re-running node and descendants…' : 'Continuing from unfinished nodes…', 'default')

    try {
        // Backend starts the partial run as a background task and returns the new
        // run ID immediately. We switch to polling (same as executeWorkflow) so the
        // canvas updates in real time while the workflow executes.
        const data = await runPartialWorkflow(
            workflowId,
            initialInputs,
            null,
            executionState.currentRunId,
            null,
            nodeId
        )

        if (!data?.id) { executionState.isRunning = false; return }

        executionState.currentRunId = data.id
        await fetchWorkflowRuns()
        updateWorkflowStatus(data.id, options)
    } catch (err: any) {
        executionState.isRunning = false
        executionState.loadedRunStatus = null
        console.error('Error continuing workflow:', err)
        options.onAlert('Error continuing workflow.', 'danger')
    }
}
