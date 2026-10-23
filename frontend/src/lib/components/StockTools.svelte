<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { nodeTypesStore } from '$lib/stores/nodeTypes.svelte'

    let searchTerm = $state('')

    interface NodeType {
        name: string
        config: Record<string, any>
        visual_tag?: { color: string; acronym: string }
        logo?: string
        category?: string
    }

    // Flatten and filter node types
    const filteredData = $derived.by(() => {
        if (!nodeTypesStore.data) return {}
        if (!searchTerm.trim()) return nodeTypesStore.data

        const result: Record<string, NodeType[]> = {}
        for (const [category, nodes] of Object.entries(nodeTypesStore.data)) {
            const filtered = (nodes as NodeType[]).filter(
                (n) =>
                    n.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                    (n.config?.title || '').toLowerCase().includes(searchTerm.toLowerCase())
            )
            if (filtered.length > 0) result[category] = filtered
        }
        return result
    })

    // Group nodes within a category by their subcategory
    function groupBySubcategory(nodes: NodeType[]) {
        const groups: Record<string, NodeType[]> = {}
        for (const node of nodes) {
            const sub = node.category || 'Other'
            if (!groups[sub]) groups[sub] = []
            groups[sub].push(node)
        }
        return groups
    }

    // Filter out output fields from config
    function filterConfig(config: Record<string, any>) {
        return Object.fromEntries(
            Object.entries(config).filter(([key]) => !key.toLowerCase().includes('output'))
        )
    }

    let expandedCategories = $state<Set<string>>(new Set())
    function toggleCategory(cat: string) {
        const next = new Set(expandedCategories)
        if (next.has(cat)) next.delete(cat)
        else next.add(cat)
        expandedCategories = next
    }
</script>

<div class="w-full space-y-4">
    <!-- Search -->
    <div class="relative">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
        <input
            type="text"
            bind:value={searchTerm}
            placeholder="Search tools..."
            class="w-full pl-9 pr-4 py-2 text-sm border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-ring"
        />
    </div>

    {#if nodeTypesStore.status === 'loading'}
        <div class="flex justify-center py-8">
            <div class="animate-spin h-6 w-6 border-2 border-primary border-t-transparent rounded-full"></div>
        </div>
    {:else}
        {#each Object.entries(filteredData) as [category, nodes]}
            {@const grouped = groupBySubcategory(nodes as NodeType[])}
            <div class="border border-border rounded-xl overflow-hidden">
                <button
                    onclick={() => toggleCategory(category)}
                    class="w-full flex items-center justify-between px-4 py-3 bg-muted/50 hover:bg-muted text-left font-medium text-sm transition-colors"
                >
                    <span>{category}</span>
                    <svg
                        xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
                        class="transition-transform {expandedCategories.has(category) ? 'rotate-180' : ''}"
                    ><path d="m6 9 6 6 6-6"/></svg>
                </button>

                {#if expandedCategories.has(category)}
                    <div class="divide-y divide-border">
                        {#each Object.entries(grouped) as [subcategory, subnodes]}
                            <div class="px-4 py-3">
                                {#if Object.keys(grouped).length > 1}
                                    <p class="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">{subcategory}</p>
                                {/if}
                                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                    {#each subnodes as node}
                                        {@const filtered = filterConfig(node.config ?? {})}
                                        <div class="border border-border rounded-lg p-4 bg-card hover:bg-muted/30 transition-colors">
                                            <div class="flex items-center gap-2 mb-2">
                                                {#if node.logo}
                                                    <img src={node.logo} alt={node.name} class="w-5 h-5 object-contain" />
                                                {:else if node.visual_tag}
                                                    <div
                                                        class="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold flex-none"
                                                        style="background-color: {node.visual_tag.color}"
                                                    >
                                                        {node.visual_tag.acronym}
                                                    </div>
                                                {/if}
                                                <span class="text-sm font-medium truncate">{node.config?.title ?? node.name}</span>
                                            </div>
                                            {#if Object.keys(filtered).length > 0}
                                                <div class="text-xs text-muted-foreground space-y-1 mt-2">
                                                    {#each Object.entries(filtered).slice(0, 3) as [key, val]}
                                                        <div class="flex gap-1">
                                                            <span class="font-medium">{key}:</span>
                                                            <span class="truncate">{typeof val === 'object' ? JSON.stringify(val) : String(val ?? '')}</span>
                                                        </div>
                                                    {/each}
                                                </div>
                                            {/if}
                                        </div>
                                    {/each}
                                </div>
                            </div>
                        {/each}
                    </div>
                {/if}
            </div>
        {/each}

        {#if Object.keys(filteredData).length === 0}
            <div class="text-center py-8 text-muted-foreground text-sm">No tools found matching "{searchTerm}"</div>
        {/if}
    {/if}
</div>
