<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { page } from '$app/stores'
    import { onMount } from 'svelte'
    import Header from '$lib/components/Header.svelte'
    import LoadingSpinner from '$lib/components/LoadingSpinner.svelte'
    import { Button } from '$lib/components/ui/button'
    import * as Dialog from '$lib/components/ui/dialog'
    import { getEvalRunStatus } from '$lib/utils/api'

    const evalRunId = $derived($page.params.id)

    interface PerExampleResult {
        example_id?: string
        task_id?: string
        prompt: string
        predicted_answer: string
        ground_truth_answer: string
        is_correct: boolean
    }

    interface EvalResults {
        run_id: string
        eval_name: string
        accuracy: number
        per_example_results: PerExampleResult[]
    }

    let results = $state<EvalResults | null>(null)
    let isLoading = $state(true)
    let error = $state<string | null>(null)
    let selectedPrompt = $state<string | null>(null)
    let isPromptOpen = $state(false)

    onMount(async () => {
        try {
            const data = await getEvalRunStatus(evalRunId)
            results = {
                run_id: data.run_id,
                eval_name: data.eval_name,
                accuracy: data.results.accuracy,
                per_example_results: data.results.subset_metrics?.default?.per_example_results ?? [],
            }
        } catch (err) {
            console.error('Error fetching eval results:', err)
            error = 'Failed to fetch eval results'
        } finally {
            isLoading = false
        }
    })
</script>

<svelte:head>
    <title>Eval Results - Faraflow</title>
</svelte:head>

<div class="min-h-screen flex flex-col">
    <Header activePage="evals" />

    <div class="max-w-7xl mx-auto w-full px-6 py-6 flex-1">
        {#if isLoading}
            <LoadingSpinner />
        {:else if error || !results}
            <p class="text-destructive">{error ?? 'No results available'}</p>
        {:else}
            <div class="flex items-center justify-between mb-6">
                <div>
                    <h1 class="text-2xl font-bold">Eval Run Results</h1>
                    <p class="text-sm text-muted-foreground mt-1">
                        Run: {results.run_id} &middot; Eval: {results.eval_name}
                    </p>
                </div>
                <span class="px-4 py-2 rounded-lg bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 font-semibold text-sm">
                    Accuracy: {(results.accuracy * 100).toFixed(1)}%
                </span>
            </div>

            <div class="border border-border rounded-xl overflow-hidden">
                <table class="w-full text-sm">
                    <thead class="bg-muted/50 border-b border-border">
                        <tr>
                            <th class="text-left px-4 py-3 font-medium">Example ID</th>
                            <th class="text-left px-4 py-3 font-medium w-2/5">Prompt</th>
                            <th class="text-left px-4 py-3 font-medium">Predicted</th>
                            <th class="text-left px-4 py-3 font-medium">Ground Truth</th>
                            <th class="text-left px-4 py-3 font-medium">Status</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-border">
                        {#each results.per_example_results as item, i (item.example_id ?? i)}
                            <tr class="hover:bg-muted/30 {i % 2 === 0 ? '' : 'bg-muted/10'}">
                                <td class="px-4 py-3 text-xs text-muted-foreground">{item.example_id ?? item.task_id}</td>
                                <td class="px-4 py-3">
                                    <div class="flex items-start gap-2">
                                        <div class="text-xs max-h-24 overflow-y-auto flex-1">{item.prompt}</div>
                                        <button
                                            onclick={() => { selectedPrompt = item.prompt; isPromptOpen = true }}
                                            class="p-1 rounded hover:bg-muted flex-none text-muted-foreground hover:text-foreground"
                                            title="Expand prompt"
                                        >
                                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" x2="14" y1="3" y2="10"/><line x1="3" x2="10" y1="21" y2="14"/></svg>
                                        </button>
                                    </div>
                                </td>
                                <td class="px-4 py-3 text-xs">{item.predicted_answer}</td>
                                <td class="px-4 py-3 text-xs">{item.ground_truth_answer}</td>
                                <td class="px-4 py-3">
                                    <span class="text-xs px-2 py-1 rounded-full font-medium
                                        {item.is_correct
                                            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                            : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'}">
                                        {item.is_correct ? 'Correct' : 'Incorrect'}
                                    </span>
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        {/if}
    </div>
</div>

<!-- Prompt expand dialog -->
<Dialog.Root bind:open={isPromptOpen}>
    <Dialog.Content class="max-w-3xl max-h-[80vh]">
        <Dialog.Header>
            <Dialog.Title>Prompt</Dialog.Title>
        </Dialog.Header>
        <div class="overflow-y-auto whitespace-pre-wrap text-sm py-2">
            {selectedPrompt}
        </div>
        <Dialog.Footer>
            <Button variant="ghost" onclick={() => (isPromptOpen = false)}>Close</Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
