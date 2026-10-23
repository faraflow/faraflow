<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { NodeResizer } from '@xyflow/svelte'
    import Icon from '@iconify/svelte'
    import { Button } from '$lib/components/ui/button'
    import { flowStore } from '$lib/stores/flow.svelte'
    import BaseNode from '../BaseNode.svelte'
    import OutputHandleRow from '../shared/OutputHandleRow.svelte'
    import CollapsibleNodePanel from '../CollapsibleNodePanel.svelte'

    interface Props {
        id: string
        data?: any
    }

    let { id, data }: Props = $props()

    let isCollapsed = $state(false)
    let showNodePanel = $state(false)

    const nodeConfig = $derived(flowStore.nodeConfigs[id])
    const node = $derived(flowStore.nodes.find((n) => n.id === id))
    const isSelected = $derived(String(id) === String(flowStore.selectedNode))

    const nodeData = $derived({
        title: nodeConfig?.title || 'Agent',
        color: data?.color || '#6B46C1',
        acronym: 'AG',
        run: data?.run,
        config: nodeConfig,
        taskStatus: data?.taskStatus,
    })

    const toolNodes = $derived(nodeConfig?.tools || [])

    const minWidth = 300
    const minHeight = $derived(toolNodes?.length ? 200 : 150)

    function handleAddTool() {
        showNodePanel = true
    }

    function handleAddNodeToAgent(nodeName: string) {
        flowStore.addToolToAgent(id, nodeName)
        showNodePanel = false
    }
</script>

{#snippet outputHandles()}
    <div class="handles-column output-handles-column" id="output-handle">
        {#if nodeConfig?.title}
            <OutputHandleRow {id} keyName={String(nodeConfig.title)} {isCollapsed} />
        {/if}
    </div>
{/snippet}

<div class="w-full h-full relative">
    <NodeResizer
        nodeId={id}
        isVisible={isSelected}
        {minWidth}
        {minHeight}
        lineStyle="border-color: rgb(148 163 184); display: none;"
        handleStyle="background-color: rgb(148 163 184); width: 1rem; height: 1rem; border-radius: 2px;"
    />
    <BaseNode
        {id}
        data={node?.data}
        {isCollapsed}
        setIsCollapsed={(v) => (isCollapsed = v)}
        positionAbsoluteX={0}
        positionAbsoluteY={0}
        className="group {isSelected ? 'selected' : ''}"
        isResizable={true}
        handleOpenModal={() => {}}
        renderOutputHandles={outputHandles}
    >
        <div class="h-full">
            <!-- Tool Management Section -->
            <div class="mt-4 flex flex-col h-full">
                <Button
                    size="lg"
                    variant="outline"
                    class="w-full mt-4"
                    onclick={(e) => { e.stopPropagation(); handleAddTool() }}
                >
                    <Icon icon="solar:add-circle-linear" width={20} class="mr-2" />
                    Add Tool
                </Button>
            </div>
        </div>
    </BaseNode>

    <!-- Node Panel for Adding Tools -->
    {#if showNodePanel}
        <div class="absolute bottom-full left-0 mb-2 z-50">
            <CollapsibleNodePanel
                handleAddNode={handleAddNodeToAgent}
                isCustomAdd={true}
                controlledExpanded={showNodePanel}
                onExpandedChange={(expanded) => { showNodePanel = expanded }}
            />
        </div>
    {/if}
</div>

<style>
    .handles-column {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    .output-handles-column {
        align-items: flex-end;
    }
</style>
