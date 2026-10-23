<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import type { NodeProps } from '@xyflow/svelte'
    import { Handle, Position } from '@xyflow/svelte'
    import { Button } from '$lib/components/ui/button'
    import { Input } from '$lib/components/ui/input'
    import Icon from '@iconify/svelte'
    import { flowStore } from '$lib/stores/flow.svelte'
    import { convertToPythonVariableName } from '$lib/utils/variableNameUtils'
    import BaseNode from './BaseNode.svelte'
    import type { FlowWorkflowNode } from '$lib/types/api_types/nodeTypeSchemas'

    interface Props extends NodeProps {
        data: FlowWorkflowNode['data']
        readOnly?: boolean
    }

    let { id, data, readOnly = false }: Props = $props()

    let isCollapsed = $state(false)
    let editingField: string | null = $state(null)
    let newFieldValue = $state('')
    let showKeyError = $state(false)

    const nodeConfig = $derived(flowStore.nodeConfigs[id])
    const isFixedOutput = $derived(nodeConfig?.has_fixed_output || false)
    const outputSchema = $derived(nodeConfig?.output_schema || {})
    const outputSchemaKeys = $derived(Object.keys(outputSchema))

    function handleAddVariable() {
        if (!newFieldValue.trim() || isFixedOutput) return
        const newKey = convertToPythonVariableName(newFieldValue)
        if (newKey !== newFieldValue) {
            showKeyError = true
            setTimeout(() => (showKeyError = false), 3000)
        }
        flowStore.setWorkflowInputVariable(newKey, 'string')
        newFieldValue = ''
    }

    function handleDeleteVariable(key: string) {
        flowStore.deleteWorkflowInputVariable(key)
    }

    function handleUpdateVariableKey(oldKey: string, newKey: string) {
        const valid = convertToPythonVariableName(newKey)
        if (valid && valid !== oldKey) {
            flowStore.updateWorkflowInputVariableKey(oldKey, valid)
        }
        editingField = null
    }

    // Close editing when clicking outside the editing input
    function closeOnOutsideMousedown(node: HTMLElement) {
        function handler(e: MouseEvent) {
            if (!node.contains(e.target as Node)) {
                editingField = null
            }
        }
        document.addEventListener('mousedown', handler, true)
        return {
            destroy() {
                document.removeEventListener('mousedown', handler, true)
            }
        }
    }
</script>

{#snippet inputNodeContent()}
    {#if !isCollapsed}
        <!-- Key list + handle column (mirrors React layout) -->
        <div class="flex items-stretch mt-2">
            <!-- Key list column -->
            <div class="flex-1 flex flex-col border-r border-border pr-1 min-w-0">
                {#each outputSchemaKeys as key}
                    <div class="flex items-center gap-1 min-h-[28px]">
                        {#if editingField === key}
                            <div use:closeOnOutsideMousedown class="flex-1 min-w-0">
                                <Input
                                    autofocus
                                    value={key}
                                    class="h-6 text-xs w-full"
                                    onclick={(e) => e.stopPropagation()}
                                    onblur={(e) => handleUpdateVariableKey(key, (e.target as HTMLInputElement).value)}
                                    onkeydown={(e) => {
                                        if (e.key === 'Enter') handleUpdateVariableKey(key, (e.target as HTMLInputElement).value)
                                        if (e.key === 'Escape') editingField = null
                                    }}
                                />
                            </div>
                        {:else}
                            <span
                                class="text-sm font-medium flex-1 cursor-pointer hover:text-primary truncate text-foreground/80"
                                role="button"
                                tabindex="0"
                                onclick={(e) => { e.stopPropagation(); !isFixedOutput && !readOnly && (editingField = key) }}
                                onkeydown={(e) => {
                                    if (e.key === 'Enter' || e.key === ' ') {
                                        e.stopPropagation()
                                        !isFixedOutput && !readOnly && (editingField = key)
                                    }
                                }}
                            >{key}</span>
                        {/if}
                        {#if !isFixedOutput && !readOnly}
                            <Button
                                variant="ghost"
                                size="icon"
                                class="h-5 w-5 shrink-0"
                                onclick={(e) => { e.stopPropagation(); handleDeleteVariable(key) }}
                            >
                                <Icon icon="solar:trash-bin-trash-linear" width={12} class="text-muted-foreground" />
                            </Button>
                        {/if}
                    </div>
                {/each}
            </div>

            <!-- Handle column: inline (position: relative) so it aligns with the key rows -->
            <div class="w-6 flex items-center justify-center shrink-0">
                <Handle
                    type="source"
                    position={Position.Right}
                    id={String(id)}
                    class="!w-3 !h-3 !bg-primary/70 !border-2 !border-background !relative !top-auto !right-auto !transform-none"
                    isConnectable={true}
                />
            </div>
        </div>

        <!-- Add field row (below the key list + handle row) -->
        {#if !isFixedOutput && !readOnly}
            <div class="flex items-center gap-1 mt-2">
                <Input
                    placeholder="Enter new field name"
                    value={newFieldValue}
                    class="h-7 text-sm flex-1"
                    onclick={(e) => e.stopPropagation()}
                    oninput={(e) => (newFieldValue = (e.target as HTMLInputElement).value)}
                    onkeydown={(e) => { if (e.key === 'Enter') handleAddVariable() }}
                />
                <Button variant="ghost" size="icon" class="h-7 w-7 shrink-0" onclick={(e) => { e.stopPropagation(); handleAddVariable() }}>
                    <Icon icon="solar:add-circle-linear" width={16} class="text-primary" />
                </Button>
            </div>
            {#if showKeyError}
                <p class="text-xs text-destructive mt-1">Variable names must be valid Python identifiers.</p>
            {/if}
        {/if}
    {:else}
        <!-- Collapsed: single handle positioned absolutely at node right edge -->
        <Handle
            type="source"
            position={Position.Right}
            id={String(id)}
            class="!w-3 !h-3 !bg-primary/70 !border-2 !border-background !opacity-50"
            isConnectable={false}
        />
    {/if}
{/snippet}

<BaseNode
    {id}
    {data}
    {isCollapsed}
    setIsCollapsed={(v) => (isCollapsed = v)}
    isInputNode={true}
    hideHandles={true}
>
    {#snippet children()}
        {@render inputNodeContent()}
    {/snippet}
</BaseNode>
