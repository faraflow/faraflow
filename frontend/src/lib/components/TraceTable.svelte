<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import Icon from '@iconify/svelte'
    import { format, formatDistanceToNow, parseISO } from 'date-fns'
    import { goto } from '$app/navigation'
    import { Button } from '$lib/components/ui/button'
    import { Input } from '$lib/components/ui/input'
    import NodeOutputDisplay from '$lib/components/nodes/NodeOutputDisplay.svelte'
    import type { RunResponse, RunStatus } from '$lib/types/api_types/runSchemas'
    import { getWorkflowRuns } from '$lib/utils/api'

    interface Props {
        workflowId: string
    }

    let { workflowId }: Props = $props()

    let runs = $state<RunResponse[]>([])
    let isLoading = $state(true)
    let isLoadingMore = $state(false)
    let hasMoreRuns = $state(true)
    let page = $state(1)

    // Filter state
    let startDate = $state('')
    let endDate = $state('')
    let startTime = $state('00:00')
    let endTime = $state('23:59')
    let numRuns = $state('100')
    let selectedStatus = $state<RunStatus | ''>('')
    let inputSearch = $state('')

    const statusOptions: { label: string; value: RunStatus | '' }[] = [
        { label: 'All', value: '' },
        { label: 'Completed', value: 'COMPLETED' },
        { label: 'Running', value: 'RUNNING' },
        { label: 'Pending', value: 'PENDING' },
        { label: 'Failed', value: 'FAILED' },
        { label: 'Cancelled', value: 'CANCELLED' },
        { label: 'Paused', value: 'PAUSED' },
    ]

    function getStatusColor(status: RunStatus): string {
        switch (status) {
            case 'COMPLETED': return 'text-green-600 bg-green-50 dark:bg-green-950 dark:text-green-400'
            case 'RUNNING':
            case 'PENDING':
            case 'PAUSED': return 'text-yellow-600 bg-yellow-50 dark:bg-yellow-950 dark:text-yellow-400'
            case 'FAILED':
            case 'CANCELLED': return 'text-destructive bg-destructive/10'
            default: return 'text-muted-foreground bg-muted'
        }
    }

    function getStatusIcon(status: RunStatus): string {
        switch (status) {
            case 'COMPLETED': return 'solar:check-circle-linear'
            case 'RUNNING': return 'solar:running-linear'
            case 'PENDING': return 'solar:clock-circle-linear'
            case 'PAUSED': return 'solar:pause-circle-linear'
            case 'FAILED': return 'solar:danger-circle-linear'
            case 'CANCELLED': return 'solar:close-circle-linear'
            default: return 'solar:question-circle-linear'
        }
    }

    function formatDuration(startT?: string, endT?: string): string {
        if (!startT) return '-'
        const utcStart = startT.endsWith('Z') ? startT : startT + 'Z'
        const start = parseISO(utcStart)
        const end = endT ? parseISO(endT.endsWith('Z') ? endT : endT + 'Z') : new Date()
        const secs = (end.getTime() - start.getTime()) / 1000
        if (secs < 60) return `${Math.round(secs)}s`
        if (secs < 3600) return `${Math.floor(secs / 60)}m ${Math.round(secs % 60)}s`
        return `${Math.floor(secs / 3600)}h ${Math.floor((secs % 3600) / 60)}m`
    }

    function formatTimestamp(ts: string): { date: string; relative: string } {
        const utc = ts.endsWith('Z') ? ts : ts + 'Z'
        const d = parseISO(utc)
        return {
            date: format(d, "MMM d, yyyy HH:mm:ss 'UTC'"),
            relative: formatDistanceToNow(d, { addSuffix: true }),
        }
    }

    async function fetchRuns(isLoadMore = false) {
        try {
            const currentPage = isLoadMore ? page + 1 : 1
            if (isLoadMore) isLoadingMore = true
            else isLoading = true

            let start: Date | undefined
            let end: Date | undefined

            if (startDate) {
                const [h, m] = startTime.split(':').map(Number)
                const d = new Date(startDate)
                start = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate(), h, m))
            }
            if (endDate) {
                const [h, m] = endTime.split(':').map(Number)
                const d = new Date(endDate)
                end = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate(), h, m))
            }

            const fetched = await getWorkflowRuns(
                workflowId,
                currentPage,
                parseInt(numRuns),
                start,
                end,
                selectedStatus || undefined,
                inputSearch || undefined
            )

            const sorted = [...fetched].sort((a, b) => {
                const da = a.start_time ? new Date(a.start_time.endsWith('Z') ? a.start_time : a.start_time + 'Z').getTime() : 0
                const db = b.start_time ? new Date(b.start_time.endsWith('Z') ? b.start_time : b.start_time + 'Z').getTime() : 0
                return db - da
            })

            runs = isLoadMore ? [...runs, ...sorted] : sorted
            page = currentPage
            hasMoreRuns = fetched.length === parseInt(numRuns)
        } catch (err) {
            console.error('Error fetching runs:', err)
        } finally {
            isLoading = false
            isLoadingMore = false
        }
    }

    // Initial fetch + polling
    $effect(() => {
        fetchRuns()
        const id = setInterval(() => {
            const hasActive = runs.some((r) => r.status === 'RUNNING' || r.status === 'PENDING' || r.status === 'PAUSED')
            if (hasActive) fetchRuns()
        }, 5000)
        return () => clearInterval(id)
    })

    function handleApplyFilter() {
        page = 1
        fetchRuns()
    }

    function handleClearFilter() {
        startDate = ''
        endDate = ''
        startTime = '00:00'
        endTime = '23:59'
        numRuns = '100'
        selectedStatus = ''
        inputSearch = ''
        page = 1
    }

    function handleRunClick(runId: string) {
        window.open(`/trace/${runId}`, '_blank')
    }
</script>

<div class="flex flex-col gap-4">
    <!-- Filters -->
    <div class="flex flex-wrap gap-4 items-end">
        <div class="flex flex-col gap-1">
            <p class="text-sm text-muted-foreground">Start Date (UTC)</p>
            <Input type="date" class="min-w-[180px] h-8 text-sm" bind:value={startDate} />
        </div>
        <div class="flex flex-col gap-1">
            <p class="text-sm text-muted-foreground">Start Time (UTC)</p>
            <Input type="time" class="min-w-[130px] h-8 text-sm" bind:value={startTime} />
        </div>
        <div class="flex flex-col gap-1">
            <p class="text-sm text-muted-foreground">End Date (UTC)</p>
            <Input type="date" class="min-w-[180px] h-8 text-sm" bind:value={endDate} />
        </div>
        <div class="flex flex-col gap-1">
            <p class="text-sm text-muted-foreground">End Time (UTC)</p>
            <Input type="time" class="min-w-[130px] h-8 text-sm" bind:value={endTime} />
        </div>
        <div class="flex flex-col gap-1">
            <p class="text-sm text-muted-foreground">Max Runs</p>
            <select
                class="text-sm border border-border rounded-md px-2 py-1.5 bg-background min-w-[110px] h-8"
                bind:value={numRuns}
            >
                <option value="10">10 runs</option>
                <option value="20">20 runs</option>
                <option value="100">100 runs</option>
                <option value="200">200 runs</option>
            </select>
        </div>
        <div class="flex flex-col gap-1">
            <p class="text-sm text-muted-foreground">Status</p>
            <select
                class="text-sm border border-border rounded-md px-2 py-1.5 bg-background min-w-[140px] h-8"
                bind:value={selectedStatus}
            >
                {#each statusOptions as opt}
                    <option value={opt.value}>{opt.label}</option>
                {/each}
            </select>
        </div>
        <div class="flex flex-col gap-1">
            <p class="text-sm text-muted-foreground">Input Search</p>
            <Input type="text" placeholder="Search inputs…" class="min-w-[180px] h-8 text-sm" bind:value={inputSearch} />
        </div>
        <div class="flex gap-2">
            <Button size="sm" onclick={handleApplyFilter}>Apply Filter</Button>
            <Button size="sm" variant="outline" onclick={handleClearFilter}>Clear</Button>
        </div>
    </div>

    <!-- Table -->
    {#if isLoading}
        <div class="flex justify-center p-8">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
    {:else if runs.length === 0}
        <div class="flex justify-center p-8 text-muted-foreground">No runs found for this flow</div>
    {:else}
        <div class="rounded-lg border border-border overflow-hidden">
            <table class="w-full text-sm">
                <thead class="bg-muted/50">
                    <tr>
                        <th class="px-4 py-3 text-left font-medium text-muted-foreground">Run ID</th>
                        <th class="px-4 py-3 text-left font-medium text-muted-foreground">Time (UTC)</th>
                        <th class="px-4 py-3 text-left font-medium text-muted-foreground">Inputs</th>
                        <th class="px-4 py-3 text-left font-medium text-muted-foreground">Duration</th>
                        <th class="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-border">
                    {#each runs as run}
                        {@const ts = run.start_time ? formatTimestamp(run.start_time) : null}
                        <tr class="hover:bg-muted/30 transition-colors">
                            <td class="px-4 py-3">
                                <button
                                    type="button"
                                    class="font-mono text-xs px-2 py-1 rounded bg-muted hover:bg-muted/70 transition-colors cursor-pointer"
                                    onclick={() => handleRunClick(run.id)}
                                >
                                    {run.id}
                                </button>
                            </td>
                            <td class="px-4 py-3">
                                {#if ts}
                                    <div class="flex flex-col">
                                        <span>{ts.date}</span>
                                        <span class="text-xs text-muted-foreground">{ts.relative}</span>
                                    </div>
                                {:else}
                                    <span class="text-muted-foreground">-</span>
                                {/if}
                            </td>
                            <td class="px-4 py-3 max-w-[200px]">
                                {#if run.initial_inputs}
                                    <div class="border rounded overflow-hidden">
                                        <NodeOutputDisplay
                                            output={Object.values(run.initial_inputs)[0] || {}}
                                            maxHeight="100px"
                                        />
                                    </div>
                                {:else}
                                    <span class="text-muted-foreground text-xs">No inputs</span>
                                {/if}
                            </td>
                            <td class="px-4 py-3 text-muted-foreground">
                                {formatDuration(run.start_time, run.end_time)}
                            </td>
                            <td class="px-4 py-3">
                                <span class="inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium {getStatusColor(run.status)}">
                                    <Icon icon={getStatusIcon(run.status)} width={12} />
                                    {run.status}
                                </span>
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>

        {#if hasMoreRuns}
            <div class="flex justify-center mt-2">
                <Button variant="outline" size="sm" onclick={() => fetchRuns(true)} disabled={isLoadingMore}>
                    {#if isLoadingMore}
                        Loading...
                    {:else}
                        <Icon icon="lucide:plus" width={14} class="mr-1" />
                        Load More
                    {/if}
                </Button>
            </div>
        {/if}
    {/if}
</div>
