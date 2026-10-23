<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { onMount } from 'svelte'
    import { goto } from '$app/navigation'
    import Header from '$lib/components/Header.svelte'
    import LoadingSpinner from '$lib/components/LoadingSpinner.svelte'
    import DocumentCollectionCard from '$lib/components/cards/DocumentCollectionCard.svelte'
    import VectorIndexCard from '$lib/components/cards/VectorIndexCard.svelte'
    import { listDocumentCollections, listVectorIndices } from '$lib/utils/api'
    import type { DocumentCollectionResponseSchema, VectorIndexResponseSchema } from '$lib/types/api_types/ragSchemas'

    let collections = $state<DocumentCollectionResponseSchema[]>([])
    let indices = $state<VectorIndexResponseSchema[]>([])
    let isLoading = $state(true)
    let error = $state<string | null>(null)

    onMount(async () => {
        try {
            const [colData, idxData] = await Promise.all([listDocumentCollections(), listVectorIndices()])
            collections = [...colData].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
            indices = [...idxData].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        } catch (err) {
            console.error('Error loading RAG data:', err)
            error = 'Failed to load data. Please try again.'
        } finally {
            isLoading = false
        }
    })
</script>

<svelte:head>
    <title>Knowledge Bases - Faraflow</title>
</svelte:head>

<div class="min-h-screen flex flex-col">
    <Header activePage="rag" />

    <div class="max-w-7xl mx-auto w-full px-6 py-6 flex-1">
        {#if error}
            <div class="mb-4 p-4 rounded-lg bg-destructive/10 text-destructive text-sm">{error}</div>
        {/if}

        {#if isLoading}
            <LoadingSpinner />
        {:else}
            <div class="space-y-8">
                <!-- Header card -->
                <div class="border border-border rounded-xl p-6">
                    <h1 class="text-2xl font-bold mb-1">Knowledge Bases</h1>
                    <p class="text-sm text-muted-foreground">Manage your document collections and vector indices</p>
                </div>

                <!-- Document Collections -->
                <div class="border border-border rounded-xl p-6 space-y-4">
                    <div class="flex items-center justify-between">
                        <h2 class="text-lg font-semibold">Document Collections</h2>
                        <button
                            onclick={() => goto('/rag/collections/new')}
                            class="flex items-center gap-2 px-3 py-2 rounded-md bg-primary text-primary-foreground text-sm hover:bg-primary/90 transition-colors"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 8v8"/><path d="M8 12h8"/></svg>
                            Create Collection
                        </button>
                    </div>

                    {#if collections.length > 0}
                        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {#each collections as col (col.id)}
                                <DocumentCollectionCard collection={col} onClick={(id) => goto(`/rag/collections/${id}`)} />
                            {/each}
                        </div>
                    {:else}
                        <div class="flex flex-col items-center gap-4 py-10 text-muted-foreground">
                            <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                            <p>No document collections found</p>
                            <button
                                onclick={() => goto('/rag/collections/new')}
                                class="flex items-center gap-2 px-3 py-2 rounded-md border border-border text-sm hover:bg-muted transition-colors"
                            >
                                Create Your First Collection
                            </button>
                        </div>
                    {/if}
                </div>

                <!-- Vector Indices -->
                <div class="border border-border rounded-xl p-6 space-y-4">
                    <div class="flex items-center justify-between">
                        <h2 class="text-lg font-semibold">Vector Indices</h2>
                        <button
                            onclick={() => goto('/rag/indices/new')}
                            class="flex items-center gap-2 px-3 py-2 rounded-md bg-primary text-primary-foreground text-sm hover:bg-primary/90 transition-colors"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 8v8"/><path d="M8 12h8"/></svg>
                            Create Index
                        </button>
                    </div>

                    {#if indices.length > 0}
                        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {#each indices as idx (idx.id)}
                                <VectorIndexCard index={idx} onClick={(id) => goto(`/rag/indices/${id}`)} />
                            {/each}
                        </div>
                    {:else}
                        <div class="flex flex-col items-center gap-4 py-10 text-muted-foreground">
                            <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/></svg>
                            <p>No vector indices found</p>
                            <button
                                onclick={() => goto('/rag/indices/new')}
                                class="flex items-center gap-2 px-3 py-2 rounded-md border border-border text-sm hover:bg-muted transition-colors"
                            >
                                Create Your First Index
                            </button>
                        </div>
                    {/if}
                </div>
            </div>
        {/if}
    </div>
</div>
