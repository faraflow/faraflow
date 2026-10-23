<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { page } from '$app/stores'
    import { onMount, onDestroy } from 'svelte'
    import Header from '$lib/components/Header.svelte'
    import LoadingSpinner from '$lib/components/LoadingSpinner.svelte'
    import TraceCanvas from '$lib/components/canvas/TraceCanvas.svelte'
    import { nodeTypesStore } from '$lib/stores/nodeTypes.svelte'
    import { getRunStatus, getRunStatusLight } from '$lib/utils/api'
    import { rolloutWorkflowDefinition } from '$lib/utils/subworkflowUtils'
    import { fetchWorkflowRuns, executionState } from '$lib/actions/workflowExecution.svelte'
    import type { RunResponse } from '$lib/types/api_types/runSchemas'
    import type { TaskResponse } from '$lib/types/api_types/taskSchemas'
    import type { WorkflowDefinition } from '$lib/types/api_types/workflowSchemas'

    const runId = $derived($page.params.id)

    let runData = $state<RunResponse | null>(null)
    let workflowId = $state<string | null>(null)
    let workflowData = $state<{ name: string; definition: WorkflowDefinition } | null>(null)
    let tasksData = $state<TaskResponse[]>([])
    let handleDownloadImage = $state<(() => void) | undefined>(undefined)
    let error = $state<string | null>(null)
    let traceInterval: ReturnType<typeof setInterval> | null = null
    let lastRefreshVersion = -1

    onMount(() => {
        traceInterval = setInterval(refreshTasks, 5000)
    })

    onDestroy(() => {
        if (traceInterval) {
            clearInterval(traceInterval)
            traceInterval = null
        }
    })

    // Re-run whenever runId changes — SvelteKit updates $page.params without
    // remounting the component, so onMount alone is not enough.
    $effect(() => {
        const id = runId
        runData = null
        workflowData = null
        tasksData = []
        error = null
        nodeTypesStore.fetch().then(() => loadRun())
    })

    async function loadRun() {
        try {
            const data = await getRunStatus(runId)
            workflowId = data.workflow_id
            runData = data
            executionState.currentRunId = runId
            fetchWorkflowRuns(data.workflow_id)

            if (data.workflow_version?.definition) {
                const { rolledOutDefinition } = data.tasks?.length
                    ? rolloutWorkflowDefinition({
                          workflowDefinition: data.workflow_version.definition,
                          tasks: data.tasks,
                      })
                    : { rolledOutDefinition: data.workflow_version.definition }

                workflowData = {
                    name: data.workflow_version.name || 'Workflow',
                    definition: rolledOutDefinition,
                }

                if (data.tasks) {
                    tasksData = data.tasks
                }
            } else {
                error = `Run ${runId} has no workflow definition`
            }
        } catch (err) {
            console.error('Error fetching run:', err)
            error = `Failed to load run ${runId}: ${err instanceof Error ? err.message : String(err)}`
        }
    }

    async function refreshTasks() {
        try {
            // Heartbeat-gated: only re-pull the full task payload when the run changed.
            const light = await getRunStatusLight(runId)
            if (light.version === lastRefreshVersion) return
            lastRefreshVersion = light.version
            const data = await getRunStatus(runId)
            if (data.tasks) {
                tasksData = data.tasks
            }
        } catch (err) {
            console.error('Error refreshing trace tasks:', err)
        }
    }
</script>

<svelte:head>
    <title>Trace {runId} - Faraflow</title>
</svelte:head>

<div class="h-screen flex flex-col overflow-hidden">
    <Header
        activePage="trace"
        associatedWorkflowId={workflowId || undefined}
        {runId}
        {handleDownloadImage}
    />
    <div class="flex-1 min-h-0 overflow-hidden">
        {#if error}
            <div class="flex items-center justify-center h-full text-destructive">{error}</div>
        {:else if !workflowData}
            <LoadingSpinner />
        {:else}
            <TraceCanvas
                {workflowData}
                workflowID={workflowId}
                {tasksData}
                onDownloadImageInit={(handler) => (handleDownloadImage = handler)}
                projectName={workflowData.name}
                runId={runData?.id}
                initialInputs={runData?.initial_inputs ?? {}}
            />
        {/if}
    </div>
</div>
