<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { page } from '$app/stores'
    import { goto } from '$app/navigation'
    import { onMount } from 'svelte'
    import { toast } from 'svelte-sonner'
    import { formatDistanceToNow } from 'date-fns'
    import Icon from '@iconify/svelte'
    import Header from '$lib/components/Header.svelte'
    import LoadingSpinner from '$lib/components/LoadingSpinner.svelte'
    import BatchRunModal from '$lib/components/modals/BatchRunModal.svelte'
    import { Button } from '$lib/components/ui/button'
    import { getDataset, listDatasetRuns, downloadOutputFile } from '$lib/utils/api'
    import { getStatusConfig } from '$lib/utils/statusConfig'
    import type { DatasetResponse } from '$lib/types/api_types/datasetSchemas'
    import type { RunResponse } from '$lib/types/api_types/runSchemas'

    const datasetId = $derived($page.params.id)

    let dataset = $state<DatasetResponse | null>(null)
    let runs = $state<RunResponse[]>([])
    let isLoading = $state(true)
    let error = $state<string | null>(null)
    let isBatchRunOpen = $state(false)
    let downloadingId = $state<string | null>(null)

    onMount(async () => {
        if (!datasetId) return
        try {
            const [ds, runList] = await Promise.all([getDataset(datasetId), listDatasetRuns(datasetId)])
            dataset = ds
            runs = runList
        } catch {
            error = 'Failed to load dataset'
        } finally {
            isLoading = false
        }
    })

    async function refreshRuns() {
        if (!datasetId) return
        try {
            runs = await listDatasetRuns(datasetId)
        } catch {
            /* keep previous runs on transient errors */
        }
    }

    // Poll runs every 5s while any batch run is still in flight
    const hasActiveRuns = $derived(runs.some((r) => r.status === 'RUNNING' || r.status === 'PENDING'))
    $effect(() => {
        if (!hasActiveRuns) return
        const interval = setInterval(refreshRuns, 5000)
        return () => clearInterval(interval)
    })

    async function handleDownload(run: RunResponse) {
        if (!run.output_file_id) return
        try {
            downloadingId = run.id
            await downloadOutputFile(run.output_file_id)
        } catch {
            toast.error('Failed to download output file')
        } finally {
            downloadingId = null
        }
    }

    const basename = (path: string) => path.split('/').pop() ?? path
</script>

<svelte:head>
    <title>{dataset?.name ?? 'Dataset'} - Faraflow</title>
</svelte:head>

<div class="min-h-screen flex flex-col">
    <Header activePage="datasets" />

    <div class="max-w-5xl mx-auto w-full px-6 py-6 flex-1">
        {#if isLoading}
            <LoadingSpinner />
        {:else if error || !dataset}
            <p class="text-destructive">{error ?? 'Dataset not found'}</p>
        {:else}
            <div class="flex items-start justify-between mb-6">
                <div class="flex items-center gap-3">
                    <button
                        onclick={() => goto('/datasets')}
                        aria-label="Back to datasets"
                        class="p-2 rounded hover:bg-muted transition-colors"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 19-7-7 7-7"/><path d="M19 12H5"/></svg>
                    </button>
                    <div>
                        <h1 class="text-2xl font-bold">{dataset.name}</h1>
                        {#if dataset.description}
                            <p class="text-sm text-muted-foreground mt-0.5">{dataset.description}</p>
                        {/if}
                    </div>
                </div>
                <Button onclick={() => (isBatchRunOpen = true)}>Start Batch Run</Button>
            </div>

            <div class="grid grid-cols-2 gap-4 mb-6">
                <div class="border border-border rounded-xl p-4">
                    <p class="text-sm text-muted-foreground">File</p>
                    <p class="font-mono text-sm mt-1">{basename(dataset.filename)}</p>
                </div>
                <div class="border border-border rounded-xl p-4">
                    <p class="text-sm text-muted-foreground">Uploaded</p>
                    <p class="font-medium mt-1">
                        {formatDistanceToNow(new Date(dataset.created_at), { addSuffix: true })}
                    </p>
                </div>
            </div>

            <h2 class="text-lg font-semibold mb-3">Batch Runs</h2>
            {#if runs.length === 0}
                <p class="text-muted-foreground text-sm py-4">
                    No runs have used this dataset yet. Start a batch run to process every row.
                </p>
            {:else}
                <div class="border border-border rounded-xl overflow-hidden">
                    <table class="w-full text-sm">
                        <thead class="bg-muted/50 text-left">
                            <tr>
                                <th class="px-4 py-3 font-medium">Run ID</th>
                                <th class="px-4 py-3 font-medium">Status</th>
                                <th class="px-4 py-3 font-medium">Started</th>
                                <th class="px-4 py-3 font-medium text-right">Output</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each runs as run (run.id)}
                                {@const status = getStatusConfig(run.status)}
                                <tr class="border-t border-border hover:bg-muted/30 transition-colors">
                                    <td class="px-4 py-3">
                                        <a href={`/trace/${run.id}`} class="font-mono text-xs text-primary hover:underline">
                                            {run.id}
                                        </a>
                                    </td>
                                    <td class="px-4 py-3">
                                        <span class="inline-flex items-center gap-1.5" style="color: {status.color}">
                                            <Icon icon={status.icon} width={14} class={status.spin ? 'animate-spin' : ''} />
                                            {status.label}
                                        </span>
                                    </td>
                                    <td class="px-4 py-3 text-muted-foreground">
                                        {run.start_time
                                            ? formatDistanceToNow(new Date(run.start_time), { addSuffix: true })
                                            : '—'}
                                    </td>
                                    <td class="px-4 py-3 text-right">
                                        {#if run.output_file_id}
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                disabled={downloadingId === run.id}
                                                onclick={() => handleDownload(run)}
                                            >
                                                {downloadingId === run.id ? 'Downloading...' : 'Download'}
                                            </Button>
                                        {:else}
                                            <span class="text-xs text-muted-foreground">—</span>
                                        {/if}
                                    </td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                </div>
            {/if}
        {/if}
    </div>
</div>

{#if datasetId}
    <BatchRunModal
        isOpen={isBatchRunOpen}
        onOpenChange={(open) => (isBatchRunOpen = open)}
        {datasetId}
        onStarted={refreshRuns}
    />
{/if}
