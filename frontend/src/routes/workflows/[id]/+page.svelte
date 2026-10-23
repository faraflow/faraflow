<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { page } from '$app/stores'
    import { beforeNavigate, goto } from '$app/navigation'
    import { onMount, onDestroy } from 'svelte'
    import { toast } from 'svelte-sonner'
    import Header from '$lib/components/Header.svelte'
    import LoadingSpinner from '$lib/components/LoadingSpinner.svelte'
    import EditorCanvas from '$lib/components/canvas/EditorCanvas.svelte'
    import ChatCanvas from '$lib/components/canvas/ChatCanvas.svelte'
    import { flowStore } from '$lib/stores/flow.svelte'
    import { nodeTypesStore } from '$lib/stores/nodeTypes.svelte'
    import { getWorkflow } from '$lib/utils/api'
    import {
        executeWorkflow,
        stopWorkflow,
        fetchWorkflowRuns,
        stopRunsOverviewPolling,
        loadRunIntoCanvas,
    } from '$lib/actions/workflowExecution.svelte'
    import { SpurType, type WorkflowCreateRequest, type WorkflowResponse } from '$lib/types/api_types/workflowSchemas'

    const workflowId = $derived($page.params.id)

    let workflowData: WorkflowResponse | null = $state(null)
    let loading = $state(true)
    let error = $state<string | null>(null)
    let handleDownloadImage: (() => void) | undefined = $state()

    async function loadWorkflow(id: string) {
        loading = true
        error = null
        try {
            const data = await getWorkflow(id)
            workflowData = data
            if (data.definition?.test_inputs) {
                flowStore.setTestInputs(data.definition.test_inputs)
            }
        } catch (err) {
            console.error('Error fetching workflow:', err)
            error = 'Failed to load workflow'
        } finally {
            loading = false
        }
    }

    $effect(() => {
        if (workflowId) {
            loadWorkflow(workflowId)
        }
    })

    onMount(async () => {
        if (!nodeTypesStore.data) {
            await nodeTypesStore.fetch()
        }
        if (workflowId) {
            await fetchWorkflowRuns(workflowId)
        }
        const runId = $page.url.searchParams.get('runId')
        if (runId) {
            await loadRunIntoCanvas(runId)
            const url = new URL($page.url)
            url.searchParams.delete('runId')
            await goto(url, { replaceState: true, noScroll: true, keepFocus: true })
        }
    })

    onDestroy(() => {
        stopRunsOverviewPolling()
    })

    // Navigation guard for unsaved changes
    beforeNavigate(({ cancel }) => {
        // Future: check flowStore.hasUnsavedChanges
    })

    const isChatbot = $derived(
        workflowData?.definition?.spur_type === SpurType.CHATBOT
    )

    function onAlert(message: string, color: string) {
        if (color === 'success') toast.success(message)
        else if (color === 'danger') toast.error(message)
        else if (color === 'warning') toast.warning(message)
        else toast(message)
    }

    async function handleExecute(inputs: Record<string, any>) {
        await executeWorkflow(inputs, { onAlert })
    }

    function handleStop() {
        stopWorkflow({ onAlert })
    }
</script>

<svelte:head>
    <title>{workflowData?.name || 'Workflow'} — Faraflow</title>
</svelte:head>

<div class="h-screen flex flex-col overflow-hidden">
    <Header
        activePage="workflow"
        {handleDownloadImage}
        onExecute={handleExecute}
        showChatToggle={isChatbot}
    />

    <div class="flex-1 overflow-hidden">
        {#if loading}
            <LoadingSpinner />
        {:else if error}
            <div class="flex items-center justify-center h-full">
                <div class="text-center">
                    <p class="text-destructive mb-2">{error}</p>
                    <button class="text-primary hover:underline" onclick={() => workflowId && loadWorkflow(workflowId)}>
                        Try again
                    </button>
                </div>
            </div>
        {:else if workflowData}
            {#if isChatbot}
                <ChatCanvas
                    {workflowData}
                    workflowID={workflowId}
                    onDownloadImageInit={(fn) => (handleDownloadImage = fn)}
                    onStop={handleStop}
                />
            {:else}
                <EditorCanvas
                    {workflowData}
                    workflowID={workflowId}
                    onDownloadImageInit={(fn) => (handleDownloadImage = fn)}
                    onStop={handleStop}
                />
            {/if}
        {/if}
    </div>
</div>
