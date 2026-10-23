<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import Icon from '@iconify/svelte'
    import { flowStore } from '$lib/stores/flow.svelte'
    import { panelStore } from '$lib/stores/panel.svelte'
    import type { FlowWorkflowNode, FlowWorkflowEdge } from '$lib/types/api_types/nodeTypeSchemas'
    import NodeStatusCard from './NodeStatusCard.svelte'

    interface Props {
        onclose: () => void
    }

    let { onclose }: Props = $props()

    type StatusFilter = 'all' | 'COMPLETED' | 'FAILED' | 'RUNNING' | 'PENDING'
    let statusFilter = $state<StatusFilter>('all')
    let orderMode = $state<'execution' | 'alphabetical'>('execution')
    let searchQuery = $state('')
    let showFilterMenu = $state(false)

    function getExecutionOrder(
        nodes: FlowWorkflowNode[],
        edges: FlowWorkflowEdge[]
    ): FlowWorkflowNode[] {
        const nodeMap = new Map(nodes.map((n) => [n.id, n]))
        const indegree = new Map(nodes.map((n) => [n.id, 0]))
        const adj = new Map<string, string[]>(nodes.map((n) => [n.id, []]))

        for (const edge of edges) {
            if (!nodeMap.has(edge.source) || !nodeMap.has(edge.target)) continue
            adj.get(edge.source)?.push(edge.target)
            indegree.set(edge.target, (indegree.get(edge.target) || 0) + 1)
        }

        const queue: FlowWorkflowNode[] = nodes.filter((n) => (indegree.get(n.id) || 0) === 0)
        const result: FlowWorkflowNode[] = []
        const visited = new Set<string>()

        while (queue.length > 0) {
            const node = queue.shift()!
            if (visited.has(node.id)) continue
            visited.add(node.id)
            result.push(node)
            for (const neighborId of adj.get(node.id) || []) {
                const d = (indegree.get(neighborId) || 1) - 1
                indegree.set(neighborId, d)
                if (d === 0 && !visited.has(neighborId)) {
                    const neighbor = nodeMap.get(neighborId)
                    if (neighbor) queue.push(neighbor)
                }
            }
        }

        const remaining = nodes.filter((n) => !visited.has(n.id))
        return [...result, ...remaining]
    }

    const rootNodes = $derived(flowStore.nodes.filter((n) => !n.parentId))

    const statusCounts = $derived({
        COMPLETED: rootNodes.filter((n) => n.data?.taskStatus === 'COMPLETED').length,
        FAILED:    rootNodes.filter((n) => n.data?.taskStatus === 'FAILED').length,
        RUNNING:   rootNodes.filter((n) => n.data?.taskStatus === 'RUNNING').length,
        PENDING:   rootNodes.filter((n) => n.data?.taskStatus === 'PENDING').length,
        CANCELED:  rootNodes.filter((n) => n.data?.taskStatus === 'CANCELED').length,
    })

    const statusButtons = $derived([
        { status: 'COMPLETED' as StatusFilter, count: statusCounts.COMPLETED, label: 'Completed', color: 'text-green-600',  activeBg: 'bg-green-100 dark:bg-green-900/30' },
        { status: 'FAILED'    as StatusFilter, count: statusCounts.FAILED,    label: 'Failed',    color: 'text-red-500',    activeBg: 'bg-red-100 dark:bg-red-900/30' },
        { status: 'RUNNING'   as StatusFilter, count: statusCounts.RUNNING,   label: 'Running',   color: 'text-blue-500',   activeBg: 'bg-blue-100 dark:bg-blue-900/30' },
        { status: 'PENDING'   as StatusFilter, count: statusCounts.PENDING,   label: 'Pending',   color: 'text-yellow-500', activeBg: 'bg-yellow-100 dark:bg-yellow-900/30' },
        { status: 'CANCELED'  as StatusFilter, count: statusCounts.CANCELED,  label: 'Canceled',  color: 'text-gray-400',   activeBg: 'bg-gray-100 dark:bg-gray-900/30' },
    ])

    const visibleNodes = $derived.by(() => {
        let nodes = rootNodes

        // Status filter
        if (statusFilter !== 'all') {
            nodes = nodes.filter((n) => n.data?.taskStatus === statusFilter)
        }

        // Order
        if (orderMode === 'alphabetical') {
            nodes = [...nodes].sort((a, b) =>
                (a.data?.title ?? '').localeCompare(b.data?.title ?? '')
            )
        } else {
            nodes = getExecutionOrder(nodes, flowStore.edges)
        }

        // Search
        if (searchQuery.trim()) {
            const q = searchQuery.trim().toLowerCase()
            nodes = nodes.filter((n) => {
                const title = (n.data?.title ?? '').toLowerCase()
                const type = (n.type ?? '').toLowerCase()
                return title.includes(q) || type.includes(q)
            })
        }

        return nodes
    })

    // Show a dot on the filter icon when non-default order is active
    const isFiltered = $derived(orderMode !== 'execution')
</script>

<!-- Click-outside backdrop -->
{#if showFilterMenu}
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <div
        class="fixed inset-0 z-30"
        onclick={() => (showFilterMenu = false)}
    ></div>
{/if}

<div class="flex flex-col flex-1 min-h-0 overflow-hidden border-b border-border bg-background">
    <!-- Header -->
    <div class="flex items-center justify-between px-3 border-b border-border shrink-0 bg-muted/30" style="height: 44px;">
        <h2 class="text-sm font-semibold shrink-0">Nodes</h2>

        <div class="flex items-center gap-1 shrink-0">
            <!-- Status toggle buttons -->
            {#each statusButtons as btn}
                <button
                    type="button"
                    title="{btn.label} ({btn.count})"
                    class="text-xs font-semibold px-1.5 py-0.5 rounded transition-colors {btn.color}
                        {statusFilter === btn.status ? btn.activeBg : 'hover:bg-muted'}"
                    onclick={() => { statusFilter = statusFilter === btn.status ? 'all' : btn.status }}
                >
                    {btn.count}
                </button>
            {/each}
            <div class="w-px h-4 bg-border mx-0.5"></div>
            <!-- Order dropdown -->
            <div class="relative">
                <button
                    type="button"
                    class="p-1.5 rounded hover:bg-muted transition-colors relative"
                    title="Order"
                    onclick={() => (showFilterMenu = !showFilterMenu)}
                >
                    <Icon icon="solar:tuning-2-linear" width={16} class="text-muted-foreground" />
                    {#if isFiltered}
                        <span class="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-primary"></span>
                    {/if}
                </button>

                {#if showFilterMenu}
                    <div
                        class="absolute right-0 top-full mt-1 z-50 rounded-lg border border-border bg-background shadow-lg overflow-hidden"
                        style="width: 170px;"
                    >
                        <div class="px-3 py-3">
                            <p class="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1.5">Order</p>
                            {#each [['execution', 'Execution'], ['alphabetical', 'Alphabetical']] as [value, label]}
                                <button
                                    type="button"
                                    class="w-full flex items-center justify-between px-2 py-1.5 rounded text-sm transition-colors
                                        {orderMode === value
                                            ? 'bg-primary/10 text-primary font-medium'
                                            : 'hover:bg-muted text-foreground'}"
                                    onclick={() => { orderMode = value as typeof orderMode }}
                                >
                                    {label}
                                    {#if orderMode === value}
                                        <Icon icon="solar:check-circle-bold" width={14} />
                                    {/if}
                                </button>
                            {/each}
                        </div>
                    </div>
                {/if}
            </div>

            <!-- Close -->
            <button
                type="button"
                class="p-1.5 rounded hover:bg-muted transition-colors"
                onclick={onclose}
            >
                <Icon icon="solar:close-circle-linear" width={18} class="text-muted-foreground" />
            </button>
        </div>
    </div>

    <!-- Search -->
    <div class="flex items-center gap-2 px-3 border-b border-border shrink-0 focus-within:bg-muted/50 transition-colors" style="height: 36px;">
        <Icon icon="solar:magnifer-linear" width={14} class="text-muted-foreground flex-shrink-0" />
        <input
            type="text"
            placeholder="Search nodes…"
            bind:value={searchQuery}
            class="flex-1 bg-transparent text-xs outline-none placeholder:text-muted-foreground"
        />
        {#if searchQuery}
            <button
                type="button"
                onclick={() => (searchQuery = '')}
                class="text-muted-foreground hover:text-foreground"
            >
                <Icon icon="solar:close-circle-bold" width={14} />
            </button>
        {/if}
    </div>

    <!-- Node list -->
    <div class="flex-1 overflow-y-auto px-2 py-2 space-y-1.5">
        {#if visibleNodes.length === 0}
            <p class="text-xs text-muted-foreground text-center py-4">
                {searchQuery ? 'No matching nodes' : 'No nodes'}
            </p>
        {:else}
            {#each visibleNodes as node (node.id)}
                <NodeStatusCard
                    {node}
                    isSelected={flowStore.selectedNode === node.id}
                    onclick={() => { flowStore.setSelectedNode(node.id); panelStore.panToNode(node.id) }}
                />
            {/each}
        {/if}
    </div>
</div>
