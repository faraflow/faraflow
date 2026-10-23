<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { goto } from '$app/navigation'
    import { toast } from 'svelte-sonner'
    import Header from '$lib/components/Header.svelte'
    import FileUploadBox from '$lib/components/FileUploadBox.svelte'
    import ChunkEditor from '$lib/components/rag/ChunkEditor.svelte'
    import { createDocumentCollection } from '$lib/utils/api'
    import type { ChunkTemplateSchema, DocumentCollectionCreateRequestSchema } from '$lib/types/api_types/ragSchemas'

    let step = $state(1)
    let name = $state(generateName())
    let description = $state('')
    let chunkingMode = $state<'automatic' | 'manual'>('automatic')
    let chunkSize = $state(1000)
    let minChunkSize = $state(100)
    let files = $state<File[]>([])
    let isSubmitting = $state(false)
    let template = $state<ChunkTemplateSchema>({
        enabled: false,
        template: '{{ text }}',
        metadata_template: {},
    })

    const chunkingConfig = $derived({
        chunk_token_size: chunkingMode === 'automatic' ? 1000 : chunkSize,
        min_chunk_size_chars: chunkingMode === 'automatic' ? 100 : minChunkSize,
        min_chunk_length_to_embed: 10,
    })

    function generateName() {
        const adjs = ['Smart', 'Neural', 'Quantum', 'Dynamic', 'Advanced']
        const nouns = ['Archive', 'Nexus', 'Vault', 'Repository', 'Hub']
        const adj = adjs[Math.floor(Math.random() * adjs.length)]
        const noun = nouns[Math.floor(Math.random() * nouns.length)]
        const ts = new Date().toLocaleString()
        return `${adj} ${noun} - ${ts}`
    }

    async function handleCreate() {
        if (!name.trim()) { toast.error('Please enter a collection name'); return }
        try {
            isSubmitting = true
            const payload: DocumentCollectionCreateRequestSchema = {
                name: name.trim(),
                description: description.trim() || undefined,
                text_processing: {
                    ...chunkingConfig,
                    max_num_chunks: 1000,
                    // Vision model support is not configurable yet (backend rejects
                    // use_vision_model without a model/provider)
                    use_vision_model: false,
                    template: template.enabled ? template : undefined,
                },
            }
            const collection = await createDocumentCollection(payload, files.length > 0 ? files : undefined)
            toast.success('Collection created!')
            goto(`/rag/collections/${collection.id}`)
        } catch (err) {
            toast.error('Failed to create collection')
            console.error(err)
            isSubmitting = false
        }
    }
</script>

<svelte:head>
    <title>New Document Collection - Faraflow</title>
</svelte:head>

<div class="min-h-screen flex flex-col">
    <Header activePage="rag" />

    <div class="max-w-2xl mx-auto w-full px-6 py-8 flex-1">
        <div class="flex items-center gap-3 mb-8">
            <button onclick={() => goto('/rag')} class="p-2 rounded hover:bg-muted transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 19-7-7 7-7"/><path d="M19 12H5"/></svg>
            </button>
            <h1 class="text-2xl font-bold">New Document Collection</h1>
        </div>

        <!-- Step indicator -->
        <div class="flex items-center gap-3 mb-8">
            {#each [{ n: 1, label: 'Upload' }, { n: 2, label: 'Configure' }] as s}
                <div class="flex items-center gap-2">
                    <div class="w-7 h-7 rounded-full flex items-center justify-center text-sm font-semibold
                        {step === s.n ? 'bg-primary text-primary-foreground' : step > s.n ? 'bg-green-500 text-white' : 'bg-muted text-muted-foreground'}">
                        {step > s.n ? '✓' : s.n}
                    </div>
                    <span class="text-sm {step === s.n ? 'font-medium' : 'text-muted-foreground'}">{s.label}</span>
                </div>
                {#if s.n < 2}
                    <div class="flex-1 h-px bg-border"></div>
                {/if}
            {/each}
        </div>

        {#if step === 1}
            <div class="border border-border rounded-xl p-6 space-y-6">
                <div>
                    <h2 class="text-lg font-semibold mb-1">Upload Documents</h2>
                    <p class="text-sm text-muted-foreground">
                        Upload PDF, TXT, or Markdown files. Optional — you can also add documents later.
                    </p>
                </div>

                <FileUploadBox
                    multiple={true}
                    onFilesChange={(f) => (files = f)}
                    supportedFormatsMessage="Upload PDF, TXT, MD, or DOCX files"
                />

                {#if files.length > 0}
                    <div class="space-y-1">
                        {#each files as file}
                            <div class="flex items-center gap-2 text-sm text-muted-foreground">
                                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                                {file.name}
                            </div>
                        {/each}
                    </div>
                {/if}

                <div class="flex gap-3 pt-2">
                    <button
                        onclick={() => goto('/rag')}
                        class="px-4 py-2 rounded-md border border-border text-sm hover:bg-muted transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onclick={() => (step = 2)}
                        class="px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm hover:bg-primary/90 transition-colors"
                    >
                        {files.length > 0 ? 'Next' : 'Skip — configure empty collection'}
                    </button>
                </div>
            </div>
        {:else}
            <div class="border border-border rounded-xl p-6 space-y-6">
                <div>
                    <label class="block text-sm font-medium mb-1.5">Collection Name</label>
                    <input
                        type="text"
                        bind:value={name}
                        class="w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                        placeholder="Enter collection name"
                    />
                </div>

                <div>
                    <label class="block text-sm font-medium mb-1.5">Description (optional)</label>
                    <textarea
                        bind:value={description}
                        rows={3}
                        class="w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring resize-none"
                        placeholder="Describe your collection..."
                    ></textarea>
                </div>

                <div>
                    <label class="block text-sm font-medium mb-1.5">Chunking</label>
                    <div class="flex gap-4">
                        {#each [{ v: 'automatic', label: 'Automatic (recommended)' }, { v: 'manual', label: 'Manual' }] as opt}
                            <label class="flex items-center gap-2 cursor-pointer">
                                <input type="radio" bind:group={chunkingMode} value={opt.v} class="rounded-full" />
                                <span class="text-sm">{opt.label}</span>
                            </label>
                        {/each}
                    </div>
                </div>

                {#if chunkingMode === 'manual'}
                    <div>
                        <label class="block text-sm font-medium mb-1.5">Chunk Token Size: {chunkSize}</label>
                        <input type="range" bind:value={chunkSize} min={128} max={2048} step={64} class="w-full" />
                        <div class="flex justify-between text-xs text-muted-foreground mt-1">
                            <span>128</span><span>2048</span>
                        </div>
                    </div>

                    <div>
                        <label class="block text-sm font-medium mb-1.5">Min Chunk Size (chars): {minChunkSize}</label>
                        <input type="range" bind:value={minChunkSize} min={5} max={200} step={5} class="w-full" />
                    </div>
                {/if}

                <ChunkEditor
                    {template}
                    onTemplateChange={(t) => (template = t)}
                    {chunkingConfig}
                    {files}
                />

                <div class="flex items-center gap-3 opacity-50">
                    <button
                        role="switch"
                        aria-checked="false"
                        disabled
                        class="relative inline-flex h-6 w-11 items-center rounded-full bg-muted cursor-not-allowed"
                    >
                        <span class="inline-block h-4 w-4 transform rounded-full bg-white translate-x-1"></span>
                    </button>
                    <label class="text-sm font-medium">Use Vision Model for PDFs <span class="text-muted-foreground font-normal">(Coming Soon)</span></label>
                </div>

                <div class="flex gap-3 pt-2">
                    <button
                        onclick={() => (step = 1)}
                        class="px-4 py-2 rounded-md border border-border text-sm hover:bg-muted transition-colors"
                    >
                        Back
                    </button>
                    <button
                        onclick={handleCreate}
                        disabled={isSubmitting}
                        class="px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm hover:bg-primary/90 disabled:opacity-50 transition-colors"
                    >
                        {isSubmitting
                            ? 'Creating...'
                            : files.length > 0
                              ? `Create & upload ${files.length} file${files.length > 1 ? 's' : ''}`
                              : 'Create Collection'}
                    </button>
                </div>
            </div>
        {/if}
    </div>
</div>
