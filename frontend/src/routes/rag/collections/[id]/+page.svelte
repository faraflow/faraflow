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
    import FileUploadBox from '$lib/components/FileUploadBox.svelte'
    import * as Dialog from '$lib/components/ui/dialog'
    import { Button } from '$lib/components/ui/button'
    import {
        getDocumentCollection,
        getCollectionDocuments,
        addDocumentsToCollection,
        deleteDocumentCollection,
    } from '$lib/utils/api'
    import type { DocumentCollectionResponseSchema, DocumentWithChunksSchema } from '$lib/types/api_types/ragSchemas'

    const collectionId = $derived($page.params.id)

    let collection = $state<DocumentCollectionResponseSchema | null>(null)
    let documents = $state<DocumentWithChunksSchema[]>([])
    let isLoading = $state(true)
    let error = $state<string | null>(null)
    let selectedFiles = $state<File[]>([])
    let isAddOpen = $state(false)
    let isDeleteOpen = $state(false)
    let isAdding = $state(false)
    let isDeleting = $state(false)
    let expandedDocs = $state<Set<string>>(new Set())
    let selectedChunkText = $state<string | null>(null)
    let isChunkOpen = $state(false)
    let viewedDoc = $state<DocumentWithChunksSchema | null>(null)

    onMount(async () => {
        await loadData()
    })

    async function loadData() {
        if (!collectionId) return
        try {
            isLoading = true
            const [col, docs] = await Promise.all([
                getDocumentCollection(collectionId),
                getCollectionDocuments(collectionId),
            ])
            collection = col
            documents = docs
        } catch (err) {
            console.error('Error loading collection:', err)
            error = 'Error loading collection data'
        } finally {
            isLoading = false
        }
    }

    async function handleAddDocuments() {
        if (selectedFiles.length === 0 || !collectionId) return
        try {
            isAdding = true
            await addDocumentsToCollection(collectionId, selectedFiles)
            toast.success('Documents added successfully')
            isAddOpen = false
            selectedFiles = []
            await loadData()
        } catch {
            toast.error('Failed to add documents')
        } finally {
            isAdding = false
        }
    }

    async function handleDelete() {
        if (!collectionId) return
        try {
            isDeleting = true
            await deleteDocumentCollection(collectionId)
            toast.success('Collection deleted')
            goto('/rag')
        } catch {
            toast.error('Failed to delete collection')
            isDeleting = false
        }
    }

    function toggleDoc(docId: string) {
        const next = new Set(expandedDocs)
        if (next.has(docId)) next.delete(docId)
        else next.add(docId)
        expandedDocs = next
    }

    const statusColor = $derived(
        collection?.status === 'ready'
            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
            : collection?.status === 'failed'
              ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
              : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
    )
</script>

<svelte:head>
    <title>{collection?.name ?? 'Collection'} - Faraflow</title>
</svelte:head>

<div class="min-h-screen flex flex-col">
    <Header activePage="rag" />

    <div class="max-w-5xl mx-auto w-full px-6 py-6 flex-1">
        {#if isLoading}
            <LoadingSpinner />
        {:else if error || !collection}
            <p class="text-destructive">{error ?? 'Collection not found'}</p>
        {:else}
            <!-- Header -->
            <div class="flex items-start justify-between mb-6">
                <div class="flex items-center gap-3">
                    <button onclick={() => goto('/rag')} class="p-2 rounded hover:bg-muted transition-colors">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 19-7-7 7-7"/><path d="M19 12H5"/></svg>
                    </button>
                    <div>
                        <h1 class="text-2xl font-bold">{collection.name}</h1>
                        {#if collection.description}
                            <p class="text-sm text-muted-foreground mt-0.5">{collection.description}</p>
                        {/if}
                    </div>
                </div>
                <div class="flex items-center gap-2">
                    <Button variant="outline" size="sm" onclick={() => (isAddOpen = true)}>
                        Add Documents
                    </Button>
                    <Button size="sm" onclick={() => goto(`/rag/indices/new?collection=${collectionId}`)}>
                        Create Vector Index
                    </Button>
                    <Button variant="destructive" size="sm" onclick={() => (isDeleteOpen = true)}>
                        Delete
                    </Button>
                </div>
            </div>

            {#if collection.error_message}
                <div class="p-4 rounded-lg bg-destructive/10 text-destructive text-sm mb-6">
                    {collection.error_message}
                </div>
            {/if}

            <!-- Stats -->
            <div class="grid grid-cols-3 gap-4 mb-6">
                <div class="border border-border rounded-xl p-4">
                    <p class="text-sm text-muted-foreground">Documents</p>
                    <p class="text-2xl font-bold mt-1">{collection.document_count}</p>
                </div>
                <div class="border border-border rounded-xl p-4">
                    <p class="text-sm text-muted-foreground">Chunks</p>
                    <p class="text-2xl font-bold mt-1">{collection.chunk_count}</p>
                </div>
                <div class="border border-border rounded-xl p-4">
                    <p class="text-sm text-muted-foreground">Status</p>
                    <span class="text-xs px-2 py-0.5 rounded-full font-medium mt-1 inline-block capitalize {statusColor}">
                        {collection.status}
                    </span>
                </div>
            </div>

            <!-- Documents -->
            <div class="space-y-3">
                <h2 class="text-lg font-semibold">Documents</h2>
                {#if documents.length === 0}
                    <p class="text-muted-foreground text-sm py-4">No documents in this collection yet.</p>
                {:else}
                    {#each documents as doc (doc.id)}
                        <div class="border border-border rounded-xl overflow-hidden">
                            <button
                                onclick={() => toggleDoc(doc.id)}
                                class="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-muted/30 transition-colors"
                            >
                                <div class="flex items-center gap-2">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                                    <span class="text-sm font-medium">{doc.metadata?.title ?? doc.id}</span>
                                    <span class="text-xs text-muted-foreground">({doc.chunks.length} chunks)</span>
                                    <span
                                        role="button"
                                        tabindex="0"
                                        onclick={(e) => { e.stopPropagation(); viewedDoc = doc }}
                                        onkeydown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); viewedDoc = doc } }}
                                        class="text-xs text-primary hover:underline"
                                    >
                                        View text
                                    </span>
                                </div>
                                <svg
                                    xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
                                    class="transition-transform {expandedDocs.has(doc.id) ? 'rotate-180' : ''}"
                                ><path d="m6 9 6 6 6-6"/></svg>
                            </button>

                            {#if expandedDocs.has(doc.id)}
                                <div class="border-t border-border p-4 grid grid-cols-2 md:grid-cols-3 gap-3">
                                    {#each doc.chunks as chunk (chunk.id)}
                                        <button
                                            onclick={() => { selectedChunkText = chunk.text; isChunkOpen = true }}
                                            class="text-left border border-border rounded-lg p-3 text-xs text-muted-foreground hover:bg-muted/50 hover:border-primary/50 transition-colors line-clamp-4"
                                        >
                                            {chunk.text}
                                        </button>
                                    {/each}
                                </div>
                            {/if}
                        </div>
                    {/each}
                {/if}
            </div>
        {/if}
    </div>
</div>

<!-- Add Documents Dialog -->
<Dialog.Root bind:open={isAddOpen}>
    <Dialog.Content class="max-w-lg">
        <Dialog.Header>
            <Dialog.Title>Add Documents</Dialog.Title>
        </Dialog.Header>
        <div class="py-4">
            <FileUploadBox
                multiple={true}
                onFilesChange={(f) => (selectedFiles = f)}
                supportedFormatsMessage="Upload PDF, TXT, MD, or DOCX files"
            />
        </div>
        <Dialog.Footer>
            <Button variant="ghost" onclick={() => (isAddOpen = false)}>Cancel</Button>
            <Button onclick={handleAddDocuments} disabled={isAdding || selectedFiles.length === 0}>
                {isAdding ? 'Uploading...' : `Upload ${selectedFiles.length} file${selectedFiles.length !== 1 ? 's' : ''}`}
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>

<!-- Delete Confirmation Dialog -->
<Dialog.Root bind:open={isDeleteOpen}>
    <Dialog.Content class="max-w-md">
        <Dialog.Header>
            <Dialog.Title>Delete Collection</Dialog.Title>
            <Dialog.Description>
                Are you sure you want to delete "{collection?.name}"? This action cannot be undone.
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

<!-- Document Text Dialog -->
<Dialog.Root open={viewedDoc !== null} onOpenChange={(open) => { if (!open) viewedDoc = null }}>
    <Dialog.Content class="max-w-3xl max-h-[80vh]">
        <Dialog.Header>
            <Dialog.Title>{viewedDoc?.metadata?.title ?? viewedDoc?.id}</Dialog.Title>
        </Dialog.Header>
        <div class="overflow-y-auto whitespace-pre-wrap text-sm py-2 max-h-[60vh]">
            {viewedDoc?.text}
        </div>
        <Dialog.Footer>
            <Button variant="ghost" onclick={() => (viewedDoc = null)}>Close</Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>

<!-- Chunk Text Dialog -->
<Dialog.Root bind:open={isChunkOpen}>
    <Dialog.Content class="max-w-2xl max-h-[80vh]">
        <Dialog.Header>
            <Dialog.Title>Chunk Text</Dialog.Title>
        </Dialog.Header>
        <div class="overflow-y-auto whitespace-pre-wrap text-sm py-2 max-h-[60vh]">
            {selectedChunkText}
        </div>
        <Dialog.Footer>
            <Button variant="ghost" onclick={() => (isChunkOpen = false)}>Close</Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
