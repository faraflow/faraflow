<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { onMount, onDestroy } from 'svelte'
    import { goto } from '$app/navigation'
    import { toast } from 'svelte-sonner'
    import Header from '$lib/components/Header.svelte'
    import LoadingSpinner from '$lib/components/LoadingSpinner.svelte'
    import EvalCard from '$lib/components/cards/EvalCard.svelte'
    import { getEvals, listEvalRuns, getEvalRunStatus, startEvalRun } from '$lib/utils/api'

    interface EvalItem {
        name: string
        description: string
        type: string
        num_samples: number
        paper_link?: string
    }

    interface EvalRun {
        run_id: string
        eval_name: string
        workflow_id: string
        status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'
        results?: { accuracy?: number; [key: string]: any }
    }

    let evals = $state<EvalItem[]>([])
    let evalRuns = $state<EvalRun[]>([])
    let isLoading = $state(true)
    let pollInterval: ReturnType<typeof setInterval>

    const statusColors: Record<string, string> = {
        PENDING: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
        RUNNING: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
        COMPLETED: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
        FAILED: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    }

    onMount(async () => {
        await Promise.all([fetchEvals(), fetchEvalRuns()])
        pollInterval = setInterval(fetchEvalRuns, 5000)
    })

    onDestroy(() => {
        clearInterval(pollInterval)
    })

    async function fetchEvals() {
        try {
            evals = await getEvals()
        } catch (err) {
            toast.error('Failed to load evals')
        } finally {
            isLoading = false
        }
    }

    async function fetchEvalRuns() {
        try {
            const runs: EvalRun[] = await listEvalRuns()
            const enriched = await Promise.all(
                runs.map(async (run) => {
                    if (run.status === 'COMPLETED') {
                        try {
                            const data = await getEvalRunStatus(run.run_id)
                            return { ...run, results: data.results }
                        } catch { return run }
                    }
                    return run
                })
            )
            evalRuns = enriched
        } catch (err) {
            console.error('Error fetching eval runs:', err)
        }
    }

    async function handleLaunchEval(workflowId: string, evalName: string, numSamples: number, outputVariable: string) {
        if (!workflowId || !outputVariable) { toast.error('Missing required fields'); return }
        try {
            const run = await startEvalRun(workflowId, evalName, outputVariable, numSamples)
            toast.success('Eval run started')
            evalRuns = [...evalRuns, run as unknown as EvalRun]
        } catch {
            toast.error('Failed to launch eval')
        }
    }
</script>

<svelte:head>
    <title>Evals - Faraflow</title>
</svelte:head>

<div class="min-h-screen flex flex-col">
    <Header activePage="evals" />

    <div class="max-w-7xl mx-auto w-full px-6 py-6 flex-1">
        <!-- Eval Runs -->
        <h1 class="text-2xl font-bold mb-4">Eval Jobs</h1>
        {#if evalRuns.length > 0}
            <div class="border border-border rounded-xl overflow-hidden mb-10">
                <table class="w-full text-sm">
                    <thead class="bg-muted/50 border-b border-border">
                        <tr>
                            <th class="text-left px-4 py-3 font-medium">Run ID</th>
                            <th class="text-left px-4 py-3 font-medium">Eval Name</th>
                            <th class="text-left px-4 py-3 font-medium">Workflow ID</th>
                            <th class="text-left px-4 py-3 font-medium">Status</th>
                            <th class="text-left px-4 py-3 font-medium">Accuracy</th>
                            <th class="text-left px-4 py-3 font-medium">Actions</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-border">
                        {#each evalRuns as run (run.run_id)}
                            <tr class="hover:bg-muted/30">
                                <td class="px-4 py-3 font-mono text-xs">{run.run_id.slice(0, 12)}...</td>
                                <td class="px-4 py-3">{run.eval_name}</td>
                                <td class="px-4 py-3 font-mono text-xs text-muted-foreground">{run.workflow_id.slice(0, 12)}...</td>
                                <td class="px-4 py-3">
                                    <span class="text-xs px-2 py-1 rounded-full font-medium {statusColors[run.status] || ''}">
                                        {#if run.status === 'RUNNING'}
                                            <span class="inline-flex items-center gap-1.5">
                                                <span class="animate-spin h-2.5 w-2.5 border-2 border-current border-t-transparent rounded-full inline-block"></span>
                                                {run.status}
                                            </span>
                                        {:else}
                                            {run.status}
                                        {/if}
                                    </span>
                                </td>
                                <td class="px-4 py-3">
                                    {#if run.results?.accuracy !== undefined}
                                        <div class="flex items-center gap-2">
                                            <div class="w-8 h-8 relative flex items-center justify-center">
                                                <svg viewBox="0 0 36 36" class="w-8 h-8 -rotate-90">
                                                    <circle cx="18" cy="18" r="14" fill="none" stroke="currentColor" stroke-width="4" class="text-muted/30"/>
                                                    <circle
                                                        cx="18" cy="18" r="14" fill="none" stroke="currentColor" stroke-width="4"
                                                        class="text-green-500"
                                                        stroke-dasharray="{run.results.accuracy * 87.96} 87.96"
                                                    />
                                                </svg>
                                                <span class="absolute text-[9px] font-bold rotate-90">{(run.results.accuracy * 100).toFixed(0)}%</span>
                                            </div>
                                        </div>
                                    {:else if run.status === 'COMPLETED'}
                                        N/A
                                    {:else}
                                        --
                                    {/if}
                                </td>
                                <td class="px-4 py-3">
                                    {#if run.status === 'COMPLETED'}
                                        <button
                                            onclick={() => goto(`/evals/${run.run_id}`)}
                                            class="text-xs px-3 py-1 rounded border border-border hover:bg-muted transition-colors"
                                        >
                                            View Examples
                                        </button>
                                    {:else}
                                        <span class="text-muted-foreground">--</span>
                                    {/if}
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        {:else}
            <p class="text-muted-foreground mb-10">No eval runs available.</p>
        {/if}

        <!-- Available Evals -->
        <h1 class="text-2xl font-bold mb-4">Available Evals</h1>
        {#if isLoading}
            <LoadingSpinner />
        {:else if evals.length > 0}
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {#each evals as evalItem (evalItem.name)}
                    <EvalCard
                        title={evalItem.name}
                        description={evalItem.description}
                        type={evalItem.type}
                        numSamples={evalItem.num_samples}
                        paperLink={evalItem.paper_link}
                        onRun={(workflowId, n, outputVar) => handleLaunchEval(workflowId, evalItem.name, n, outputVar)}
                    />
                {/each}
            </div>
        {:else}
            <p class="text-muted-foreground">No evals available.</p>
        {/if}
    </div>
</div>
