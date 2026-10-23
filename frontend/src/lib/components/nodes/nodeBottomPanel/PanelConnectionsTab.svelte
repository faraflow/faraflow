<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import Icon from '@iconify/svelte'
    import { flowStore } from '$lib/stores/flow.svelte'
    import NodeOutputDisplay from '$lib/components/nodes/NodeOutputDisplay.svelte'

    interface Props {
        nodeID: string
        readOnly?: boolean
        onNavigate: (id: string, peek: boolean) => void
    }

    let { nodeID, readOnly = false, onNavigate }: Props = $props()

    const upstreamEdges = $derived(flowStore.edges.filter((e) => e.target === nodeID))
    const downstreamEdges = $derived(flowStore.edges.filter((e) => e.source === nodeID))

    function getNode(id: string) {
        return flowStore.nodes.find((n) => n.id === id) ?? null
    }

    function getNodeTitle(id: string): string {
        return flowStore.nodeConfigs[id]?.title || id
    }

    function handleClick(e: MouseEvent, nodeId: string) {
        onNavigate(nodeId, e.metaKey || e.ctrlKey)
    }
</script>

<div class="p-4 space-y-4">
    {#if upstreamEdges.length === 0 && downstreamEdges.length === 0}
        <p class="text-sm text-muted-foreground text-center py-4">No connections</p>
    {/if}

    {#if upstreamEdges.length > 0}
        <div>
            <h3 class="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Upstream</h3>
            <div class="space-y-2">
                {#each upstreamEdges as edge}
                    {@const sourceNode = getNode(edge.source)}
                    {#if sourceNode}
                        <button
                            type="button"
                            class="w-full text-left p-3 rounded-lg border border-border hover:bg-muted/50 transition-colors"
                            onclick={(e) => handleClick(e, edge.source)}
                            title="Click to select · Cmd+Click to peek"
                        >
                            <div class="flex items-center gap-2 mb-1">
                                <Icon icon="solar:arrow-up-linear" class="text-blue-500 shrink-0" width={14} />
                                <span class="text-sm font-medium truncate">{getNodeTitle(edge.source)}</span>
                                <span class="text-xs text-muted-foreground ml-auto shrink-0">{sourceNode.type}</span>
                            </div>
                            {#if edge.sourceHandle || edge.targetHandle}
                                <div class="text-xs text-muted-foreground">
                                    {edge.sourceHandle ?? 'output'} → {edge.targetHandle ?? 'input'}
                                </div>
                            {/if}
                            {#if readOnly && sourceNode.data?.run}
                                <div class="mt-2">
                                    <NodeOutputDisplay output={sourceNode.data.run} maxHeight="96px" />
                                </div>
                            {/if}
                        </button>
                    {/if}
                {/each}
            </div>
        </div>
    {/if}

    {#if downstreamEdges.length > 0}
        <div>
            <h3 class="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Downstream</h3>
            <div class="space-y-2">
                {#each downstreamEdges as edge}
                    {@const targetNode = getNode(edge.target)}
                    {#if targetNode}
                        <button
                            type="button"
                            class="w-full text-left p-3 rounded-lg border border-border hover:bg-muted/50 transition-colors"
                            onclick={(e) => handleClick(e, edge.target)}
                            title="Click to select · Cmd+Click to peek"
                        >
                            <div class="flex items-center gap-2 mb-1">
                                <Icon icon="solar:arrow-down-linear" class="text-green-500 shrink-0" width={14} />
                                <span class="text-sm font-medium truncate">{getNodeTitle(edge.target)}</span>
                                <span class="text-xs text-muted-foreground ml-auto shrink-0">{targetNode.type}</span>
                            </div>
                            {#if edge.sourceHandle || edge.targetHandle}
                                <div class="text-xs text-muted-foreground">
                                    {edge.sourceHandle ?? 'output'} → {edge.targetHandle ?? 'input'}
                                </div>
                            {/if}
                        </button>
                    {/if}
                {/each}
            </div>
        </div>
    {/if}
</div>
