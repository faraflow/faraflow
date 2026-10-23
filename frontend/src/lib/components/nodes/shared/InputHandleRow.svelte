<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { Handle, Position, useNodeConnections, useUpdateNodeInternals } from '@xyflow/svelte'
    import { onMount } from 'svelte'

    interface Props {
        id: string
        keyName: string
        isCollapsed: boolean
        nodeId: string
    }

    let { id, keyName, isCollapsed, nodeId }: Props = $props()

    // svelte-ignore state_referenced_locally -- useNodeConnections manages its own reactivity
    const connections = useNodeConnections({ id: nodeId, handleType: 'target', handleId: String(keyName) })
    const isConnectable = $derived(
        !isCollapsed && (connections.current.length === 0 || String(keyName).startsWith('branch'))
    )

    const updateNodeInternals = useUpdateNodeInternals()

    // When this handle row mounts (new incoming connection added), tell @xyflow to
    // re-scan the parent node's handles so it can route the edge to this handle.
    onMount(() => {
        updateNodeInternals(nodeId)
    })
</script>

<div class="handle-row w-full flex items-center overflow-hidden whitespace-nowrap" id="input-{keyName}-row">
    <div class="handle-cell relative shrink-0 flex items-center justify-center w-6 h-6" id="input-{keyName}-handle">
        <Handle
            type="target"
            position={Position.Left}
            id={String(id)}
            class="!w-3 !h-3 !bg-primary/70 !border-2 !border-background !top-1/2 !left-1/2 !-translate-x-1/2 !-translate-y-1/2 {isCollapsed ? '!opacity-50' : ''}"
            isConnectable={isConnectable}
        />
    </div>
    <div class="border-r border-border h-4 mx-0"></div>
    {#if !isCollapsed}
        <div class="flex flex-grow flex-shrink ml-2 max-w-full overflow-hidden items-center" id="input-{keyName}-label">
            <span class="text-sm font-medium cursor-pointer hover:text-primary mr-auto overflow-hidden text-ellipsis whitespace-nowrap text-foreground/80">
                {String(keyName)}
            </span>
        </div>
    {/if}
</div>

<style>
    .handle-row {
        min-height: 32px;
    }
</style>
