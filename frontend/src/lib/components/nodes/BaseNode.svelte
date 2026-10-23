<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { Handle, Position, useConnection } from '@xyflow/svelte'
    import Icon from '@iconify/svelte'
    import { getContext } from 'svelte'
    import { Button } from '$lib/components/ui/button'
    import { Input } from '$lib/components/ui/input'
    import { flowStore } from '$lib/stores/flow.svelte'
    import { getNodeTitle, duplicateNode } from '$lib/utils/flowUtils'
    import { convertToPythonVariableName } from '$lib/utils/variableNameUtils'
    import { isTargetAncestorOfSource } from '$lib/utils/cyclicEdgeUtils'
    import NodeControls from './NodeControls.svelte'
    import NodeErrorDisplay from './NodeErrorDisplay.svelte'
    import NodeOutputDisplay from './NodeOutputDisplay.svelte'
    import InputHandleRow from './shared/InputHandleRow.svelte'
    import type { FlowWorkflowNode } from '$lib/types/api_types/nodeTypeSchemas'
    import type { TaskStatus } from '$lib/types/api_types/taskSchemas'
    import { getStatusColor } from '$lib/utils/statusConfig'
    import type { Snippet } from 'svelte'

    interface TraceContext {
        readOnly: boolean
        onPauseAction: (nodeId: string) => void
        onPartialRun?: (nodeId: string, nodeTitle: string) => Promise<void>
    }

    interface Props {
        isCollapsed: boolean
        setIsCollapsed: (collapsed: boolean) => void
        id: string
        data?: FlowWorkflowNode['data']
        children?: Snippet
        style?: string
        isInputNode?: boolean
        className?: string
        isResizable?: boolean
        handleOpenModal?: (open: boolean) => void
        positionAbsoluteX?: number
        positionAbsoluteY?: number
        renderOutputHandles?: Snippet
        hideHandles?: boolean
    }

    let {
        isCollapsed,
        setIsCollapsed,
        id,
        data,
        children,
        style = '',
        isInputNode = false,
        className = '',
        isResizable = false,
        handleOpenModal,
        renderOutputHandles,
        hideHandles = false,
    }: Props = $props()

    const traceCtx = getContext<TraceContext | undefined>('traceContext')
    const isReadOnly = traceCtx?.readOnly ?? false

    let editingTitle = $state(false)
    let isRunning = $state(false)
    let titleInputValue = $state('')

    // Close title editing when clicking outside the title input
    function closeTitleOnOutsideMousedown(node: HTMLElement) {
        function handler(e: MouseEvent) {
            if (!node.contains(e.target as Node)) {
                editingTitle = false
            }
        }
        document.addEventListener('mousedown', handler, true)
        return {
            destroy() {
                document.removeEventListener('mousedown', handler, true)
            }
        }
    }

    const connection = useConnection()

    const selectedNodeId = $derived(flowStore.selectedNode)
    const parentId = $derived(flowStore.nodes.find((n) => n.id === id)?.parentId)
    const nodePosition = $derived(flowStore.nodes.find((n) => n.id === id)?.position)
    const parentPosition = $derived(
        parentId ? flowStore.nodes.find((n) => n.id === parentId)?.position : undefined
    )
    const isTool = $derived.by(() => {
        const node = flowStore.nodes.find((n) => n.id === id)
        if (node?.data?.isTool) return true
        const parentNode = node?.parentId ? flowStore.nodes.find((n) => n.id === node.parentId) : undefined
        return parentNode?.type === 'AgentNode'
    })

    const isSelected = $derived(String(id) === String(selectedNodeId))

    const nodeRunStatus = $derived(data?.taskStatus as TaskStatus)

    // Effective border color: status takes priority, then selection highlight, then idle border
    const outlineColor = $derived.by(() => {
        if (nodeRunStatus) return getStatusColor(nodeRunStatus)
        if (data?.run) return '#4CAF50'
        if (isSelected) return 'hsl(var(--primary))'
        return 'hsl(var(--border))'
    })

    const outlineWidth = $derived(isSelected ? 2.5 : (data?.run || nodeRunStatus === 'COMPLETED') ? 2 : 1)

    const acronym = $derived(data?.acronym || 'N/A')
    const color = $derived(data?.color || '#ccc')

    // Predecessor nodes (incoming connections)
    const predecessorNodes = $derived.by(() => {
        const edges = flowStore.edges
        const nodes = flowStore.nodes
        const conn = connection.current

        let result: any[] = edges
            .filter((e) => e.target === id)
            .map((edge) => {
                const srcNode = nodes.find((n) => n.id === edge.source)
                if (!srcNode) return null
                if (srcNode.type === 'RouterNode' && edge.sourceHandle) {
                    return { ...srcNode, handle_id: edge.sourceHandle }
                }
                return srcNode
            })
            .filter(Boolean)

        // If connection is in progress towards this node, preview it
        if (conn.inProgress && conn.toNode && conn.toNode.id === id) {
            const fromNodeParentId = (conn.fromNode as any)?.parentId
            const toNodeParentId = (conn.toNode as any)?.parentId
            const canConnect =
                fromNodeParentId === toNodeParentId &&
                !isTargetAncestorOfSource(conn.fromNode.id, conn.toNode.id, nodes, edges)

            if (canConnect && conn.fromNode && !result.find((n: any) => n?.id === conn.fromNode.id)) {
                if (conn.fromNode.type === 'RouterNode' && conn.fromHandle) {
                    result = [
                        ...result,
                        {
                            id: conn.fromNode.id,
                            type: conn.fromNode.type,
                            handle_id: (conn.fromHandle as any).id,
                            data: { title: (conn.fromNode.data as any)?.title || conn.fromNode.id },
                        },
                    ]
                } else {
                    result = [
                        ...result,
                        {
                            id: conn.fromNode.id,
                            type: conn.fromNode.type,
                            data: { title: (conn.fromNode.data as any)?.title || conn.fromNode.id },
                        },
                    ]
                }
            }
        }

        // Deduplicate
        return result.filter(
            (node: any, index: number, self: any[]) => self.findIndex((n: any) => n?.id === node?.id) === index
        )
    })

    function handleTitleChange(newTitle: string) {
        const validTitle = convertToPythonVariableName(newTitle)
        if (validTitle && validTitle !== getNodeTitle(data)) {
            flowStore.updateNodeTitle(id, validTitle)
        }
    }

    function handleDelete() {
        flowStore.deleteNode(id)
        if (selectedNodeId === id) {
            flowStore.setSelectedNode(null)
        }
    }

    function handleDuplicate() {
        if (!data) return
        duplicateNode(id)
    }

    function handleDetach() {
        if (!data || !nodePosition || !parentPosition) return
        const absolutePosition = {
            x: nodePosition.x + parentPosition.x,
            y: nodePosition.y + parentPosition.y,
        }
        flowStore.updateNodeParentAndCoordinates(id, undefined, absolutePosition)
    }

    async function handlePartialRun() {
        if (!data) return
        isRunning = true
        flowStore.updateNodeDataOnly(id, { run: undefined, taskStatus: 'RUNNING' })

        try {
            if (traceCtx?.onPartialRun) {
                await traceCtx.onPartialRun(id, data.title)
            } else {
                const workflowId = window.location.pathname.split('/').pop()
                if (!workflowId) return
                const { partialRun } = await import('$lib/actions/partialRun.svelte')
                await partialRun(workflowId, id, data.title)
            }
        } catch (err) {
            console.error('Error running node:', err)
        } finally {
            isRunning = false
        }
    }

    // In trace context, only show play button on nodes that aren't already done/running.
    // Covers FAILED, PENDING, and undefined (never-executed) nodes.
    const showPartialRunInTrace = $derived(
        traceCtx?.onPartialRun != null &&
        nodeRunStatus !== 'COMPLETED' &&
        nodeRunStatus !== 'RUNNING'
    )

    const resizableClass = $derived(isResizable ? 'w-full h-full' : '')
    const nodeType = $derived(flowStore.nodes.find((n) => n.id === id)?.type)
    const canDelete = $derived(!isInputNode && nodeType !== 'OutputNode')
</script>

<div
    class="group relative {resizableClass}"
    id="node-{id}"
    draggable={false}
    role="presentation"
    onpointerdown={(e) => {
        if (!(e.target as HTMLElement).closest('input, textarea, select, button, [role="combobox"]')) {
            (document.activeElement as HTMLElement)?.blur()
        }
    }}
>
    <div class={resizableClass}>
        <!-- Full-body target handle when connection in progress -->
        {#if connection.current.inProgress}
            <Handle
                type="target"
                position={Position.Left}
                id="node-body-{id}"
                style="top: 50%; left: 0; width: 30%; height: 100%; z-index: 10; opacity: 0; pointer-events: auto;"
                isConnectable={true}
                isConnectableStart={false}
            />
        {/if}

        <div class="react-flow__node-drag-handle {resizableClass}" style="width: 100%; height: 100%; pointer-events: none;">
            <div
                class="base-node {className} {resizableClass} bg-background rounded-xl border pointer-events-auto transition-all duration-200"
                style="outline: {outlineWidth}px solid {outlineColor}; outline-offset: 2px; {isSelected ? `box-shadow: 0 0 0 4px ${outlineColor}26;` : ''} {style}"
            >
                {#if data}
                    <!-- Header -->
                    <div class="relative px-3 pt-2" style="padding-bottom: {isCollapsed ? '4px' : '16px'};">
                        {#if editingTitle}
                            <div use:closeTitleOnOutsideMousedown>
                                <Input
                                    autofocus
                                    value={titleInputValue}
                                    class="text-sm h-7"
                                    onclick={(e) => e.stopPropagation()}
                                    oninput={(e) => {
                                        const valid = convertToPythonVariableName((e.target as HTMLInputElement).value)
                                        titleInputValue = valid
                                    }}
                                    onblur={() => {
                                        handleTitleChange(titleInputValue)
                                        editingTitle = false
                                    }}
                                    onkeydown={(e) => {
                                        if (e.key === 'Enter' || e.key === 'Escape') {
                                            e.stopPropagation()
                                            e.preventDefault()
                                            handleTitleChange(titleInputValue)
                                            editingTitle = false
                                        }
                                    }}
                                />
                            </div>
                        {:else}
                            <div class="flex items-center pr-16">
                                {#if data.logo}
                                    <img src={data.logo} alt="Node Logo" class="mr-2 max-h-8 max-w-8 mb-3" />
                                {/if}
                                <!-- svelte-ignore a11y_click_events_have_key_events -->
                                <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
                                <h3
                                    class="text-base font-semibold {isReadOnly ? '' : 'cursor-pointer hover:text-primary'} transition-colors dark:text-white truncate"
                                    style="margin-bottom: {isCollapsed ? '4px' : '8px'};"
                                    onclick={(e) => {
                                        if (isReadOnly) return
                                        e.stopPropagation()
                                        titleInputValue = getNodeTitle(data)
                                        editingTitle = true
                                    }}
                                >
                                    {getNodeTitle(data)}
                                </h3>
                            </div>
                        {/if}

                        <!-- Controls: collapse button + tag -->
                        <div class="absolute top-2 right-2 flex items-center gap-1">
                            <Button
                                variant="ghost"
                                size="icon"
                                class="h-6 w-6 dark:bg-muted/20"
                                onclick={(e) => { e.stopPropagation(); setIsCollapsed(!isCollapsed) }}
                            >
                                <Icon
                                    icon={isCollapsed ? 'solar:alt-arrow-down-linear' : 'solar:alt-arrow-up-linear'}
                                    width={14}
                                    class="text-muted-foreground"
                                />
                            </Button>
                            <div
                                class="px-2 py-0.5 rounded-xl text-xs font-medium text-white flex items-center"
                                style="background-color: {color};"
                            >
                                {acronym}
                            </div>
                        </div>
                    </div>
                {/if}

                {#if !isCollapsed}
                    <div class="border-t border-border"></div>
                {/if}

                <!-- Body -->
                <div class="px-3 py-2">
                    <div id="node-{id}-wrapper">
                        <!-- Handles -->
                        {#if data && !hideHandles && !isTool}
                            <div class="handles-wrapper flex w-full" id="handles">
                                <div class="input-handles flex flex-col flex-1 items-start overflow-hidden" id="input-handles">
                                    {#each predecessorNodes as node (node.id + (node.handle_id || ''))}
                                        {@const handleId = node.type === 'RouterNode' && node.handle_id
                                            ? (node.data?.title || node.id) + '.' + node.handle_id
                                            : String(node.data?.title || node.id || '')}
                                        {@const nodeId = node.type === 'RouterNode'
                                            ? node.id + '.' + node.handle_id
                                            : node.id}
                                        <InputHandleRow
                                            id={nodeId}
                                            keyName={handleId}
                                            {isCollapsed}
                                            nodeId={id}
                                        />
                                    {/each}
                                </div>
                                {#if renderOutputHandles}
                                    {@render renderOutputHandles()}
                                {/if}
                            </div>
                        {/if}

                        {#if children}
                            {@render children()}
                        {/if}
                        {#if data?.error}
                            <NodeErrorDisplay error={data.error} />
                        {/if}
                        <NodeOutputDisplay output={data?.run} />
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Node controls (shown on hover) -->
    <NodeControls
        {id}
        {isRunning}
        loading={false}
        {isInputNode}
        hasRun={data?.run !== undefined}
        handlePartialRun={
            nodeType === 'HumanInterventionNode' && nodeRunStatus === 'PAUSED' ? undefined :
            (!isReadOnly || showPartialRunInTrace) ? handlePartialRun : undefined
        }
        handleDelete={isReadOnly || !canDelete ? undefined : handleDelete}
        handleDuplicate={isReadOnly || !canDelete ? undefined : handleDuplicate}
        handleDetach={isReadOnly || !parentId ? undefined : handleDetach}
        readOnly={isReadOnly}
        taskStatus={data?.taskStatus}
        onPauseAction={traceCtx ? () => traceCtx.onPauseAction(id) : undefined}
    />
</div>

<style>
    .handles-wrapper {
        min-height: 32px;
    }

    /* Suppress xyflow's default selection box — we render our own */
    :global(.svelte-flow__node.selected) {
        outline: none !important;
    }
</style>
