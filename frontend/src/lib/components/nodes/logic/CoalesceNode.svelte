<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { flowStore } from '$lib/stores/flow.svelte'
    import BaseNode from '../BaseNode.svelte'
    import OutputHandleRow from '../shared/OutputHandleRow.svelte'

    interface Props {
        id: string
        data?: any
    }

    let { id, data }: Props = $props()

    let isCollapsed = $state(false)

    const nodeConfig = $derived(flowStore.nodeConfigs[id])

    const nodeData = $derived({
        title: nodeConfig?.title || 'Coalesce',
        color: data?.color || '#38B2AC',
        acronym: 'CL',
        run: data?.run,
        config: nodeConfig,
        taskStatus: data?.taskStatus,
    })

    // Predecessor nodes
    const predecessors = $derived.by(() => {
        return flowStore.edges
            .filter((e) => e.target === id)
            .map((e) => {
                const src = flowStore.nodes.find((n) => n.id === e.source)
                return src || null
            })
            .filter(Boolean)
            .filter((n, i, self) => self.findIndex((x) => x!.id === n!.id) === i)
    })

    const inputVariables = $derived.by(() => {
        return predecessors.map((pred) => {
            if (!pred) return null
            const predConfig = flowStore.nodeConfigs[pred.id]
            const label = predConfig?.title || pred.data?.title || pred.id
            const value = `${pred.id}|${pred.data?.title || ''}`
            return { value, label }
        }).filter(Boolean) as { value: string; label: string }[]
    })

    const usedPreferences = $derived(nodeConfig?.preferences?.filter(Boolean) ?? [])

    function availableVariablesForIndex(index: number) {
        return inputVariables.filter(
            (v) => !usedPreferences.includes(v.value) || v.value === nodeConfig?.preferences?.[index]
        )
    }

    // Keep preference array in sync with number of input variables
    $effect(() => {
        const desired = inputVariables.length
        const current = nodeConfig?.preferences ?? []
        let updated = [...current]
        if (updated.length > desired) {
            updated = updated.slice(0, desired)
        } else {
            while (updated.length < desired) updated.push('')
        }
        const changed =
            updated.length !== current.length ||
            updated.some((v, i) => v !== current[i])
        if (changed) {
            flowStore.updateNodeConfigOnly(id, { ...nodeConfig, preferences: updated })
        }
    })

    function handlePreferenceChange(index: number, value: string) {
        const updated = [...(nodeConfig?.preferences ?? [])]
        updated[index] = value
        flowStore.updateNodeConfigOnly(id, { ...nodeConfig, preferences: updated })
    }
</script>

{#snippet outputHandles()}
    <div class="handles-column output-handles-column" id="output-handle">
        {#if nodeData?.title}
            <OutputHandleRow {id} keyName={String(nodeData.title)} {isCollapsed} />
        {/if}
    </div>
{/snippet}

<BaseNode
    {id}
    {isCollapsed}
    setIsCollapsed={(v) => (isCollapsed = v)}
    data={nodeData}
    style="width: auto; max-height: 800px; display: flex; flex-direction: column;"
    className="hover:!bg-background"
    renderOutputHandles={outputHandles}
>
    <div class="flex flex-col flex-grow overflow-hidden">
        {#if !isCollapsed}
            <div
                class="p-3 overflow-y-auto"
                style="touch-action: none; max-height: 600px;"
                role="presentation"
                onwheelcapture={(e) => e.stopPropagation()}
                onclick={(e) => e.stopPropagation()}
            >
                <!-- Preferences header -->
                <div class="sticky top-0 bg-background/95 backdrop-blur-sm z-10 pb-4">
                    <hr class="my-2 border-border" />
                    <div class="flex items-center gap-2 mb-4">
                        <span class="text-sm font-medium text-foreground">Preferences</span>
                        <hr class="flex-grow border-border" />
                    </div>
                </div>

                <div class="flex flex-col gap-4">
                    {#each (nodeConfig?.preferences ?? []) as prefValue, i}
                        <div class="border border-border rounded-lg p-2 bg-background">
                            <select
                                class="text-sm border border-border rounded-md px-2 py-1 bg-background w-full min-w-[200px]"
                                value={prefValue}
                                onchange={(e) => handlePreferenceChange(i, (e.target as HTMLSelectElement).value)}
                            >
                                <option value="">Select variable</option>
                                {#each availableVariablesForIndex(i) as variable}
                                    <option value={variable.value}>{variable.label}</option>
                                {/each}
                            </select>
                        </div>
                    {/each}
                </div>
            </div>
        {/if}
    </div>
</BaseNode>

<style>
    .handles-column {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    .output-handles-column {
        align-items: flex-end;
    }
</style>
