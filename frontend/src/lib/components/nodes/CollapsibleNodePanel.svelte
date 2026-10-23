<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { Button } from '$lib/components/ui/button'
    import { Input } from '$lib/components/ui/input'
    import * as Accordion from '$lib/components/ui/accordion'
    import Icon from '@iconify/svelte'
    import { useSvelteFlow } from '@xyflow/svelte'
    import { nodeTypesStore } from '$lib/stores/nodeTypes.svelte'
    import { panelStore } from '$lib/stores/panel.svelte'
    import { createNodeAtCenter } from '$lib/utils/flowUtils'
    import type { FlowWorkflowNodeType, FlowWorkflowNodeTypesByCategory } from '$lib/types/api_types/nodeTypeSchemas'

    interface CategoryGroup {
        nodes: FlowWorkflowNodeType[]
        logo?: string
        color?: string
        acronym?: string
    }

    interface Props {
        handleAddNode?: (nodeName: string) => void
        isCustomAdd?: boolean
        controlledExpanded?: boolean
        onExpandedChange?: (expanded: boolean) => void
    }

    let { handleAddNode, isCustomAdd = false, controlledExpanded, onExpandedChange }: Props = $props()

    const { screenToFlowPosition } = useSvelteFlow()

    let searchTerm = $state('')
    let selectedCategories = $state<Set<string>>(new Set())
    let panelEl: HTMLDivElement | undefined = $state()
    let searchInputEl: HTMLInputElement | null = $state(null)

    const isExpanded = $derived(
        typeof controlledExpanded !== 'undefined' ? controlledExpanded : panelStore.isNodePanelExpanded
    )

    const nodeTypes = $derived(nodeTypesStore.data as FlowWorkflowNodeTypesByCategory || {})

    const filteredNodeTypes = $derived.by(() => {
        if (!searchTerm.trim()) return nodeTypes
        return Object.keys(nodeTypes).reduce((acc, category) => {
            const filtered = (nodeTypes[category] || []).filter((node) =>
                node.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                node.config?.title?.toLowerCase().includes(searchTerm.toLowerCase())
            )
            if (filtered.length > 0) acc[category] = filtered
            return acc
        }, {} as FlowWorkflowNodeTypesByCategory)
    })

    $effect(() => {
        if (isExpanded && searchInputEl) {
            searchInputEl.focus()
        }
    })

    $effect(() => {
        if (!isExpanded) {
            searchTerm = ''
        }
    })

    function toggleExpanded() {
        if (onExpandedChange) {
            onExpandedChange(!isExpanded)
        } else {
            panelStore.toggleNodePanelExpanded()
        }
    }

    function collapse() {
        if (onExpandedChange) {
            onExpandedChange(false)
        } else {
            panelStore.setNodePanelExpanded(false)
        }
    }

    function onAddNode(nodeName: string) {
        if (isCustomAdd && handleAddNode) {
            handleAddNode(nodeName)
        } else {
            createNodeAtCenter(nodeName, screenToFlowPosition)
        }
        collapse()
    }

    function groupBySubcategory(nodes: FlowWorkflowNodeType[]): Record<string, CategoryGroup> {
        return nodes.reduce((acc, node) => {
            const sub = node.category || 'Other'
            if (!acc[sub]) {
                acc[sub] = { nodes: [], logo: node.logo, color: node.visual_tag?.color, acronym: node.visual_tag?.acronym }
            }
            acc[sub].nodes.push(node)
            return acc
        }, {} as Record<string, CategoryGroup>)
    }

    function toggleCategory(cat: string) {
        const next = new Set(selectedCategories)
        if (next.has(cat)) next.delete(cat)
        else next.add(cat)
        selectedCategories = next
    }

    const isMac = typeof navigator !== 'undefined' && navigator.platform.includes('Mac')
</script>

<svelte:window
    onkeydown={(e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault()
            toggleExpanded()
        }
        if (e.key === 'Escape' && isExpanded && panelEl?.contains(document.activeElement)) {
            collapse()
        }
    }}
/>

<div
    bind:this={panelEl}
    data-node-panel
    data-expanded={isExpanded}
    class="shadow-sm rounded-xl border border-border bg-background transition-all duration-300 {isExpanded ? 'w-64' : 'w-auto h-auto'}"
>
    <Button
        variant="ghost"
        size="icon"
        class="w-10 h-10 bg-background"
        title="{isMac ? '⌘' : 'Ctrl'}+K to toggle panel"
        onclick={toggleExpanded}
    >
        <Icon
            icon={isExpanded ? 'solar:minus-square-linear' : 'solar:widget-add-linear'}
            width={22}
            class="text-muted-foreground"
        />
    </Button>

    {#if isExpanded}
        <div class="px-2 pb-1">
            <div class="relative">
                <Icon
                    icon="akar-icons:search"
                    class="absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground z-10"
                    width={14}
                />
                <Input
                    bind:ref={searchInputEl}
                    type="search"
                    placeholder="Search nodes..."
                    value={searchTerm}
                    oninput={(e) => (searchTerm = (e.target as HTMLInputElement).value)}
                    class="pl-7 h-8 text-sm"
                />
            </div>
        </div>

        <div class="mt-2 max-h-[calc(100vh-16rem)] overflow-auto" id="node-type-accordion">
            {#each Object.keys(filteredNodeTypes).filter((c) => c !== 'Input/Output') as category}
                {@const nodes = filteredNodeTypes[category]}
                {@const hasSubcategories = new Set(nodes.map((n) => n.category || 'Other')).size > 1}
                {@const isOpen = selectedCategories.has(category)}

                <div class="border-t border-border first:border-t-0">
                    <button
                        class="w-full flex items-center justify-between px-3 py-2 text-sm font-medium hover:bg-muted/50 text-left"
                        onclick={() => toggleCategory(category)}
                    >
                        <span>{category}</span>
                        <Icon
                            icon={isOpen ? 'solar:alt-arrow-up-linear' : 'solar:alt-arrow-down-linear'}
                            width={14}
                            class="text-muted-foreground"
                        />
                    </button>

                    {#if isOpen}
                        <div class="pb-1">
                            {#if hasSubcategories}
                                {@const grouped = groupBySubcategory(nodes)}
                                {#each Object.entries(grouped) as [subcategory, { nodes: subNodes, logo, color, acronym }]}
                                    <div class="pl-2">
                                        <button
                                            class="w-full flex items-center gap-2 px-2 py-1.5 text-xs font-semibold hover:bg-muted/50 text-left"
                                            onclick={() => toggleCategory(subcategory)}
                                        >
                                            <div class="flex-shrink-0 mr-2">
                                                {#if logo}
                                                    <img src={logo} alt="{subcategory} Logo" class="max-h-5 max-w-5" />
                                                {:else}
                                                    <div
                                                        class="text-white px-1 py-0.5 rounded-full text-xs whitespace-nowrap"
                                                        style="background-color: {color};"
                                                    >{acronym}</div>
                                                {/if}
                                            </div>
                                            <span class="flex-1">{subcategory}</span>
                                            <Icon
                                                icon={selectedCategories.has(subcategory) ? 'solar:alt-arrow-up-linear' : 'solar:alt-arrow-down-linear'}
                                                width={12}
                                                class="text-muted-foreground"
                                            />
                                        </button>
                                        {#if selectedCategories.has(subcategory)}
                                            {#each subNodes as node}
                                                <div
                                                    class="flex items-center cursor-pointer p-2 hover:bg-muted/50 ml-4"
                                                    role="button"
                                                    tabindex="0"
                                                    onclick={() => onAddNode(node.name)}
                                                    onkeydown={(e) => e.key === 'Enter' && onAddNode(node.name)}
                                                >
                                                    <span class="flex-grow overflow-hidden text-ellipsis whitespace-nowrap text-sm text-foreground" title={node.config?.title}>
                                                        {node.config?.title || node.name}
                                                    </span>
                                                </div>
                                            {/each}
                                        {/if}
                                    </div>
                                {/each}
                            {:else}
                                {#each nodes as node}
                                    <div
                                        class="flex items-center cursor-pointer p-2 hover:bg-muted/50"
                                        role="button"
                                        tabindex="0"
                                        onclick={() => onAddNode(node.name)}
                                        onkeydown={(e) => e.key === 'Enter' && onAddNode(node.name)}
                                    >
                                        <div class="flex-shrink-0 mr-2">
                                            {#if node.logo}
                                                <img src={node.logo} alt="Node Logo" class="max-h-6 max-w-6" />
                                            {:else if node.visual_tag}
                                                <div
                                                    class="text-white px-1.5 py-0.5 rounded-full text-xs whitespace-nowrap"
                                                    style="background-color: {node.visual_tag.color};"
                                                >{node.visual_tag.acronym}</div>
                                            {/if}
                                        </div>
                                        <span class="flex-grow overflow-hidden text-ellipsis whitespace-nowrap text-sm text-foreground" title={node.config?.title}>
                                            {node.config?.title || node.name}
                                        </span>
                                    </div>
                                {/each}
                            {/if}
                        </div>
                    {/if}
                </div>
            {/each}
        </div>
    {/if}
</div>
