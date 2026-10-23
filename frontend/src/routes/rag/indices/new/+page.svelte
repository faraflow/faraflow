<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { onMount } from 'svelte'
    import { goto } from '$app/navigation'
    import { page } from '$app/stores'
    import { toast } from 'svelte-sonner'
    import Header from '$lib/components/Header.svelte'
    import ApiKeyWarning from '$lib/components/rag/ApiKeyWarning.svelte'
    import { getEmbeddingModels, getVectorStores, listDocumentCollections, createVectorIndex } from '$lib/utils/api'
    import { apiKeyStatus } from '$lib/stores/apiKeyStatus.svelte'
    import type { DocumentCollectionResponseSchema } from '$lib/types/api_types/ragSchemas'
    import type { EmbeddingModelConfig, VectorStoreConfig } from '$lib/utils/api'

    let name = $state(generateName())
    let description = $state('')
    let collectionId = $state('')
    let embeddingModel = $state('')
    let vectorDb = $state('')
    let searchStrategy = $state('semantic')
    let collections = $state<DocumentCollectionResponseSchema[]>([])
    let embeddingModels = $state<Record<string, EmbeddingModelConfig>>({})
    let vectorStores = $state<Record<string, VectorStoreConfig>>({})
    let apiKeys = $state<Record<string, string>>({})
    let isLoading = $state(true)
    let isSubmitting = $state(false)

    const modelsByProvider = $derived(
        Object.entries(embeddingModels).reduce(
            (groups, [key, model]) => {
                const provider = model.provider || 'Other'
                ;(groups[provider] ??= []).push([key, model])
                return groups
            },
            {} as Record<string, Array<[string, EmbeddingModelConfig]>>
        )
    )

    function generateName() {
        const adjs = ['Smart', 'Neural', 'Quantum', 'Dynamic', 'Advanced']
        const nouns = ['Atlas', 'Nexus', 'Matrix', 'Archive', 'Index']
        const adj = adjs[Math.floor(Math.random() * adjs.length)]
        const noun = nouns[Math.floor(Math.random() * nouns.length)]
        return `${adj} ${noun} - ${new Date().toLocaleString()}`
    }

    onMount(async () => {
        try {
            const [cols, models, stores] = await Promise.all([
                listDocumentCollections(),
                getEmbeddingModels(),
                getVectorStores(),
            ])
            collections = cols
            embeddingModels = models
            vectorStores = stores
            // Set defaults
            const firstModel = Object.keys(models)[0]
            const firstStore = Object.keys(stores)[0]
            if (firstModel) embeddingModel = firstModel
            if (firstStore) vectorDb = firstStore

            // Preselect collection from ?collection= (link from collection page)
            const preselect = $page.url.searchParams.get('collection')
            if (preselect && cols.some((c) => c.id === preselect)) {
                collectionId = preselect
            }

            // Load configured API keys so we can warn about missing provider credentials
            apiKeyStatus
                .ensureLoaded()
                .then(() => {
                    const map: Record<string, string> = {}
                    for (const [name, set] of Object.entries(apiKeyStatus.configured)) {
                        if (set) map[name] = 'set'
                    }
                    apiKeys = map
                })
                .catch(() => {})
        } catch (err) {
            toast.error('Failed to load configuration options')
        } finally {
            isLoading = false
        }
    })

    async function handleCreate() {
        if (!name.trim()) { toast.error('Please enter a name'); return }
        if (!collectionId) { toast.error('Please select a collection'); return }
        if (!embeddingModel) { toast.error('Please select an embedding model'); return }
        if (!vectorDb) { toast.error('Please select a vector store'); return }

        try {
            isSubmitting = true
            const index = await createVectorIndex({
                name: name.trim(),
                description: description.trim() || undefined,
                collection_id: collectionId,
                embedding: {
                    model: embeddingModel,
                    vector_db: vectorDb,
                    search_strategy: searchStrategy,
                },
            })
            toast.success('Vector index created!')
            goto(`/rag/indices/${index.id}`)
        } catch (err) {
            toast.error('Failed to create vector index')
            console.error(err)
        } finally {
            isSubmitting = false
        }
    }
</script>

<svelte:head>
    <title>New Vector Index - Faraflow</title>
</svelte:head>

<div class="min-h-screen flex flex-col">
    <Header activePage="rag" />

    <div class="max-w-2xl mx-auto w-full px-6 py-8 flex-1">
        <div class="flex items-center gap-3 mb-8">
            <button onclick={() => goto('/rag')} class="p-2 rounded hover:bg-muted transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 19-7-7 7-7"/><path d="M19 12H5"/></svg>
            </button>
            <h1 class="text-2xl font-bold">New Vector Index</h1>
        </div>

        {#if isLoading}
            <div class="flex justify-center py-12">
                <div class="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full"></div>
            </div>
        {:else}
            <div class="border border-border rounded-xl p-6 space-y-6">
                <div>
                    <label class="block text-sm font-medium mb-1.5">Index Name</label>
                    <input type="text" bind:value={name} class="w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring" />
                </div>

                <div>
                    <label class="block text-sm font-medium mb-1.5">Description (optional)</label>
                    <textarea bind:value={description} rows={2} class="w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring resize-none"></textarea>
                </div>

                <div>
                    <label class="block text-sm font-medium mb-1.5">Document Collection</label>
                    <select bind:value={collectionId} class="w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring">
                        <option value="">Select a collection...</option>
                        {#each collections as col}
                            <option value={col.id}>{col.name} ({col.chunk_count} chunks)</option>
                        {/each}
                    </select>
                </div>

                <div>
                    <label class="block text-sm font-medium mb-1.5">Embedding Model</label>
                    <select bind:value={embeddingModel} class="w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring">
                        <option value="">Select a model...</option>
                        {#each Object.entries(modelsByProvider) as [provider, models]}
                            <optgroup label={provider}>
                                {#each models as [key, model]}
                                    <option value={key}>{model.name ?? key}{model.dimensions ? ` — ${model.dimensions} dims` : ''}</option>
                                {/each}
                            </optgroup>
                        {/each}
                    </select>
                    {#if embeddingModel && embeddingModels[embeddingModel]}
                        <ApiKeyWarning
                            requiredEnvVars={embeddingModels[embeddingModel].required_env_vars ?? []}
                            {apiKeys}
                            serviceName={embeddingModels[embeddingModel].name ?? embeddingModel}
                        />
                    {/if}
                </div>

                <div>
                    <label class="block text-sm font-medium mb-1.5">Vector Store</label>
                    <select bind:value={vectorDb} class="w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring">
                        <option value="">Select a vector store...</option>
                        {#each Object.entries(vectorStores) as [key, store]}
                            <option value={key}>{store.name ?? key}{store.description ? ` — ${store.description}` : ''}</option>
                        {/each}
                    </select>
                    {#if vectorDb && vectorStores[vectorDb]}
                        <ApiKeyWarning
                            requiredEnvVars={vectorStores[vectorDb].required_env_vars ?? []}
                            {apiKeys}
                            serviceName={vectorStores[vectorDb].name ?? vectorDb}
                        />
                    {/if}
                </div>

                <div>
                    <label class="block text-sm font-medium mb-1.5">Search Strategy</label>
                    <div class="flex gap-4">
                        {#each ['semantic', 'keyword', 'hybrid'] as strategy}
                            <label class="flex items-center gap-2 cursor-pointer">
                                <input type="radio" bind:group={searchStrategy} value={strategy} class="rounded-full" />
                                <span class="text-sm capitalize">{strategy}</span>
                            </label>
                        {/each}
                    </div>
                </div>

                <div class="flex gap-3 pt-2">
                    <button
                        onclick={() => goto('/rag')}
                        class="px-4 py-2 rounded-md border border-border text-sm hover:bg-muted transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onclick={handleCreate}
                        disabled={isSubmitting}
                        class="px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm hover:bg-primary/90 disabled:opacity-50 transition-colors"
                    >
                        {isSubmitting ? 'Creating...' : 'Create Index'}
                    </button>
                </div>
            </div>
        {/if}
    </div>
</div>
