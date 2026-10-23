<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { page } from '$app/stores'
    import { onMount } from 'svelte'
    import Header from '$lib/components/Header.svelte'
    import LoadingSpinner from '$lib/components/LoadingSpinner.svelte'
    import TraceTable from '$lib/components/TraceTable.svelte'
    import { getWorkflow } from '$lib/utils/api'

    const workflowId = $derived($page.params.id)

    let workflowName = $state('')
    let isLoading = $state(true)
    let error = $state<string | null>(null)

    onMount(async () => {
        try {
            const wf = await getWorkflow(workflowId)
            workflowName = wf.name
        } catch (err) {
            console.error('Error fetching workflow:', err)
            error = 'Failed to load workflow'
        } finally {
            isLoading = false
        }
    })
</script>

<svelte:head>
    <title>{workflowName ? `${workflowName} - Runs` : 'Flow Runs'} - Faraflow</title>
</svelte:head>

<div style="height: 100vh; display: flex; flex-direction: column;">
    <Header activePage="runs" associatedWorkflowId={workflowId} />
    <div class="max-w-7xl mx-auto px-4 py-6 flex-grow w-full overflow-auto">
        {#if isLoading}
            <LoadingSpinner />
        {:else if error}
            <div class="flex items-center justify-center h-32 text-destructive">{error}</div>
        {:else}
            <div class="mb-4">
                <h1 class="text-xl font-semibold">{workflowName} — Runs</h1>
            </div>
            <TraceTable {workflowId} />
        {/if}
    </div>
</div>
