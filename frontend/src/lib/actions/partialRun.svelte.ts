// Copyright 2026 Alokin LLC
// SPDX-License-Identifier: FCL-1.0-ALv2
import { flowStore } from '$lib/stores/flow.svelte'
import { runPartialWorkflow } from '$lib/utils/api'
import { executionState, updateWorkflowStatus, fetchWorkflowRuns } from '$lib/actions/workflowExecution.svelte'

/**
 * Run a partial workflow up to (and including) the given node.
 * Uses existing input-node run data if present; otherwise opens the RunModal.
 *
 * The backend always returns a RunResponseSchema. For completed/failed runs we
 * process the tasks directly (synchronous path). For paused runs we switch into
 * polling mode so the HumanInterventionNode flow keeps working.
 */
export async function partialRun(
    workflowId: string,
    nodeId: string,
    nodeTitle: string
): Promise<void> {
    const nodes = flowStore.nodes

    // Collect existing node outputs as partial outputs (skip the target node)
    const partialOutputs: Record<string, any> = {}
    nodes.forEach((n) => {
        if (n.id !== nodeId && n.data?.run) {
            partialOutputs[n.id] = n.data.run
        }
    })

    // Determine initial inputs — prefer run data already on the input node;
    // if absent, open the modal so the user can provide/confirm inputs.
    let initialInputs: Record<string, any> = {}

    const inputNode = nodes.find((n) => n.type === 'InputNode')
    const inputNodeRunData = inputNode?.data?.run as Record<string, any> | undefined
    const hasInputData = inputNodeRunData && Object.keys(inputNodeRunData).length > 0

    if (hasInputData && inputNode) {
        initialInputs = { [inputNode.id]: inputNodeRunData }
    } else {
        flowStore.setRunModalOpen(true)
        return
    }

    try {
        // Backend now runs partial workflows as background tasks and returns
        // the new run ID immediately — switch to polling like a normal run.
        const data = await runPartialWorkflow(
            workflowId,
            initialInputs,
            partialOutputs,
            executionState.currentRunId,
            [nodeId]
        )

        if (!data?.id) return

        executionState.currentRunId = data.id
        executionState.isRunning = true
        updateWorkflowStatus(data.id, {
            onAlert: () => {},
        })
        fetchWorkflowRuns()
    } catch (err: any) {
        console.error('Error during partial run:', err)
        flowStore.updateNodeDataOnly(nodeId, { taskStatus: 'FAILED', error: err?.message ?? 'Unknown error' })
    }
}
