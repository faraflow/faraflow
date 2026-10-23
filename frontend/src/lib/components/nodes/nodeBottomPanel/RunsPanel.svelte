<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import Icon from '@iconify/svelte'
    import { formatDistanceStrict, format } from 'date-fns'
    import { Button } from '$lib/components/ui/button'
    import { Input } from '$lib/components/ui/input'
    import { executionState, loadRunIntoCanvas } from '$lib/actions/workflowExecution.svelte'
    import { getWorkflowRuns } from '$lib/utils/api'
    import { flowStore } from '$lib/stores/flow.svelte'
    import type { RunListItem, RunStatus } from '$lib/types/api_types/runSchemas'
    import { getStatusConfig } from '$lib/utils/statusConfig'

    interface Props {
        readOnly?: boolean
        totalCount?: number
    }
    let { readOnly = false, totalCount = $bindable(0) }: Props = $props()

    const PAGE_SIZE = 50

    let runs = $state<RunListItem[]>([])
    let page = $state(1)
    let hasMore = $state(false)
    let loading = $state(false)
    let loadingMore = $state(false)
    let search = $state('')
    let statusFilter = $state<'all' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'PENDING'>('all')
    let loadingRunId = $state<string | null>(null)
    let wasRunning = false

    async function fetchPage(p: number, append = false) {
        const workflowId = flowStore.workflowID
        if (!workflowId) return
        if (append) loadingMore = true
        else loading = true
        try {
            const status = statusFilter !== 'all' ? statusFilter as RunStatus : undefined
            const q = search.trim() || undefined
            const result = await getWorkflowRuns(workflowId, p, PAGE_SIZE, undefined, undefined, status, q)
            if (append) {
                runs = [...runs, ...result]
            } else {
                runs = result
            }
            page = p
            hasMore = result.length === PAGE_SIZE
            totalCount = runs.length
        } catch (err) {
            console.error('Error loading runs:', err)
        } finally {
            loading = false
            loadingMore = false
        }
    }

    async function loadMore() {
        await fetchPage(page + 1, true)
    }

    // Reload on search/filter changes (debounced for search)
    let searchTimer: ReturnType<typeof setTimeout> | null = null
    $effect(() => {
        const q = search
        const sf = statusFilter
        const wfId = flowStore.workflowID
        if (searchTimer) clearTimeout(searchTimer)
        const delay = q !== '' ? 300 : 0
        searchTimer = setTimeout(() => fetchPage(1), delay)
        return () => { if (searchTimer) clearTimeout(searchTimer) }
    })

    // Reload when a run finishes
    $effect(() => {
        const nowRunning = executionState.isRunning
        if (wasRunning && !nowRunning) {
            setTimeout(() => fetchPage(1), 800)
        }
        wasRunning = nowRunning
    })

    function getInputEntries(run: RunListItem): [string, string][] {
        const vals = Object.values(run.initial_inputs ?? {})[0]
        if (!vals) return []
        return Object.entries(vals as Record<string, unknown>).map(([k, v]) => [k, String(v)])
    }

    function formatStartTime(isoStr?: string): string {
        if (!isoStr) return '—'
        try { return format(Date.parse(isoStr + 'Z'), 'MMM d, HH:mm:ss') }
        catch { return isoStr }
    }

    function formatDuration(run: RunListItem): string {
        const s = run.status?.toLowerCase()
        if (['running', 'pending', 'paused'].includes(s) && run.start_time) {
            return formatDistanceStrict(Date.parse(run.start_time + 'Z'), new Date())
        }
        if (run.start_time && run.end_time) {
            return formatDistanceStrict(Date.parse(run.start_time + 'Z'), Date.parse(run.end_time + 'Z'))
        }
        return '—'
    }

    function statusBadgeClass(status: string): string {
        switch (status?.toUpperCase()) {
            case 'COMPLETED': return 'text-green-700 dark:text-green-400 bg-green-500/10'
            case 'RUNNING':   return 'text-blue-700 dark:text-blue-400 bg-blue-500/10'
            case 'FAILED':    return 'text-red-700 dark:text-red-400 bg-red-500/10'
            case 'PAUSED':    return 'text-orange-700 dark:text-orange-400 bg-orange-500/10'
            case 'PENDING':   return 'text-yellow-700 dark:text-yellow-400 bg-yellow-500/10'
            default:          return 'text-muted-foreground bg-muted'
        }
    }

    async function handleRowClick(run: RunListItem) {
        if (loadingRunId) return
        loadingRunId = run.id
        await loadRunIntoCanvas(run.id)
        loadingRunId = null
    }

    const statusFilters = [
        ['all', 'All'] as const,
        ['RUNNING', 'Running'] as const,
        ['COMPLETED', 'Completed'] as const,
        ['FAILED', 'Failed'] as const,
        ['PENDING', 'Pending'] as const,
    ]
</script>

<div class="flex flex-col h-full min-h-0">
    <div class="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-0">

        <!-- Search + filter bar -->
        <div class="flex items-center gap-2 flex-wrap">
            <div class="relative flex-1 min-w-48">
                <Icon icon="solar:magnifer-linear" width={14} class="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
                <Input class="pl-8 h-8 text-sm" placeholder="Search by run ID or input value…" bind:value={search} />
            </div>
            <div class="flex items-center gap-1 shrink-0 flex-wrap">
                {#each statusFilters as [val, label]}
                    <button
                        type="button"
                        class="px-3 py-1 rounded-full text-xs font-medium border transition-colors
                            {statusFilter === val
                                ? 'bg-primary text-primary-foreground border-primary'
                                : 'bg-background text-muted-foreground border-border hover:bg-muted'}"
                        onclick={() => { statusFilter = val }}
                    >
                        {label}
                    </button>
                {/each}
            </div>
            <Button
                variant="ghost"
                size="icon"
                class="h-8 w-8 shrink-0"
                title="Reload runs"
                onclick={() => fetchPage(1)}
            >
                <Icon icon="solar:refresh-linear" width={15} class="text-muted-foreground {loading ? 'animate-spin' : ''}" />
            </Button>
        </div>

        <!-- Runs table -->
        {#if loading && runs.length === 0}
            <div class="flex items-center justify-center py-12 gap-2 text-muted-foreground">
                <Icon icon="solar:refresh-bold" width={20} class="animate-spin opacity-50" />
                <span class="text-sm">Loading runs…</span>
            </div>
        {:else if runs.length === 0}
            <div class="flex flex-col items-center justify-center py-12 gap-2 text-muted-foreground">
                <Icon icon="solar:history-linear" width={32} class="opacity-30" />
                <p class="text-sm">{search || statusFilter !== 'all' ? 'No runs match your search or filter.' : 'No runs yet. Run the workflow to see results here.'}</p>
            </div>
        {:else}
            <div class="border rounded-lg overflow-x-auto">
                <table class="w-full text-sm">
                    <thead class="bg-muted/50 border-b">
                        <tr>
                            <th class="px-3 py-2 text-left font-medium text-muted-foreground w-32">Status</th>
                            <th class="px-3 py-2 text-left font-medium text-muted-foreground w-20">Run ID</th>
                            <th class="px-3 py-2 text-left font-medium text-muted-foreground w-20">Parent</th>
                            <th class="px-3 py-2 text-left font-medium text-muted-foreground">Inputs</th>
                            <th class="px-3 py-2 text-left font-medium text-muted-foreground w-36">Started</th>
                            <th class="px-3 py-2 text-left font-medium text-muted-foreground w-24">Duration</th>
                            <th class="px-3 py-2 text-left font-medium text-muted-foreground w-20">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each runs as run (run.id)}
                            {@const cfg = getStatusConfig(run.status)}
                            {@const entries = getInputEntries(run)}
                            {@const isLoaded = executionState.currentRunId === run.id}
                            {@const isLoading = loadingRunId === run.id}
                            <tr
                                class="border-b last:border-0 cursor-pointer transition-colors
                                    {isLoaded ? 'bg-blue-500/10 dark:bg-blue-400/10' : 'hover:bg-muted/50'}"
                                onclick={() => handleRowClick(run)}
                                title="Click to load onto canvas"
                            >
                                <!-- Status -->
                                <td class="px-3 py-2">
                                    <span class="inline-flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded-full {statusBadgeClass(run.status)}">
                                        <Icon
                                            icon={isLoading ? 'solar:refresh-bold' : cfg.icon}
                                            width={12}
                                            class={(cfg.spin || isLoading) ? 'animate-spin' : ''}
                                        />
                                        {cfg.label}
                                    </span>
                                </td>
                                <!-- Run ID -->
                                <td class="px-3 py-2">
                                    <span class="font-mono text-muted-foreground">{run.id}</span>
                                </td>
                                <!-- Parent run ID -->
                                <td class="px-3 py-2">
                                    {#if run.parent_run_id}
                                        <button
                                            type="button"
                                            class="font-mono text-xs text-muted-foreground/60 hover:text-foreground transition-colors"
                                            title="Load parent run onto canvas"
                                            onclick={(e) => { e.stopPropagation(); handleRowClick({ ...run, id: run.parent_run_id! }) }}
                                        >
                                            {run.parent_run_id}
                                        </button>
                                    {:else}
                                        <span class="text-muted-foreground/30">—</span>
                                    {/if}
                                </td>
                                <!-- Inputs -->
                                <td class="px-3 py-2">
                                    {#if entries.length > 0}
                                        <div class="flex flex-wrap gap-x-3 gap-y-0.5">
                                            {#each entries as [k, v]}
                                                <span class="text-sm text-muted-foreground break-all">
                                                    <span class="opacity-60 font-medium">{k}:</span>
                                                    <span> {v}</span>
                                                </span>
                                            {/each}
                                        </div>
                                    {:else}
                                        <span class="text-muted-foreground/50">—</span>
                                    {/if}
                                </td>
                                <!-- Started -->
                                <td class="px-3 py-2 text-muted-foreground whitespace-nowrap">
                                    {formatStartTime(run.start_time)}
                                </td>
                                <!-- Duration -->
                                <td class="px-3 py-2 text-muted-foreground whitespace-nowrap">
                                    {formatDuration(run)}
                                </td>
                                <!-- Actions -->
                                <td class="px-3 py-2">
                                    <div class="flex items-center gap-0.5">
                                        {#if isLoaded}
                                            <span class="text-[10px] font-medium text-blue-600 dark:text-blue-400 px-1.5 whitespace-nowrap">on canvas</span>
                                        {:else}
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                class="h-7 w-7"
                                                title="View trace"
                                                onclick={(e) => {
                                                    e.stopPropagation()
                                                    window.open(`/trace/${run.id}`, '_blank')
                                                }}
                                            >
                                                <Icon icon="solar:eye-linear" width={14} />
                                            </Button>
                                        {/if}
                                    </div>
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>

            <!-- Load More -->
            {#if hasMore}
                <div class="flex justify-center py-2">
                    <Button
                        variant="outline"
                        size="sm"
                        class="text-xs"
                        disabled={loadingMore}
                        onclick={loadMore}
                    >
                        {#if loadingMore}
                            <Icon icon="solar:refresh-bold" width={12} class="mr-1.5 animate-spin" />
                            Loading…
                        {:else}
                            Load more
                        {/if}
                    </Button>
                </div>
            {/if}
        {/if}
    </div>
</div>
