<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { onMount } from 'svelte'
    import { goto } from '$app/navigation'
    import { toast } from 'svelte-sonner'
    import { formatDistanceToNow } from 'date-fns'
    import Header from '$lib/components/Header.svelte'
    import LoadingSpinner from '$lib/components/LoadingSpinner.svelte'
    import ConfirmationModal from '$lib/components/modals/ConfirmationModal.svelte'
    import UploadDatasetModal from '$lib/components/modals/UploadDatasetModal.svelte'
    import { Button } from '$lib/components/ui/button'
    import { listDatasets, deleteDataset } from '$lib/utils/api'
    import type { DatasetResponse } from '$lib/types/api_types/datasetSchemas'

    let datasets = $state<DatasetResponse[]>([])
    let isLoading = $state(true)
    let isUploadOpen = $state(false)
    let deleteTarget = $state<DatasetResponse | null>(null)

    onMount(loadDatasets)

    async function loadDatasets() {
        try {
            isLoading = true
            const result = await listDatasets()
            datasets = [...result].sort(
                (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
            )
        } catch {
            toast.error('Failed to load datasets')
        } finally {
            isLoading = false
        }
    }

    async function handleDelete() {
        if (!deleteTarget) return
        try {
            await deleteDataset(deleteTarget.id)
            toast.success('Dataset deleted')
            deleteTarget = null
            await loadDatasets()
        } catch {
            toast.error('Failed to delete dataset')
        }
    }

    const basename = (path: string) => path.split('/').pop() ?? path
</script>

<svelte:head>
    <title>Datasets - Faraflow</title>
</svelte:head>

<div class="min-h-screen flex flex-col">
    <Header activePage="datasets" />

    <div class="max-w-5xl mx-auto w-full px-6 py-6 flex-1">
        <div class="flex items-center justify-between mb-6">
            <div>
                <h1 class="text-2xl font-bold">Datasets</h1>
                <p class="text-sm text-muted-foreground mt-0.5">
                    Upload tabular data and batch-run workflows over every row.
                </p>
            </div>
            <Button onclick={() => (isUploadOpen = true)}>Upload Dataset</Button>
        </div>

        {#if isLoading}
            <LoadingSpinner />
        {:else if datasets.length === 0}
            <div class="border border-dashed border-border rounded-xl py-16 text-center">
                <h2 class="text-lg font-semibold mb-1">No datasets yet</h2>
                <p class="text-sm text-muted-foreground mb-4">
                    Upload a CSV, JSONL, or Parquet file to batch-run workflows over it.
                </p>
                <Button onclick={() => (isUploadOpen = true)}>Upload your first dataset</Button>
            </div>
        {:else}
            <div class="border border-border rounded-xl overflow-hidden">
                <table class="w-full text-sm">
                    <thead class="bg-muted/50 text-left">
                        <tr>
                            <th class="px-4 py-3 font-medium">Name</th>
                            <th class="px-4 py-3 font-medium">Description</th>
                            <th class="px-4 py-3 font-medium">File</th>
                            <th class="px-4 py-3 font-medium">Created</th>
                            <th class="px-4 py-3 font-medium text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each datasets as ds (ds.id)}
                            <tr
                                class="border-t border-border hover:bg-muted/30 transition-colors cursor-pointer"
                                onclick={() => goto(`/datasets/${ds.id}`)}
                            >
                                <td class="px-4 py-3 font-medium">{ds.name}</td>
                                <td class="px-4 py-3 text-muted-foreground">{ds.description || '—'}</td>
                                <td class="px-4 py-3 font-mono text-xs text-muted-foreground">{basename(ds.filename)}</td>
                                <td class="px-4 py-3 text-muted-foreground">
                                    {formatDistanceToNow(new Date(ds.created_at), { addSuffix: true })}
                                </td>
                                <td class="px-4 py-3 text-right">
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onclick={(e: MouseEvent) => {
                                            e.stopPropagation()
                                            deleteTarget = ds
                                        }}
                                    >
                                        Delete
                                    </Button>
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        {/if}
    </div>
</div>

<UploadDatasetModal
    isOpen={isUploadOpen}
    onOpenChange={(open) => (isUploadOpen = open)}
    onUploaded={(ds) => goto(`/datasets/${ds.id}`)}
/>

<ConfirmationModal
    isOpen={deleteTarget !== null}
    onClose={() => (deleteTarget = null)}
    onConfirm={handleDelete}
    title="Delete Dataset"
    message={`Are you sure you want to delete "${deleteTarget?.name}"? This action cannot be undone.`}
    confirmText="Delete"
    isDanger={true}
/>
