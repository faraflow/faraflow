<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { page } from '$app/stores'
    import { goto } from '$app/navigation'
    import { onMount } from 'svelte'
    import { formatDistanceToNow } from 'date-fns'
    import { diffLines, type Change } from 'diff'
    import Header from '$lib/components/Header.svelte'
    import { Button } from '$lib/components/ui/button'
    import { getWorkflowVersions } from '$lib/utils/api'
    import type { WorkflowVersionResponse } from '$lib/types/api_types/workflowSchemas'

    const workflowId = $derived($page.params.id)

    let versions = $state<WorkflowVersionResponse[]>([])
    let isLoading = $state(true)
    let leftVersion = $state<number | null>(null)
    let rightVersion = $state<number | null>(null)

    onMount(async () => {
        try {
            const fetched = await getWorkflowVersions(workflowId)
            versions = fetched

            const leftParam = $page.url.searchParams.get('left')
            const rightParam = $page.url.searchParams.get('right')

            if (leftParam && rightParam) {
                leftVersion = parseInt(leftParam)
                rightVersion = parseInt(rightParam)
            } else if (fetched.length >= 2) {
                leftVersion = fetched[1].version
                rightVersion = fetched[0].version
            }
        } catch (err) {
            console.error('Error fetching versions:', err)
        } finally {
            isLoading = false
        }
    })

    const leftDef = $derived(versions.find((v) => v.version === leftVersion))
    const rightDef = $derived(versions.find((v) => v.version === rightVersion))

    const diffResult = $derived.by((): Change[] => {
        if (!leftDef || !rightDef) return []
        const oldStr = JSON.stringify(leftDef.definition, null, 2)
        const newStr = JSON.stringify(rightDef.definition, null, 2)
        return diffLines(oldStr, newStr)
    })

    function versionLabel(v: WorkflowVersionResponse, index: number): string {
        const age = formatDistanceToNow(new Date(v.created_at), { addSuffix: true })
        return `${index === 0 ? 'Current Version' : `Version ${v.version}`} (${age})`
    }
</script>

<svelte:head>
    <title>Version Diff - Faraflow</title>
</svelte:head>

<div class="flex flex-col h-screen">
    <Header activePage="trace" associatedWorkflowId={workflowId} />

    <div class="flex-1 p-6 overflow-auto">
        <div class="max-w-7xl mx-auto space-y-6">
            <div class="flex items-center justify-between">
                <h1 class="text-2xl font-bold">Compare Workflow Versions</h1>
                <Button variant="outline" onclick={() => goto(`/workflows/${workflowId}`)}>
                    Back to Workflow
                </Button>
            </div>

            {#if isLoading}
                <div class="flex justify-center items-center h-64">
                    <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-primary"></div>
                </div>
            {:else}
                <!-- Version selectors -->
                <div class="border border-border rounded-xl p-4">
                    <div class="flex gap-4">
                        <div class="flex-1">
                            <p class="text-sm font-medium mb-1.5">Base Version</p>
                            <select
                                class="text-sm border border-border rounded-md px-2 py-1.5 bg-background w-full"
                                value={leftVersion?.toString() ?? ''}
                                onchange={(e) => (leftVersion = parseInt((e.target as HTMLSelectElement).value))}
                            >
                                <option value="">Select a version</option>
                                {#each versions as v, i}
                                    <option value={v.version.toString()}>{versionLabel(v, i)}</option>
                                {/each}
                            </select>
                        </div>
                        <div class="flex-1">
                            <p class="text-sm font-medium mb-1.5">Compare Version</p>
                            <select
                                class="text-sm border border-border rounded-md px-2 py-1.5 bg-background w-full"
                                value={rightVersion?.toString() ?? ''}
                                onchange={(e) => (rightVersion = parseInt((e.target as HTMLSelectElement).value))}
                            >
                                <option value="">Select a version</option>
                                {#each versions as v, i}
                                    <option value={v.version.toString()}>{versionLabel(v, i)}</option>
                                {/each}
                            </select>
                        </div>
                    </div>
                </div>

                <!-- Diff view -->
                {#if leftDef && rightDef && diffResult.length > 0}
                    <div class="border border-border rounded-xl overflow-hidden">
                        <div class="flex text-xs font-mono bg-muted/50 border-b border-border">
                            <div class="flex-1 px-4 py-2 font-medium">
                                {versionLabel(leftDef, versions.indexOf(leftDef))}
                            </div>
                            <div class="flex-1 px-4 py-2 font-medium border-l border-border">
                                {versionLabel(rightDef, versions.indexOf(rightDef))}
                            </div>
                        </div>
                        <div class="overflow-x-auto">
                            <table class="w-full text-xs font-mono">
                                <tbody>
                                    {#each diffResult as part}
                                        {#each (part.value || '').split('\n').filter((_, i, arr) => i < arr.length - 1 || part.value.endsWith('\n') || i === 0) as line, lineIdx}
                                            {#if line !== undefined}
                                                <tr class="{part.added ? 'bg-green-50 dark:bg-green-950/30' : part.removed ? 'bg-red-50 dark:bg-red-950/30' : ''}">
                                                    <td class="px-4 py-0.5 whitespace-pre select-text {part.added ? 'text-green-700 dark:text-green-400' : part.removed ? 'text-red-700 dark:text-red-400' : 'text-foreground'}">
                                                        {part.added ? '+' : part.removed ? '-' : ' '} {line}
                                                    </td>
                                                </tr>
                                            {/if}
                                        {/each}
                                    {/each}
                                </tbody>
                            </table>
                        </div>
                    </div>
                {:else if leftDef && rightDef}
                    <div class="text-center py-8 text-muted-foreground border border-border rounded-xl">
                        No differences between these versions
                    </div>
                {/if}
            {/if}
        </div>
    </div>
</div>
