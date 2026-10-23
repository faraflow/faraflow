<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import Icon from '@iconify/svelte'
    import type { FlowWorkflowNode } from '$lib/types/api_types/nodeTypeSchemas'
    import type { Snippet } from 'svelte'
    import { getStatusConfig } from '$lib/utils/statusConfig'

    interface Props {
        node: FlowWorkflowNode
        isSelected: boolean
        onclick: () => void
        children?: Snippet
    }

    let { node, isSelected, onclick, children }: Props = $props()

    const status = $derived(node.data?.taskStatus ?? null)
    const displayType = $derived((node.type ?? '').replace(/Node$/, ''))

    const statusConfig = $derived(getStatusConfig(status))

    const hasBorder = $derived(isSelected || status === 'FAILED' || status === 'COMPLETED' || status === 'RUNNING')
</script>

<!-- svelte-ignore a11y_interactive_supports_focus -->
<div
    role="button"
    tabindex="0"
    class="w-full text-left px-3 py-2.5 rounded-lg border border-border transition-all cursor-pointer bg-background"
    style={hasBorder ? `border-color: ${statusConfig.color}; border-width: 1.5px;` : ''}
    {onclick}
    onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') onclick() }}
>
    <div class="flex items-start gap-2.5">
        <!-- Color badge with acronym -->
        <div
            class="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold mt-0.5"
            style="background-color: {node.data?.color ?? '#888'};"
        >
            {node.data?.acronym ?? '?'}
        </div>

        <div class="flex-1 min-w-0">
            <!-- Title and type -->
            <p class="text-sm font-medium leading-tight truncate">{node.data?.title ?? node.id}</p>
            <p class="text-xs text-muted-foreground truncate">{displayType}</p>

            <!-- Status badge -->
            {#if status}
                <div class="flex items-center gap-1 mt-1.5">
                    <Icon
                        icon={statusConfig.icon}
                        width={13}
                        class={statusConfig.spin ? 'animate-spin' : ''}
                        style="color: {statusConfig.color}; flex-shrink: 0;"
                    />
                    <span class="text-xs" style="color: {statusConfig.color};">{statusConfig.label}</span>
                </div>
            {/if}

            <!-- Error preview (NodesOverviewPanel mode — no expandable children) -->
            {#if !children && status === 'FAILED' && node.data?.error}
                <p class="text-xs text-destructive line-clamp-2 mt-1 break-words">{node.data.error}</p>
            {/if}
        </div>

        <!-- Expand chevron when children are provided -->
        {#if children}
            <Icon
                icon={isSelected ? 'solar:alt-arrow-up-linear' : 'solar:alt-arrow-down-linear'}
                width={14}
                class="flex-shrink-0 self-center text-muted-foreground"
            />
        {/if}
    </div>

    <!-- Expandable content -->
    {#if children && isSelected}
        <div class="mt-2 pt-2 border-t border-border">
            {@render children()}
        </div>
    {/if}
</div>
