<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import {
        SvelteFlow,
        Background,
        ConnectionMode,
        Panel,
        SelectionMode,
        getViewportForBounds,
        getNodesBounds,
        addEdge,
        type Connection,
        type EdgeTypes,
        type NodeTypes,
    } from '@xyflow/svelte'
    import '@xyflow/svelte/dist/style.css'
    import { toPng } from 'html-to-image'
    import { onMount, onDestroy, setContext, type Snippet } from 'svelte'
    import { flowStore } from '$lib/stores/flow.svelte'
    import { nodeTypesStore } from '$lib/stores/nodeTypes.svelte'
    import { panelStore } from '$lib/stores/panel.svelte'
    import { modeStore } from '$lib/stores/mode.svelte'
    import { isTargetAncestorOfSource } from '$lib/utils/cyclicEdgeUtils'
    import { getLayoutedNodes } from '$lib/utils/nodeLayoutUtils'
    import { adjustGroupNodesZIndex, applyModeToNodes, insertNodeBetweenNodes } from '$lib/utils/flowUtils'
    import { mode } from 'mode-watcher'
    import type { WorkflowCreateRequest, WorkflowResponse } from '$lib/types/api_types/workflowSchemas'
    import type { FlowWorkflowNode, FlowWorkflowEdge } from '$lib/types/api_types/nodeTypeSchemas'
    import type { PausedWorkflowResponse, PauseHistoryResponse, ResumeActionRequest } from '$lib/types/api_types/pausedWorkflowSchemas'
    import type { RunResponse } from '$lib/types/api_types/runSchemas'
    import { takePauseAction } from '$lib/utils/api'
    import { executionState, resumeWorkflowPolling, startTracePolling, stopTracePolling } from '$lib/actions/workflowExecution.svelte'

    import LoadingSpinner from '$lib/components/LoadingSpinner.svelte'
    import CollapsibleNodePanel from '$lib/components/nodes/CollapsibleNodePanel.svelte'
    import Operator from './footer/Operator.svelte'
    import CustomEdge from './Edge.svelte'
    import { saveWorkflow } from '$lib/actions/saveWorkflow.svelte'
    import EdgeNodePopover from './EdgeNodePopover.svelte'
    import { preferencesStore } from '$lib/stores/preferences.svelte'
    import { sidebarPanels } from '$lib/stores/sidebarPanels.svelte'
    import NodeOverviewSidebar from './NodeOverviewSidebar.svelte'
    import RunsOverviewSidebar from './RunsOverviewSidebar.svelte'
    import InitFitView from './InitFitView.svelte'

    // Node type components
    import DynamicNode from '$lib/components/nodes/DynamicNode.svelte'
    import InputNode from '$lib/components/nodes/InputNode.svelte'
    import NodeBottomPanel from '$lib/components/nodes/nodeBottomPanel/NodeBottomPanel.svelte'
    import PanViewportBridge from '$lib/components/nodes/nodeBottomPanel/PanViewportBridge.svelte'
    import HumanInputModal from '$lib/components/modals/HumanInputModal.svelte'
    import RouterNode from '$lib/components/nodes/logic/RouterNode.svelte'
    import CoalesceNode from '$lib/components/nodes/logic/CoalesceNode.svelte'
    import DynamicGroupNode from '$lib/components/nodes/loops/DynamicGroupNode.svelte'
    import AgentNode from '$lib/components/nodes/agent/AgentNode.svelte'

    interface Props {
        workflowData?: WorkflowCreateRequest | WorkflowResponse
        workflowID?: string
        onDownloadImageInit?: (handler: () => void) => void
        onStop?: () => void
        sidebarExtra?: Snippet
    }

    let {
        workflowData,
        workflowID,
        onDownloadImageInit,
        onStop,
        sidebarExtra,
    }: Props = $props()

    // ── Pause-action modal state ───────────────────────────────────────────
    let pauseActionNodeId = $state<string | null>(null)
    let isPauseModalOpen = $state(false)

    const pausedWorkflowForModal = $derived.by((): PausedWorkflowResponse | null => {
        if (!pauseActionNodeId || !executionState.currentRunId) return null
        const node = flowStore.nodes.find((n) => n.id === pauseActionNodeId)
        return {
            run: { id: executionState.currentRunId } as RunResponse,
            current_pause: {
                id: pauseActionNodeId,
                run_id: executionState.currentRunId,
                node_id: pauseActionNodeId,
                pause_message: (node?.data?.run as any)?.pause_message ?? null,
                pause_time: new Date().toISOString(),
                resume_time: null,
                resume_user_id: null,
                resume_action: null,
                input_data: node?.data?.run ?? null,
                comments: null,
            } as PauseHistoryResponse,
            workflow: {
                name: typeof workflowData === 'object' && 'name' in workflowData ? workflowData.name : 'Workflow',
                definition: flowStore.nodes.length > 0
                    ? { nodes: flowStore.nodes as any, links: flowStore.edges as any, test_inputs: [] }
                    : {},
            } as any,
        }
    })

    async function handlePauseActionSubmit(
        action: 'APPROVE' | 'DECLINE' | 'OVERRIDE',
        inputData: Record<string, any>,
        comments: string
    ) {
        if (!executionState.currentRunId) return
        try {
            await takePauseAction(executionState.currentRunId, {
                action,
                inputs: inputData,
                user_id: 'current-user',
                comments,
            } as ResumeActionRequest)
            resumeWorkflowPolling()
        } catch (err) {
            console.error('Failed to take pause action', err)
        } finally {
            isPauseModalOpen = false
            pauseActionNodeId = null
        }
    }

    setContext('traceContext', {
        readOnly: false,
        onPauseAction: (nodeId: string) => {
            pauseActionNodeId = nodeId
            isPauseModalOpen = true
        },
    })

    // Edge display context — consumed by Edge.svelte to compute hover/selected styles
    // Uses getters so the context values are reactive (read $state signals at access time)
    setContext('edgeDisplayContext', {
        get hoveredEdge() { return hoveredEdge },
        get hoveredNode() { return hoveredNode },
        get selectedEdgeId() { return flowStore.selectedEdgeId },
        get isDark() { return isDark },
        get handlePopoverOpen() { return handlePopoverOpen },
        onLabelEnter() {
            if (hoveredEdgeLeaveTimer) {
                clearTimeout(hoveredEdgeLeaveTimer)
                hoveredEdgeLeaveTimer = null
            }
        },
        onLabelLeave: onEdgeLeave,
    })

    // Edge popup state (add node between nodes)
    let popoverVisible = $state(false)
    let popoverPosition = $state({ x: 0, y: 0 })
    let selectedEdgeData: { sourceNode: FlowWorkflowNode; targetNode: FlowWorkflowNode; edgeId: string } | null = $state(null)

    let hoveredNode: string | null = $state(null)
    let hoveredEdge: string | null = $state(null)
    let hoveredEdgeLeaveTimer: ReturnType<typeof setTimeout> | null = null

    function onEdgeEnter(edgeId: string) {
        if (hoveredEdgeLeaveTimer) {
            clearTimeout(hoveredEdgeLeaveTimer)
            hoveredEdgeLeaveTimer = null
        }
        hoveredEdge = edgeId
    }

    function onEdgeLeave() {
        hoveredEdgeLeaveTimer = setTimeout(() => {
            hoveredEdge = null
            hoveredEdgeLeaveTimer = null
        }, 150)
    }

    // Node types registry — dynamically built from API data like the React version.
    // Special types map to dedicated components; all others map to DynamicNode.
    const SPECIAL_NODE_TYPES: NodeTypes = {
        InputNode,
        RouterNode,
        CoalesceNode,
        ForLoopNode: DynamicGroupNode,
        AgentNode,
    }

    const nodeTypes = $derived.by((): NodeTypes => {
        const types: NodeTypes = { ...SPECIAL_NODE_TYPES }
        if (nodeTypesStore.data) {
            for (const nodes of Object.values(nodeTypesStore.data)) {
                for (const node of nodes as any[]) {
                    if (!types[node.name]) {
                        types[node.name] = DynamicNode
                    }
                }
            }
        }
        return types
    })

    const edgeTypes: EdgeTypes = {
        custom: CustomEdge,
    }

    // Initialize flow when workflowData changes
    $effect(() => {
        if (workflowData && nodeTypesStore.data) {
            flowStore.initializeFlow({
                nodeTypes: nodeTypesStore.data,
                definition: workflowData.definition,
                workflowID,
                name: workflowData.name,
            })
        }
    })

    // Fetch node types on mount
    onMount(async () => {
        if (!nodeTypesStore.data) {
            await nodeTypesStore.fetch()
        }
    })

    const isDark = $derived($mode === 'dark')

    // Nodes with mode applied (pointer/hand affects draggable etc.)
    const nodesWithMode = $derived(
        applyModeToNodes(flowStore.nodes, modeStore.mode as 'pointer' | 'hand')
    )

    const nodesWithZIndex = $derived(adjustGroupNodesZIndex(nodesWithMode))

    // @xyflow/svelte only picks up edge changes when it receives new object references.
    // Map to fresh objects so that any flowStore.edges reassignment (e.g. after connect)
    // propagates into @xyflow's internal renderer.
    const edgesForFlow = $derived(
        flowStore.edges.map((e) => ({ ...e, type: 'custom' }))
    )

    function handlePopoverOpen(data: { sourceNode: FlowWorkflowNode; targetNode: FlowWorkflowNode; edgeId: string; screenPosition?: { x: number; y: number } }) {
        selectedEdgeData = data
        if (data.screenPosition) {
            popoverPosition = data.screenPosition
        }
        popoverVisible = true
    }

    function handleInsertNode(nodeType: string) {
        if (!selectedEdgeData) return
        insertNodeBetweenNodes(
            nodeType,
            selectedEdgeData.sourceNode as FlowWorkflowNode,
            selectedEdgeData.targetNode as FlowWorkflowNode,
            selectedEdgeData.edgeId,
        )
        popoverVisible = false
        selectedEdgeData = null
    }

    function handleConnect(connection: Connection) {
        flowStore.connect(connection)
    }

    function handleNodeDragStart(_: MouseEvent, node: FlowWorkflowNode) {
        // If the dragged node is not selected, deselect everything so it moves independently.
        // If it IS selected, preserve the selection (intentional multi-node drag).
        if (!node.selected) {
            flowStore.nodes = flowStore.nodes.map((n) => ({ ...n, selected: false }))
        }
    }

    function handleNodeClick(_: MouseEvent, node: FlowWorkflowNode) {
        flowStore.setSelectedNode(node.id)
    }

    function handleEdgeClick(_: MouseEvent, edge: FlowWorkflowEdge) {
        flowStore.setSelectedEdgeId(edge.id)
    }

    function handlePaneClick(_: { event: MouseEvent }) {
        flowStore.setSelectedNode(null)
        flowStore.setSelectedEdgeId(null)
        panelStore.setNodePanelExpanded(false)
    }

    function handleLayout() {
        const layouted = getLayoutedNodes(flowStore.nodes, flowStore.edges)
        flowStore.setNodes(layouted)
    }

    function handleDownloadImage() {
        const imageWidth = 1200
        const imageHeight = 675
        const bounds = getNodesBounds(flowStore.nodes)
        const zoomX = (imageWidth * 0.9) / (bounds.width || 1)
        const zoomY = (imageHeight * 0.9) / (bounds.height || 1)
        const optimalZoom = Math.min(zoomX, zoomY)

        const transform = getViewportForBounds(bounds, imageWidth, imageHeight, optimalZoom, optimalZoom, 0.05)

        const viewport = document.querySelector('.svelte-flow__viewport') as HTMLElement
        if (!viewport) return

        toPng(viewport, {
            backgroundColor: 'transparent',
            width: imageWidth,
            height: imageHeight,
            style: {
                width: `${imageWidth}px`,
                height: `${imageHeight}px`,
                transform: `translate(${transform.x}px, ${transform.y}px) scale(${transform.zoom})`,
            },
        })
            .then((dataUrl) => {
                const a = document.createElement('a')
                a.href = dataUrl
                a.download = `${flowStore.projectName || 'workflow'}.png`
                a.click()
            })
            .catch(console.error)
    }

    onMount(() => {
        if (onDownloadImageInit) {
            onDownloadImageInit(handleDownloadImage)
        }
        startTracePolling()
    })

    onDestroy(() => {
        stopTracePolling()
    })

    // Keyboard shortcuts
    let lastPasteTime = 0
    function handleKeyDown(e: KeyboardEvent) {
        const target = e.target as HTMLElement
        const tag = target.tagName.toLowerCase()
        if (target.isContentEditable || tag === 'input' || tag === 'textarea' || tag === 'select') return

        const nodePanelEl = document.querySelector('[data-node-panel]')
        const isNodePanelExpanded = nodePanelEl?.getAttribute('data-expanded') === 'true'
        const isNodePanelFocused = nodePanelEl?.contains(document.activeElement)

        if (e.key === 'Escape') {
            flowStore.setSelectedNode(null)
            flowStore.setSelectedEdgeId(null)
            panelStore.setNodePanelExpanded(false)
            return
        }

        if (e.key === 'Delete' || e.key === 'Backspace') {
            flowStore.deleteNodes(flowStore.nodes.filter((n) => n.selected).map((n) => n.id))
            if (flowStore.selectedEdgeId) {
                flowStore.deleteEdge(flowStore.selectedEdgeId)
            }
            return
        }

        if ((e.ctrlKey || e.metaKey) && !e.shiftKey) {
            if (e.key === 'c' && !window.getSelection()?.toString()) {
                flowStore.copySelection()
                return
            }
            if (e.key === 'x') {
                e.preventDefault()
                flowStore.cutSelection()
                return
            }
            if (e.key === 'v') {
                e.preventDefault()
                const now = Date.now()
                if (now - lastPasteTime < 300) return
                lastPasteTime = now
                flowStore.paste()
                return
            }
            // Cmd/Ctrl+I: layout (Cmd+L is browser-reserved and never reaches the page)
            if (e.key === 'i') {
                e.preventDefault()
                handleLayout()
                return
            }
        }

        if (e.key === 'v' && !e.ctrlKey && !e.metaKey) {
            modeStore.setMode('pointer')
            return
        }
        if (e.key === ' ') {
            modeStore.setMode('hand')
            return
        }
    }

    const isLoading = $derived(nodeTypesStore.status === 'loading')

    // Right sidebar resize
    let isSidebarDragging = $state(false)
    let sidebarDragStartX = 0
    let sidebarDragStartWidth = 0

    function handleSidebarPointerDown(e: PointerEvent) {
        isSidebarDragging = true
        sidebarDragStartX = e.clientX
        sidebarDragStartWidth = sidebarPanels.width
        ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
        document.body.style.cursor = 'ew-resize'
        e.preventDefault()
    }

    function handleSidebarPointerMove(e: PointerEvent) {
        if (!isSidebarDragging) return
        const delta = sidebarDragStartX - e.clientX
        sidebarPanels.setWidth(sidebarDragStartWidth + delta)
    }

    function handleSidebarPointerUp() {
        isSidebarDragging = false
        document.body.style.cursor = ''
    }

    // Auto-save on node/edge changes (debounced via saveWorkflow).
    // Guard: never save when there are no nodes — that means the flow hasn't
    // initialized yet (nodeTypes not loaded) and we'd overwrite the backend data.
    $effect(() => {
        const _nodes = flowStore.nodes.length
        const _edges = flowStore.edges.length
        const _configs = Object.keys(flowStore.nodeConfigs).length
        if (flowStore.workflowID && flowStore.nodes.length > 0) {
            saveWorkflow()
        }
    })
</script>

<svelte:window onkeydown={handleKeyDown} />

{#if isLoading}
    <LoadingSpinner />
{:else}
    <div class="flex flex-row w-full h-full">


        <!-- Left column: canvas + bottom panel -->
        <div class="flex-1 flex flex-col min-w-0">
        <div class="flex-1 min-h-0 overflow-hidden relative" style="z-index: 1;">
            <SvelteFlow
                bind:nodes={flowStore.nodes}
                edges={edgesForFlow}
                onedgeschange={(changes: any[]) => {
                    changes.filter((c) => c.type === 'remove').forEach((c) => flowStore.deleteEdge(c.id))
                }}
                {nodeTypes}
                {edgeTypes}
                onnodedragstart={({ node, event }) => handleNodeDragStart(event as MouseEvent, node as FlowWorkflowNode)}
                onnodeclick={({ node, event }) => handleNodeClick(event as MouseEvent, node as FlowWorkflowNode)}
                onedgeclick={({ edge, event }) => handleEdgeClick(event, edge as FlowWorkflowEdge)}
                onpaneclick={handlePaneClick}
                onconnect={(connection) => handleConnect(connection)}
                onnodepointerenter={({ node }) => (hoveredNode = node.id)}
                onnodepointerleave={() => (hoveredNode = null)}
                onedgepointerenter={({ edge }) => onEdgeEnter(edge.id)}
                onedgepointerleave={() => onEdgeLeave()}
                panOnDrag={modeStore.mode === 'hand' && !flowStore.nodes.some((n) => n.selected)}
                panOnScroll={true}
                zoomOnScroll={true}
                minZoom={0.1}
                maxZoom={2}
                selectionMode={modeStore.mode === 'pointer' ? SelectionMode.Full : SelectionMode.Partial}
                selectNodesOnDrag={modeStore.mode === 'pointer'}
                selectionOnDrag={modeStore.mode === 'pointer'}
                deleteKey={null}
                connectionMode={ConnectionMode.Loose}
                proOptions={{ hideAttribution: true }}
            >
                <Background />
                <Operator {handleLayout} {handleDownloadImage} />
                <!-- Node panel inside SvelteFlow so useSvelteFlow() context is available -->
                <Panel position="top-left" style="z-index: 15; margin: 1rem;">
                    <CollapsibleNodePanel />
                </Panel>
                <!-- Bridge to register panToNode with panelStore -->
                <Panel position="top-left" style="display:none;">
                    <PanViewportBridge />
                    <InitFitView />
                </Panel>

            </SvelteFlow>
        </div>

        <!-- Bottom panel: node properties -->
        <NodeBottomPanel nodeID={flowStore.selectedNode} {onStop} />
        </div>

        <!-- Right column: sidebars stacked vertically -->
        {#if sidebarPanels.isOpen('nodes') || sidebarPanels.isOpen('runs') || (sidebarExtra && sidebarPanels.isOpen('chat'))}
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div
                class="flex flex-col border-l border-border relative flex-shrink-0"
                style="width: {sidebarPanels.width}px; transition: {isSidebarDragging ? 'none' : 'width 0ms'};"
            >
                <!-- Resize handle: wide invisible hit area straddling the border -->
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <div
                    class="absolute top-0 bottom-0 w-5 cursor-ew-resize z-10 touch-none group flex items-center justify-center"
                    style="left: -10px;"
                    title="Drag to resize"
                    onpointerdown={handleSidebarPointerDown}
                    onpointermove={handleSidebarPointerMove}
                    onpointerup={handleSidebarPointerUp}
                >
                    <!-- Pill bar: hidden at rest, visible on hover/drag -->
                    <div class="w-[4px] h-12 rounded-full bg-foreground/60 opacity-0 group-hover:opacity-100 {isSidebarDragging ? '!opacity-100' : ''} transition-opacity duration-150"></div>
                </div>
                <!-- Wrapper adds left breathing room so content clears the grip handle -->
                <div class="flex flex-col flex-1 min-h-0">
                    {#if sidebarExtra && sidebarPanels.isOpen('chat')}
                        {@render sidebarExtra()}
                    {/if}
                    {#if sidebarPanels.isOpen('nodes')}
                        <NodeOverviewSidebar onclose={() => sidebarPanels.toggle('nodes')} />
                    {/if}
                    {#if sidebarPanels.isOpen('runs')}
                        <RunsOverviewSidebar onclose={() => sidebarPanels.toggle('runs')} />
                    {/if}
                </div>
            </div>
        {/if}

        <!-- Edge node insertion popover -->
        {#if popoverVisible && selectedEdgeData}
            <EdgeNodePopover
                x={popoverPosition.x}
                y={popoverPosition.y}
                onSelect={handleInsertNode}
                onClose={() => { popoverVisible = false; selectedEdgeData = null }}
            />
        {/if}
    </div>
{/if}

<!-- Pause action modal -->
{#if pausedWorkflowForModal}
    <HumanInputModal
        isOpen={isPauseModalOpen}
        onOpenChange={(open) => { isPauseModalOpen = open; if (!open) pauseActionNodeId = null }}
        workflow={pausedWorkflowForModal}
        onSubmit={handlePauseActionSubmit}
    />
{/if}
