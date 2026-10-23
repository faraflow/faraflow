<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { page } from '$app/stores'
    import { goto } from '$app/navigation'
    import { onMount } from 'svelte'
    import { toast } from 'svelte-sonner'
    import Header from '$lib/components/Header.svelte'
    import LoadingSpinner from '$lib/components/LoadingSpinner.svelte'
    import * as Dialog from '$lib/components/ui/dialog'
    import { Button } from '$lib/components/ui/button'
    import { getVectorIndex, deleteVectorIndex, getDocumentCollection, getIndexProgress } from '$lib/utils/api'
    import type {
        DocumentCollectionResponseSchema,
        ProcessingProgressSchema,
        VectorIndexResponseSchema,
    } from '$lib/types/api_types/ragSchemas'

    const indexId = $derived($page.params.id)

    let index = $state<VectorIndexResponseSchema | null>(null)
    let collection = $state<DocumentCollectionResponseSchema | null>(null)
    let progressData = $state<ProcessingProgressSchema | null>(null)
    let progressError = $state<string | null>(null)
    let isLoading = $state(true)
    let error = $state<string | null>(null)
    let isDeleteOpen = $state(false)
    let isDeleting = $state(false)

    onMount(async () => {
        if (!indexId) return
        try {
            index = await getVectorIndex(indexId)
            getDocumentCollection(index.collection_id)
                .then((c) => (collection = c))
                .catch(() => {})
        } catch (err) {
            error = 'Failed to load vector index'
        } finally {
            isLoading = false
        }
    })

    // Poll progress every 2s while the index is processing
    $effect(() => {
        if (index?.status !== 'processing' || !indexId) return

        let cancelled = false
        const poll = async () => {
            try {
                const data = await getIndexProgress(indexId)
                if (cancelled) return
                if (!data) {
                    progressError = 'Progress information is not available'
                    clearInterval(interval)
                    return
                }
                progressData = data
                if (data.status === 'completed' || data.current_step === 'completed') {
                    clearInterval(interval)
                    index = await getVectorIndex(indexId)
                }
            } catch {
                if (cancelled) return
                progressError = 'Failed to fetch indexing progress'
                clearInterval(interval)
            }
        }
        poll()
        const interval = setInterval(poll, 2000)
        return () => {
            cancelled = true
            clearInterval(interval)
        }
    })

    const humanizeStep = (step: string) => step.replace(/_/g, ' ')

    async function handleDelete() {
        if (!indexId) return
        try {
            isDeleting = true
            await deleteVectorIndex(indexId)
            toast.success('Vector index deleted')
            goto('/rag')
        } catch {
            toast.error('Failed to delete vector index')
            isDeleting = false
        }
    }

    const statusColor = $derived(
        index?.status === 'ready'
            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
            : index?.status === 'failed'
              ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
              : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
    )
</script>

<svelte:head>
    <title>{index?.name ?? 'Vector Index'} - Faraflow</title>
</svelte:head>

<div class="min-h-screen flex flex-col">
    <Header activePage="rag" />

    <div class="max-w-3xl mx-auto w-full px-6 py-6 flex-1">
        {#if isLoading}
            <LoadingSpinner />
        {:else if error || !index}
            <p class="text-destructive">{error ?? 'Index not found'}</p>
        {:else}
            <div class="flex items-start justify-between mb-6">
                <div class="flex items-center gap-3">
                    <button onclick={() => goto('/rag')} class="p-2 rounded hover:bg-muted transition-colors">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 19-7-7 7-7"/><path d="M19 12H5"/></svg>
                    </button>
                    <div>
                        <h1 class="text-2xl font-bold">{index.name}</h1>
                        {#if index.description}
                            <p class="text-sm text-muted-foreground mt-0.5">{index.description}</p>
                        {/if}
                    </div>
                </div>
                <Button variant="destructive" size="sm" onclick={() => (isDeleteOpen = true)}>Delete</Button>
            </div>

            <!-- Details grid -->
            <div class="grid grid-cols-2 gap-4 mb-6">
                <div class="border border-border rounded-xl p-4">
                    <p class="text-sm text-muted-foreground">Embedding Model</p>
                    <p class="font-medium mt-1">{index.embedding_model}</p>
                </div>
                <div class="border border-border rounded-xl p-4">
                    <p class="text-sm text-muted-foreground">Vector Store</p>
                    <p class="font-medium mt-1">{index.vector_db}</p>
                </div>
                <div class="border border-border rounded-xl p-4">
                    <p class="text-sm text-muted-foreground">Documents</p>
                    <p class="text-2xl font-bold mt-1">{index.document_count}</p>
                </div>
                <div class="border border-border rounded-xl p-4">
                    <p class="text-sm text-muted-foreground">Chunks</p>
                    <p class="text-2xl font-bold mt-1">{index.chunk_count}</p>
                </div>
                <div class="border border-border rounded-xl p-4">
                    <p class="text-sm text-muted-foreground">Status</p>
                    <span class="text-xs px-2 py-0.5 rounded-full font-medium mt-1 inline-block capitalize {statusColor}">
                        {index.status}
                    </span>
                </div>
            </div>

            {#if index.status === 'processing'}
                <div class="border border-border rounded-xl p-4 mb-6">
                    <div class="flex items-center justify-between mb-2">
                        <p class="text-sm font-medium">
                            Indexing{#if progressData?.current_step}
                                <span class="text-muted-foreground font-normal capitalize">
                                    — {humanizeStep(progressData.current_step)}</span>
                            {/if}
                        </p>
                        {#if progressData}
                            <p class="text-sm text-muted-foreground">{Math.round(progressData.progress * 100)}%</p>
                        {/if}
                    </div>
                    <div class="w-full h-2 bg-muted rounded-full overflow-hidden">
                        <div
                            class="h-full bg-primary rounded-full transition-all duration-500"
                            style="width: {(progressData?.progress ?? 0) * 100}%"
                        ></div>
                    </div>
                    {#if progressData}
                        <div class="flex gap-6 mt-2 text-xs text-muted-foreground">
                            {#if progressData.total_files}
                                <span>{progressData.processed_files ?? 0}/{progressData.total_files} files</span>
                            {/if}
                            {#if progressData.total_chunks}
                                <span>{progressData.processed_chunks ?? 0}/{progressData.total_chunks} chunks</span>
                            {/if}
                        </div>
                    {/if}
                    {#if progressError}
                        <p class="text-xs text-muted-foreground mt-2">{progressError}</p>
                    {/if}
                </div>
            {/if}

            {#if index.error_message}
                <div class="p-4 rounded-lg bg-destructive/10 text-destructive text-sm mb-4">
                    {index.error_message}
                </div>
            {/if}

            <div class="border border-border rounded-xl p-4">
                <p class="text-sm text-muted-foreground">Document Collection</p>
                <p class="font-medium mt-1">{collection?.name ?? index.collection_id}</p>
                {#if collection}
                    <p class="font-mono text-xs text-muted-foreground mt-0.5">{index.collection_id}</p>
                {/if}
                <button
                    onclick={() => goto(`/rag/collections/${index!.collection_id}`)}
                    class="text-primary text-sm hover:underline mt-1 block"
                >
                    View Collection →
                </button>
            </div>
        {/if}
    </div>
</div>

<Dialog.Root bind:open={isDeleteOpen}>
    <Dialog.Content class="max-w-md">
        <Dialog.Header>
            <Dialog.Title>Delete Vector Index</Dialog.Title>
            <Dialog.Description>
                Are you sure you want to delete "{index?.name}"? This action cannot be undone.
            </Dialog.Description>
        </Dialog.Header>
        <Dialog.Footer>
            <Button variant="ghost" onclick={() => (isDeleteOpen = false)}>Cancel</Button>
            <Button variant="destructive" onclick={handleDelete} disabled={isDeleting}>
                {isDeleting ? 'Deleting...' : 'Delete'}
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
