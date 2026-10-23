<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { Input } from '$lib/components/ui/input'
    import Icon from '@iconify/svelte'
    import { nodeTypesStore } from '$lib/stores/nodeTypes.svelte'
    import type { FlowWorkflowNodeTypesByCategory } from '$lib/types/api_types/nodeTypeSchemas'

    interface Props {
        x: number
        y: number
        onSelect: (nodeType: string) => void
        onClose: () => void
    }

    let { x, y, onSelect, onClose }: Props = $props()

    let searchTerm = $state('')
    let containerEl: HTMLDivElement | undefined = $state()

    const nodeTypes = $derived((nodeTypesStore.data as FlowWorkflowNodeTypesByCategory) || {})

    const filteredCategories = $derived.by(() => {
        const q = searchTerm.trim().toLowerCase()
        const result: { category: string; nodes: { name: string; title: string; logo?: string; color?: string; acronym?: string }[] }[] = []
        for (const [category, nodes] of Object.entries(nodeTypes)) {
            if (category === 'Input/Output') continue
            const filtered = (nodes as any[])
                .filter((n) => !q || n.name.toLowerCase().includes(q) || (n.config?.title || '').toLowerCase().includes(q))
                .map((n) => ({
                    name: n.name,
                    title: n.config?.title || n.name,
                    logo: n.logo,
                    color: n.visual_tag?.color,
                    acronym: n.visual_tag?.acronym,
                }))
            if (filtered.length > 0) result.push({ category, nodes: filtered })
        }
        return result
    })

    // Close on outside click
    function handleOutsideMousedown(e: MouseEvent) {
        if (containerEl && !containerEl.contains(e.target as Node)) {
            onClose()
        }
    }

    // Clamp position so the panel stays within the viewport
    const PANEL_WIDTH = 240
    const PANEL_MAX_HEIGHT = 320

    const clampedX = $derived(Math.min(x, window.innerWidth - PANEL_WIDTH - 8))
    const clampedY = $derived(Math.min(y, window.innerHeight - PANEL_MAX_HEIGHT - 8))
</script>

<svelte:document onmousedown={handleOutsideMousedown} />

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
    bind:this={containerEl}
    class="fixed z-[100] bg-background border border-border rounded-xl shadow-xl flex flex-col"
    style="left: {clampedX}px; top: {clampedY}px; width: {PANEL_WIDTH}px; max-height: {PANEL_MAX_HEIGHT}px;"
    onmousedown={(e) => e.stopPropagation()}
>
    <!-- Search -->
    <div class="p-2 border-b border-border">
        <div class="relative">
            <Icon icon="akar-icons:search" class="absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground" width={13} />
            <!-- svelte-ignore a11y_autofocus -->
            <Input
                autofocus
                type="search"
                placeholder="Search nodes…"
                value={searchTerm}
                oninput={(e) => (searchTerm = (e.target as HTMLInputElement).value)}
                onkeydown={(e) => e.key === 'Escape' && onClose()}
                class="pl-6 h-7 text-xs"
            />
        </div>
    </div>

    <!-- Node list -->
    <div class="overflow-y-auto flex-1">
        {#each filteredCategories as { category, nodes }}
            <div class="border-t border-border first:border-t-0">
                <div class="px-3 py-1 text-xs font-semibold text-muted-foreground bg-muted/30">{category}</div>
                {#each nodes as node}
                    <button
                        class="w-full flex items-center gap-2 px-3 py-1.5 hover:bg-muted/60 text-left text-sm"
                        onclick={() => onSelect(node.name)}
                    >
                        {#if node.logo}
                            <img src={node.logo} alt="" class="w-4 h-4 shrink-0" />
                        {:else if node.color && node.acronym}
                            <span
                                class="text-white text-xs px-1 rounded shrink-0"
                                style="background-color: {node.color};"
                            >{node.acronym}</span>
                        {/if}
                        <span class="truncate text-foreground">{node.title}</span>
                    </button>
                {/each}
            </div>
        {/each}
        {#if filteredCategories.length === 0}
            <p class="text-sm text-muted-foreground text-center py-4">No nodes found</p>
        {/if}
    </div>
</div>
