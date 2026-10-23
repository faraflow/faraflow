<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import Icon from '@iconify/svelte'
    import { formatDistanceStrict } from 'date-fns'
    import { goto } from '$app/navigation'
    import { page } from '$app/stores'
    import { executionState, loadRunIntoCanvas, fetchWorkflowRuns } from '$lib/actions/workflowExecution.svelte'
    import { flowStore } from '$lib/stores/flow.svelte'
    import type { RunResponse } from '$lib/types/api_types/runSchemas'
    import { getStatusConfig } from '$lib/utils/statusConfig'

    interface Props {
        onclose: () => void
    }

    let { onclose }: Props = $props()

    const runs: RunResponse[] = $derived(executionState.workflowRuns)

    let search = $state('')

    const filteredRuns = $derived(
        search.trim()
            ? runs.filter(run => {
                  const q = search.trim().toLowerCase()
                  if (run.id.toLowerCase().includes(q)) return true
                  const vals = Object.values(run.initial_inputs ?? {})[0]
                  if (!vals) return false
                  return Object.values(vals).some(v => String(v).toLowerCase().includes(q))
              })
            : runs
    )

    function getInputEntries(run: RunResponse): [string, string][] {
        const vals = Object.values(run.initial_inputs ?? {})[0]
        if (!vals) return []
        return Object.entries(vals).map(([k, v]) => [k, String(v)])
    }

    const currentRun = $derived(runs.find(r => r.id === executionState.currentRunId) ?? null)

    let loadingRunId = $state<string | null>(null)
    let reloading = $state(false)

    async function reloadRuns() {
        reloading = true
        await fetchWorkflowRuns()
        reloading = false
    }

    async function handleRunClick(e: MouseEvent, run: RunResponse) {
        e.preventDefault()
        loadingRunId = run.id
        await loadRunIntoCanvas(run.id)
        loadingRunId = null
    }

    function formatRunTime(run: RunResponse): string {
        const s = run.status?.toLowerCase()
        if (['running', 'pending', 'paused'].includes(s) && run.start_time) {
            return `running for ${formatDistanceStrict(Date.parse(run.start_time + 'Z'), new Date())}`
        }
        if (['failed', 'completed', 'cancelled'].includes(s) && run.end_time) {
            return formatDistanceStrict(Date.parse(run.end_time + 'Z'), new Date(), { addSuffix: true })
        }
        if (run.start_time) {
            return formatDistanceStrict(Date.parse(run.start_time + 'Z'), new Date(), { addSuffix: true })
        }
        return ''
    }
</script>

<div class="flex flex-col flex-1 min-h-0 overflow-hidden bg-background">
    <!-- Header -->
    <div class="flex items-center justify-between px-3 border-b border-border shrink-0 bg-muted/30" style="height: 44px;">
        <h2 class="text-sm font-semibold">Runs</h2>
        <div class="flex items-center gap-1.5">
            {#if currentRun}
                {@const cfg = getStatusConfig(currentRun.status)}
                <button
                    type="button"
                    class="flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono font-medium border transition-colors hover:bg-muted"
                    style="color: {cfg.color}; border-color: {cfg.color}33;"
                    title="On canvas: {currentRun.id}"
                    onclick={() => {
                        if ($page.url.pathname.startsWith('/trace/')) {
                            document.getElementById(`run-${currentRun.id}`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
                        } else {
                            goto(`/trace/${currentRun.id}`)
                        }
                    }}
                >
                    <Icon icon={cfg.icon} width={11} class="{cfg.spin ? 'animate-spin' : ''}" style="color: {cfg.color};" />
                    {currentRun.id}
                </button>
            {/if}
            <button
                type="button"
                class="p-1.5 rounded hover:bg-muted transition-colors"
                title="Reload runs"
                onclick={reloadRuns}
            >
                <Icon icon="solar:refresh-linear" width={16} class="text-muted-foreground {reloading ? 'animate-spin' : ''}" />
            </button>
            <button
                type="button"
                class="p-1.5 rounded hover:bg-muted transition-colors"
                onclick={onclose}
            >
                <Icon icon="solar:close-circle-linear" width={18} class="text-muted-foreground" />
            </button>
        </div>
    </div>

    <!-- Search -->
    <div class="flex items-center gap-2 px-3 border-b border-border shrink-0 focus-within:bg-muted/50 transition-colors" style="height: 36px;">
        <Icon icon="solar:magnifer-linear" width={14} class="text-muted-foreground flex-shrink-0" />
        <input
            type="text"
            placeholder="Search by ID or input…"
            class="flex-1 bg-transparent text-xs outline-none placeholder:text-muted-foreground"
            bind:value={search}
        />
        {#if search}
            <button type="button" onclick={() => search = ''} class="text-muted-foreground hover:text-foreground">
                <Icon icon="solar:close-circle-bold" width={14} />
            </button>
        {/if}
    </div>

    <!-- Run list -->
    <div class="flex-1 overflow-y-auto px-2 py-1.5 space-y-1.5">
        {#if runs.length === 0}
            <p class="text-xs text-muted-foreground text-center py-4">No runs yet</p>
        {:else if filteredRuns.length === 0}
            <p class="text-xs text-muted-foreground text-center py-4">No matches</p>
        {:else}
            {#each filteredRuns as run (run.id)}
                {@const cfg = getStatusConfig(run.status)}
                {@const inputEntries = getInputEntries(run)}
                {@const isLoaded = executionState.currentRunId === run.id}
                {@const isLoading = loadingRunId === run.id}
                <button
                    id="run-{run.id}"
                    type="button"
                    class="w-full text-left px-3 py-2.5 rounded-lg border transition-all cursor-pointer bg-background hover:border-primary/50
                        {isLoaded ? 'border-primary/60 bg-primary/5' : 'border-border'}"
                    style={!isLoaded && run.status?.toUpperCase() === 'FAILED' ? `border-color: ${cfg.color}; border-width: 1.5px;` : ''}
                    title="Click to load onto canvas"
                    onclick={(e) => handleRunClick(e, run)}
                >
                    <div class="flex items-center justify-between gap-2 min-w-0">
                        <!-- Status icon + label + run ID + time -->
                        <div class="flex items-center gap-1.5 min-w-0 flex-1">
                            <Icon
                                icon={isLoading ? 'solar:refresh-bold' : cfg.icon}
                                width={14}
                                class="{(cfg.spin || isLoading) ? 'animate-spin flex-shrink-0' : 'flex-shrink-0'}"
                                style="color: {cfg.color};"
                            />
                            <span class="text-xs font-medium shrink-0" style="color: {cfg.color};">{cfg.label}</span>
                            <span class="text-xs font-mono text-muted-foreground shrink-0 whitespace-nowrap">
                                {run.id}{#if run.parent_run_id}<span class="text-muted-foreground/40"> / {run.parent_run_id}</span>{/if}
                            </span>
                            {#if formatRunTime(run)}
                                <span class="text-xs text-muted-foreground truncate">· {formatRunTime(run)}</span>
                            {/if}
                        </div>
                        <!-- Loaded badge or open trace icon -->
                        {#if isLoaded}
                            <span class="text-[10px] font-medium text-primary shrink-0">on canvas</span>
                        {:else}
                            <Icon icon="lucide:external-link" width={12} class="text-muted-foreground flex-shrink-0" />
                        {/if}
                    </div>

                    <!-- Input preview: one field per line, CSS truncation -->
                    {#if inputEntries.length > 0}
                        <div class="mt-1.5 space-y-0.5">
                            {#each inputEntries as [k, v]}
                                <p class="text-xs text-muted-foreground overflow-hidden text-ellipsis whitespace-nowrap opacity-75">
                                    <span class="opacity-70">{k}:</span> {v}
                                </p>
                            {/each}
                        </div>
                    {/if}
                </button>
            {/each}
        {/if}
    </div>

    <!-- Hint -->
    <div class="shrink-0 px-3 py-1.5 border-t border-border bg-muted/20">
        <p class="text-[10px] text-muted-foreground text-center">Click a run to load it onto the canvas</p>
    </div>

    <!-- Footer: see all runs -->
    {#if flowStore.workflowID}
        <div class="shrink-0 border-t border-border px-3 py-2">
            <a
                href="/runs/{flowStore.workflowID}"
                class="flex items-center justify-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
                See all runs
                <Icon icon="solar:arrow-right-linear" width={13} />
            </a>
        </div>
    {/if}
</div>
