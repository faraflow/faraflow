<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import type { NodeProps } from '@xyflow/svelte'
    import BaseNode from './BaseNode.svelte'
    import OutputHandleRow from './shared/OutputHandleRow.svelte'
    import { flowStore } from '$lib/stores/flow.svelte'
    import type { FlowWorkflowNode } from '$lib/types/api_types/nodeTypeSchemas'

    interface Props extends NodeProps {
        data: FlowWorkflowNode['data']
        displayOutput?: boolean
        readOnly?: boolean
        displaySubflow?: boolean
        displayResizer?: boolean
    }

    let { id, data, selected, positionAbsoluteX, positionAbsoluteY, displayOutput = true, readOnly = false }: Props = $props()

    let isCollapsed = $state(false)

    const baseNodeStyle = 'width: auto; min-width: 300px; max-width: 600px; height: auto; min-height: 150px; max-height: 800px; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); backdrop-filter: blur(8px); background-color: rgba(255,255,255,0.8);'
</script>

{#snippet outputHandles()}
    <div class="output-handles flex flex-col flex-1 items-end overflow-hidden" id="output-handles">
        {#if data?.title}
            <OutputHandleRow id={id} keyName={String(data.title)} {isCollapsed} />
        {/if}
    </div>
{/snippet}

<BaseNode
    {id}
    {data}
    {isCollapsed}
    setIsCollapsed={(v) => (isCollapsed = v)}
    style={baseNodeStyle}
    handleOpenModal={(open) => { if (open) flowStore.setSelectedNode(id) }}
    {positionAbsoluteX}
    {positionAbsoluteY}
    renderOutputHandles={outputHandles}
/>
