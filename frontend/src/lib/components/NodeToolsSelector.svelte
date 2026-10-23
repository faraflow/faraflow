<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import Icon from '@iconify/svelte'
    import { Input } from '$lib/components/ui/input'
    import type { FlowWorkflowNodeType, FlowWorkflowNodeTypesByCategory } from '$lib/types/api_types/nodeTypeSchemas'

    interface Props {
        nodeTypes: FlowWorkflowNodeTypesByCategory
        onSelectionChange: (selectedNodes: FlowWorkflowNodeType[]) => void
        initialSelection?: FlowWorkflowNodeType[]
    }

    let { nodeTypes, onSelectionChange, initialSelection = [] }: Props = $props()

    let searchTerm = $state('')
    let openCategories = $state<Set<string>>(new Set())
    let selectedNodes = $state<Record<string, boolean>>({})

    // Initialize from initialSelection
    $effect(() => {
        if (initialSelection.length > 0) {
            const init = initialSelection.reduce(
                (acc, node) => { acc[node.name] = true; return acc },
                {} as Record<string, boolean>
            )
            selectedNodes = init
        }
    })

    // Filter by search term
    const filteredNodeTypes = $derived.by(() => {
        if (!searchTerm.trim()) return nodeTypes
        const result: FlowWorkflowNodeTypesByCategory = {}
        for (const category of Object.keys(nodeTypes)) {
            const filtered = nodeTypes[category].filter((node: FlowWorkflowNodeType) =>
                node.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                (node.config?.title || '').toLowerCase().includes(searchTerm.toLowerCase())
            )
            if (filtered.length > 0) {
                result[category] = filtered
                openCategories.add(category)
            }
        }
        return result
    })

    function toggleNode(node: FlowWorkflowNodeType) {
        const updated = { ...selectedNodes, [node.name]: !selectedNodes[node.name] }
        selectedNodes = updated
        // Notify parent
        const selected = Object.entries(updated)
            .filter(([_, v]) => v)
            .map(([name]) => {
                for (const cat of Object.keys(nodeTypes)) {
                    const found = nodeTypes[cat].find((n) => n.name === name)
                    if (found) return found
                }
                return null
            })
            .filter(Boolean) as FlowWorkflowNodeType[]
        onSelectionChange(selected)
    }

    function toggleCategory(category: string) {
        const updated = new Set(openCategories)
        if (updated.has(category)) updated.delete(category)
        else updated.add(category)
        openCategories = updated
    }

    function groupBySubcategory(nodes: FlowWorkflowNodeType[]) {
        return nodes.reduce((acc: Record<string, FlowWorkflowNodeType[]>, node) => {
            const sub = node.category || 'Other'
            if (!acc[sub]) acc[sub] = []
            acc[sub].push(node)
            return acc
        }, {})
    }
</script>

<div class="w-full">
    <div class="relative mb-4">
        <Icon icon="solar:magnifer-linear" class="absolute left-2.5 top-2.5 text-muted-foreground" width={14} />
        <Input
            type="search"
            placeholder="Search nodes..."
            class="pl-8 text-sm h-8"
            value={searchTerm}
            oninput={(e) => (searchTerm = (e.target as HTMLInputElement).value)}
        />
    </div>

    <div class="max-h-[60vh] overflow-auto space-y-1">
        {#each Object.keys(filteredNodeTypes).filter((c) => c !== 'Input/Output') as category}
            {@const nodes = filteredNodeTypes[category]}
            {@const hasSubcategories = new Set(nodes.map((n: FlowWorkflowNodeType) => n.category || 'Other')).size > 1}
            <div class="border border-border rounded-lg overflow-hidden">
                <button
                    type="button"
                    class="w-full flex items-center justify-between px-3 py-2 bg-muted/30 hover:bg-muted/50 text-sm font-medium text-left"
                    onclick={() => toggleCategory(category)}
                >
                    <span>{category}</span>
                    <Icon
                        icon={openCategories.has(category) ? 'solar:alt-arrow-up-linear' : 'solar:alt-arrow-down-linear'}
                        width={14}
                    />
                </button>
                {#if openCategories.has(category)}
                    <div class="p-2 space-y-1">
                        {#if hasSubcategories}
                            {#each Object.entries(groupBySubcategory(nodes)) as [subcategory, subNodes]}
                                <div class="pl-2">
                                    <p class="text-xs text-muted-foreground font-medium py-1">{subcategory}</p>
                                    {#each subNodes as node}
                                        <button
                                            type="button"
                                            class="w-full flex items-center gap-2 p-2 rounded-md hover:bg-muted/50 text-left"
                                            onclick={() => toggleNode(node)}
                                        >
                                            <input
                                                type="checkbox"
                                                checked={!!selectedNodes[node.name]}
                                                class="rounded"
                                                tabindex="-1"
                                                onclick={(e) => e.stopPropagation()}
                                                onchange={() => toggleNode(node)}
                                            />
                                            {#if node.logo}
                                                <img src={node.logo} alt="" class="w-5 h-5 object-contain" />
                                            {:else if node.visual_tag?.color && node.visual_tag?.acronym}
                                                <span
                                                    class="text-white px-1.5 py-0.5 rounded-full text-xs"
                                                    style="background-color: {node.visual_tag.color}"
                                                >{node.visual_tag.acronym}</span>
                                            {/if}
                                            <span class="text-sm">{node.config?.title || node.name}</span>
                                        </button>
                                    {/each}
                                </div>
                            {/each}
                        {:else}
                            {#each nodes as node}
                                <button
                                    type="button"
                                    class="w-full flex items-center gap-2 p-2 rounded-md hover:bg-muted/50 text-left"
                                    onclick={() => toggleNode(node)}
                                >
                                    <input
                                        type="checkbox"
                                        checked={!!selectedNodes[node.name]}
                                        class="rounded"
                                        tabindex="-1"
                                        onclick={(e) => e.stopPropagation()}
                                        onchange={() => toggleNode(node)}
                                    />
                                    {#if node.logo}
                                        <img src={node.logo} alt="" class="w-5 h-5 object-contain" />
                                    {:else if node.visual_tag?.color && node.visual_tag?.acronym}
                                        <span
                                            class="text-white px-1.5 py-0.5 rounded-full text-xs"
                                            style="background-color: {node.visual_tag.color}"
                                        >{node.visual_tag.acronym}</span>
                                    {/if}
                                    <span class="text-sm">{node.config?.title || node.name}</span>
                                </button>
                            {/each}
                        {/if}
                    </div>
                {/if}
            </div>
        {/each}
    </div>
</div>
