<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { toast } from 'svelte-sonner'
    import * as Dialog from '$lib/components/ui/dialog'
    import { Button } from '$lib/components/ui/button'
    import TextEditor from '$lib/components/textEditor/TextEditor.svelte'
    import { previewChunk } from '$lib/utils/api'
    import type {
        ChunkPreviewResponseSchema,
        ChunkPreviewSchema,
        ChunkTemplateSchema,
    } from '$lib/types/api_types/ragSchemas'

    interface Props {
        template: ChunkTemplateSchema
        onTemplateChange: (template: ChunkTemplateSchema) => void
        chunkingConfig: {
            chunk_token_size: number
            min_chunk_size_chars: number
            min_chunk_length_to_embed: number
        }
        files?: File[]
    }

    let { template, onTemplateChange, chunkingConfig, files = [] }: Props = $props()

    let selectedFileIndex = $state(0)
    let isPreviewLoading = $state(false)
    let previewResult = $state<ChunkPreviewResponseSchema | null>(null)
    let expandedChunk = $state<ChunkPreviewSchema | null>(null)

    // Keep the selected file valid as the upload list changes
    $effect(() => {
        if (selectedFileIndex >= files.length) selectedFileIndex = 0
    })

    async function handlePreview() {
        const file = files[selectedFileIndex]
        if (!file) {
            toast.error('Upload a file first to preview chunks')
            return
        }
        try {
            isPreviewLoading = true
            previewResult = await previewChunk(file, { ...chunkingConfig, template })
        } catch (err) {
            toast.error('Failed to generate chunk preview')
            console.error(err)
        } finally {
            isPreviewLoading = false
        }
    }

    function addMetadataField() {
        onTemplateChange({
            ...template,
            metadata_template: { ...template.metadata_template, '': '' },
        })
    }

    function updateMetadataField(oldKey: string, newKey: string, value: string) {
        const entries = Object.entries(template.metadata_template).map(([k, v]) =>
            k === oldKey ? [newKey, value] : [k, v]
        )
        onTemplateChange({ ...template, metadata_template: Object.fromEntries(entries) })
    }

    function removeMetadataField(key: string) {
        const { [key]: _, ...rest } = template.metadata_template as Record<string, string>
        onTemplateChange({ ...template, metadata_template: rest })
    }
</script>

<div class="border border-border rounded-xl p-4 space-y-4">
    <div class="flex items-center justify-between">
        <div>
            <h3 class="text-sm font-semibold">Chunk Template</h3>
            <p class="text-xs text-muted-foreground mt-0.5">
                Use <code class="px-1 py-0.5 rounded bg-muted font-mono">{'{{ text }}'}</code> to reference the chunk text.
            </p>
        </div>
        <button
            role="switch"
            aria-checked={template.enabled}
            aria-label="Enable chunk template"
            onclick={() => onTemplateChange({ ...template, enabled: !template.enabled })}
            class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                {template.enabled ? 'bg-primary' : 'bg-muted'}"
        >
            <span class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                {template.enabled ? 'translate-x-6' : 'translate-x-1'}"></span>
        </button>
    </div>

    {#if template.enabled}
        <TextEditor
            nodeID="chunk-template"
            fieldName="template"
            content={template.template}
            setContent={(content) => onTemplateChange({ ...template, template: content })}
            inputSchema={['text']}
            isTemplateEditor={true}
        />

        <div>
            <div class="flex items-center justify-between mb-2">
                <h4 class="text-sm font-medium">Metadata Template</h4>
                <Button variant="outline" size="sm" onclick={addMetadataField}>Add field</Button>
            </div>
            {#each Object.entries(template.metadata_template) as [key, value] (key)}
                <div class="flex gap-2 mb-2">
                    <input
                        type="text"
                        value={key}
                        placeholder="Field name"
                        onchange={(e) => updateMetadataField(key, e.currentTarget.value, value as string)}
                        class="flex-1 px-3 py-1.5 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                    <input
                        type="text"
                        {value}
                        placeholder="Value template"
                        onchange={(e) => updateMetadataField(key, key, e.currentTarget.value)}
                        class="flex-1 px-3 py-1.5 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring font-mono"
                    />
                    <button
                        onclick={() => removeMetadataField(key)}
                        aria-label="Remove metadata field"
                        class="px-2 text-muted-foreground hover:text-destructive transition-colors"
                    >
                        ✕
                    </button>
                </div>
            {/each}
        </div>

        <div class="border-t border-border pt-4">
            <div class="flex items-center justify-between mb-3">
                <h4 class="text-sm font-medium">Preview</h4>
                <div class="flex items-center gap-2">
                    {#if files.length > 1}
                        <select
                            bind:value={selectedFileIndex}
                            class="px-2 py-1.5 text-sm border border-border rounded-md bg-background focus:outline-none"
                        >
                            {#each files as file, i}
                                <option value={i}>{file.name}</option>
                            {/each}
                        </select>
                    {/if}
                    <Button
                        variant="outline"
                        size="sm"
                        onclick={handlePreview}
                        disabled={isPreviewLoading || files.length === 0}
                    >
                        {isPreviewLoading ? 'Generating...' : 'Preview Chunks'}
                    </Button>
                </div>
            </div>

            {#if files.length === 0}
                <p class="text-xs text-muted-foreground">Upload a file in the previous step to preview how it will be chunked.</p>
            {:else if previewResult}
                <div class="space-y-2 max-h-80 overflow-y-auto">
                    {#each previewResult.chunks as chunk}
                        <button
                            onclick={() => (expandedChunk = chunk)}
                            class="w-full text-left border border-border rounded-lg p-3 hover:border-primary transition-colors"
                        >
                            <p class="text-xs text-muted-foreground mb-1">Chunk {chunk.chunk_index + 1}</p>
                            <p class="text-sm line-clamp-3 whitespace-pre-wrap">{chunk.processed_text}</p>
                        </button>
                    {/each}
                </div>
            {/if}
        </div>
    {/if}
</div>

<Dialog.Root open={expandedChunk !== null} onOpenChange={(open) => { if (!open) expandedChunk = null }}>
    <Dialog.Content class="max-w-2xl">
        <Dialog.Header>
            <Dialog.Title>Chunk {(expandedChunk?.chunk_index ?? 0) + 1}</Dialog.Title>
        </Dialog.Header>
        {#if expandedChunk}
            <div class="space-y-4 max-h-[60vh] overflow-y-auto">
                <div>
                    <h4 class="text-sm font-medium mb-1">Processed</h4>
                    <p class="text-sm whitespace-pre-wrap border border-border rounded-lg p-3 bg-muted/30">{expandedChunk.processed_text}</p>
                </div>
                <div>
                    <h4 class="text-sm font-medium mb-1">Original</h4>
                    <p class="text-sm whitespace-pre-wrap border border-border rounded-lg p-3">{expandedChunk.original_text}</p>
                </div>
            </div>
        {/if}
        <Dialog.Footer>
            <Button variant="outline" onclick={() => (expandedChunk = null)}>Close</Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
