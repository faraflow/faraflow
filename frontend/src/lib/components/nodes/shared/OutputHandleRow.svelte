<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { Handle, Position } from '@xyflow/svelte'

    interface Props {
        id: string
        keyName: string
        isCollapsed: boolean
    }

    let { id, keyName, isCollapsed }: Props = $props()
</script>

<div class="handle-row w-full flex items-center justify-end overflow-hidden whitespace-nowrap" id="output-{keyName}-row">
    {#if !isCollapsed}
        <div class="flex flex-grow flex-shrink mr-2 max-w-full overflow-hidden items-center" id="output-{keyName}-label">
            <span class="handle-label text-sm font-medium cursor-pointer hover:text-primary ml-auto overflow-hidden text-ellipsis whitespace-nowrap text-foreground/80">
                {keyName}
            </span>
        </div>
    {/if}
    <div class="border-l border-border h-full mx-0"></div>
    <div class="handle-cell output-handle-cell relative flex items-center justify-center w-6 h-6" id="output-{keyName}-handle">
        <Handle
            type="source"
            position={Position.Right}
            id={String(id)}
            class="!w-3 !h-3 !bg-primary/70 !border-2 !border-background !top-1/2 !left-1/2 !-translate-x-1/2 !-translate-y-1/2 {isCollapsed ? '!opacity-50' : ''}"
            isConnectable={!isCollapsed}
        />
    </div>
</div>

<style>
    .handle-row {
        min-height: 32px;
    }
</style>
