<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { NodeResizer } from '@xyflow/svelte'
    import { flowStore } from '$lib/stores/flow.svelte'
    import BaseNode from '../BaseNode.svelte'
    import OutputHandleRow from '../shared/OutputHandleRow.svelte'
    import { getRelativeNodesBounds } from './groupNodeUtils'
    import isEqual from 'lodash.isequal'

    interface Props {
        id: string
        data?: any
    }

    let { id, data }: Props = $props()

    let isCollapsed = $state(false)

    const nodeConfig = $derived(flowStore.nodeConfigs[id])
    const node = $derived(flowStore.nodes.find((n) => n.id === id))

    const nodeData = $derived({
        title: nodeConfig?.title || 'For Loop',
        color: data?.color || '#805AD5',
        acronym: 'FL',
        run: data?.run,
        config: nodeConfig,
        taskStatus: data?.taskStatus,
    })

    const isSelected = $derived(String(id) === String(flowStore.selectedNode))

    // Compute minimum dimensions from child nodes using flowStore
    const dimensions = $derived.by(() => {
        const childNodes = flowStore.nodes.filter((n) => n.parentId === id)
        const rect = getRelativeNodesBounds(childNodes as any[])
        return {
            minWidth: Math.max(200, rect.x + rect.width),
            minHeight: Math.max(100, rect.y + rect.height),
        }
    })

    // Keep input node's output schema in sync with parent's input_map
    $effect(() => {
        const inputNode = flowStore.nodes.find((n) => n.type === 'InputNode' && n.parentId === id)
        if (!inputNode || !nodeConfig?.input_map) return

        const derivedSchema: Record<string, string> = {}
        Object.entries(nodeConfig.input_map).forEach(([key, sourceField]) => {
            const [sourceNodeTitle, fieldName] = String(sourceField).split('.')
            if (sourceNodeTitle && fieldName) {
                const sourceNode = flowStore.nodes.find((n) => n.data?.title === sourceNodeTitle)
                if (sourceNode) {
                    const srcConfig = flowStore.nodeConfigs[sourceNode.id]
                    if (srcConfig?.output_schema && fieldName in srcConfig.output_schema) {
                        derivedSchema[key] = srcConfig.output_schema[fieldName]
                    }
                }
            }
        })

        const inputNodeConfig = flowStore.nodeConfigs[inputNode.id]
        if (!isEqual(inputNodeConfig?.output_schema, derivedSchema)) {
            flowStore.updateNodeConfigOnly(inputNode.id, {
                ...inputNodeConfig,
                output_schema: derivedSchema,
                has_fixed_output: true,
            })
        }
    })
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
        isVisible={true}
        minWidth={dimensions.minWidth}
        minHeight={dimensions.minHeight}
        lineStyle="border-color: rgb(148 163 184); display: none;"
        handleStyle="background-color: rgb(148 163 184); width: 1rem; height: 1rem; border-radius: 2px;"
    />
    <BaseNode
        {id}
        data={nodeData}
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
            <hr class="mt-2 border-border" />
            <div
                class="mt-2 bg-muted/10 rounded-md h-full"
                style="min-height: {dimensions.minHeight}px;"
            >
                <!-- Container for child nodes -->
            </div>
        </div>
    </BaseNode>
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
