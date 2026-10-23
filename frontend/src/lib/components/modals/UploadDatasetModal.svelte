<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { toast } from 'svelte-sonner'
    import * as Dialog from '$lib/components/ui/dialog'
    import { Button } from '$lib/components/ui/button'
    import { uploadDataset } from '$lib/utils/api'
    import type { DatasetResponse } from '$lib/types/api_types/datasetSchemas'

    interface Props {
        isOpen: boolean
        onOpenChange: (open: boolean) => void
        onUploaded: (dataset: DatasetResponse) => void
    }

    let { isOpen, onOpenChange, onUploaded }: Props = $props()

    let name = $state('')
    let description = $state('')
    let file = $state<File | null>(null)
    let isUploading = $state(false)

    function handleFileChange(e: Event) {
        const selected = (e.currentTarget as HTMLInputElement).files?.[0] ?? null
        file = selected
        if (selected && !name.trim()) {
            name = selected.name.replace(/\.(csv|jsonl|parquet)$/i, '')
        }
    }

    async function handleUpload() {
        if (!file) { toast.error('Please choose a file'); return }
        if (!name.trim()) { toast.error('Please enter a name'); return }
        try {
            isUploading = true
            const dataset = await uploadDataset(name.trim(), description.trim(), file)
            toast.success('Dataset uploaded')
            name = ''
            description = ''
            file = null
            onUploaded(dataset)
            onOpenChange(false)
        } catch (err) {
            toast.error('Failed to upload dataset')
            console.error(err)
        } finally {
            isUploading = false
        }
    }
</script>

<Dialog.Root open={isOpen} onOpenChange={(open) => { if (!open) onOpenChange(false) }}>
    <Dialog.Content class="max-w-md">
        <Dialog.Header>
            <Dialog.Title>Upload Dataset</Dialog.Title>
            <Dialog.Description>
                CSV, JSONL, or Parquet. Column names must match the input fields of the workflows you
                want to batch-run.
            </Dialog.Description>
        </Dialog.Header>

        <div class="space-y-4 py-2">
            <div>
                <label for="dataset-file" class="block text-sm font-medium mb-1.5">File</label>
                <input
                    id="dataset-file"
                    type="file"
                    accept=".csv,.jsonl,.parquet"
                    onchange={handleFileChange}
                    class="w-full text-sm file:mr-3 file:px-3 file:py-1.5 file:rounded-md file:border-0 file:bg-muted file:text-sm file:font-medium hover:file:bg-muted/80 cursor-pointer"
                />
            </div>
            <div>
                <label for="dataset-name" class="block text-sm font-medium mb-1.5">Name</label>
                <input
                    id="dataset-name"
                    type="text"
                    bind:value={name}
                    placeholder="My dataset"
                    class="w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                />
            </div>
            <div>
                <label for="dataset-description" class="block text-sm font-medium mb-1.5">Description (optional)</label>
                <textarea
                    id="dataset-description"
                    bind:value={description}
                    rows={2}
                    class="w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring resize-none"
                ></textarea>
            </div>
        </div>

        <Dialog.Footer>
            <Button variant="ghost" onclick={() => onOpenChange(false)}>Cancel</Button>
            <Button onclick={handleUpload} disabled={isUploading || !file}>
                {isUploading ? 'Uploading...' : 'Upload'}
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
