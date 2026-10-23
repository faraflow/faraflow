<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { getWorkflows, getWorkflowOutputVariables, startEvalRun } from '$lib/utils/api'
    import { toast } from 'svelte-sonner'
    import * as Dialog from '$lib/components/ui/dialog'
    import { Button } from '$lib/components/ui/button'

    interface Props {
        title: string
        description: string
        type: string
        numSamples: number
        paperLink?: string
        onRun?: (workflowId: string, numSamples: number, outputVariable: string) => Promise<void>
    }

    let { title, description, type, numSamples, paperLink, onRun }: Props = $props()

    let isModalOpen = $state(false)
    let workflows = $state<{ id: string; name: string }[]>([])
    let selectedWorkflowId = $state('')
    let outputVariables = $state<{ node_id: string; variable_name: string; prefixed_variable: string }[]>([])
    let selectedOutputVariable = $state('')
    let selectedNumSamples = $state(1)
    let isRunning = $state(false)

    $effect(() => {
        if (isModalOpen) {
            loadWorkflows()
        }
    })

    $effect(() => {
        if (selectedWorkflowId) {
            loadOutputVariables(selectedWorkflowId)
        } else {
            outputVariables = []
            selectedOutputVariable = ''
        }
    })

    async function loadWorkflows() {
        try {
            workflows = await getWorkflows()
        } catch (err) {
            toast.error('Failed to load workflows')
        }
    }

    async function loadOutputVariables(workflowId: string) {
        try {
            outputVariables = await getWorkflowOutputVariables(workflowId)
            selectedOutputVariable = ''
        } catch (err) {
            toast.error('Failed to load output variables')
        }
    }

    async function handleRunEval() {
        if (!selectedWorkflowId) { toast.error('Please select a workflow'); return }
        if (!selectedOutputVariable) { toast.error('Please select an output variable'); return }

        try {
            isRunning = true
            if (onRun) {
                await onRun(selectedWorkflowId, selectedNumSamples, selectedOutputVariable)
            } else {
                const result = await startEvalRun(selectedWorkflowId, title, selectedOutputVariable, selectedNumSamples)
                toast.success(`Eval run started: ${result.run_id}`)
            }
            isModalOpen = false
        } catch (err) {
            toast.error('Failed to start eval run')
        } finally {
            isRunning = false
        }
    }

    // Group output variables by node_id
    const groupedVariables = $derived.by(() => {
        const groups: Record<string, typeof outputVariables> = {}
        for (const v of outputVariables) {
            if (!groups[v.node_id]) groups[v.node_id] = []
            groups[v.node_id].push(v)
        }
        return groups
    })
</script>

<div class="border border-border rounded-xl overflow-hidden flex flex-col">
    <div class="p-6 flex-1 bg-gradient-to-br from-background to-muted/30">
        <h2 class="text-lg font-semibold mb-2">{title}</h2>
        <p class="text-muted-foreground text-sm mb-3">{description}</p>
        <p class="text-sm text-muted-foreground"><strong>Type:</strong> {type}</p>
        <p class="text-sm text-muted-foreground"><strong>Samples:</strong> {numSamples}</p>
        {#if paperLink}
            <a href={paperLink} target="_blank" rel="noopener noreferrer" class="text-primary text-sm hover:underline mt-2 inline-block">
                Original Paper
            </a>
        {/if}
    </div>
    <div class="border-t border-border p-3 flex justify-end">
        <Button variant="outline" size="sm" onclick={() => (isModalOpen = true)}>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="mr-2"><polygon points="6 3 20 12 6 21 6 3"/></svg>
            Run Eval
        </Button>
    </div>
</div>

<Dialog.Root bind:open={isModalOpen}>
    <Dialog.Content class="max-w-md">
        <Dialog.Header>
            <Dialog.Title>Eval Configuration</Dialog.Title>
        </Dialog.Header>

        <div class="space-y-4 py-2">
            <!-- Workflow selector -->
            <div>
                <label class="text-sm font-medium block mb-1.5">Select a Workflow</label>
                <select
                    bind:value={selectedWorkflowId}
                    class="w-full text-sm border border-border rounded-md px-3 py-2 bg-background"
                >
                    <option value="">Choose a workflow...</option>
                    {#each workflows as wf}
                        <option value={wf.id}>{wf.name}</option>
                    {/each}
                </select>
            </div>

            <!-- Output variable selector -->
            {#if selectedWorkflowId && outputVariables.length > 0}
                <div>
                    <label class="text-sm font-medium block mb-1.5">Select an Output Variable</label>
                    <select
                        bind:value={selectedOutputVariable}
                        class="w-full text-sm border border-border rounded-md px-3 py-2 bg-background"
                    >
                        <option value="">Choose a variable...</option>
                        {#each Object.entries(groupedVariables) as [nodeId, vars]}
                            <optgroup label="Node: {nodeId}">
                                {#each vars as v}
                                    <option value={v.prefixed_variable}>{v.variable_name}</option>
                                {/each}
                            </optgroup>
                        {/each}
                    </select>
                </div>
            {/if}

            <!-- Sample count -->
            <div>
                <label class="text-sm font-medium block mb-1.5">
                    Number of Samples: {selectedNumSamples}
                </label>
                <input
                    type="range"
                    bind:value={selectedNumSamples}
                    min={1}
                    max={numSamples}
                    step={1}
                    class="w-full"
                />
            </div>
        </div>

        <Dialog.Footer>
            <Button variant="ghost" onclick={() => (isModalOpen = false)}>Cancel</Button>
            <Button onclick={handleRunEval} disabled={isRunning}>
                {isRunning ? 'Starting...' : 'Run Eval'}
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
