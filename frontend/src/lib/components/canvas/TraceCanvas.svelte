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
        getViewportForBounds,
        getNodesBounds,
        type EdgeTypes,
        type NodeTypes,
    } from '@xyflow/svelte'
    import '@xyflow/svelte/dist/style.css'
    import { toPng } from 'html-to-image'
    import { onMount, untrack, setContext } from 'svelte'
    import { flowStore } from '$lib/stores/flow.svelte'
    import { nodeTypesStore } from '$lib/stores/nodeTypes.svelte'
    import { sidebarPanels } from '$lib/stores/sidebarPanels.svelte'
    import { getLayoutedNodes } from '$lib/utils/nodeLayoutUtils'
    import { getStyledEdges } from '$lib/utils/flowUtils'
    import { mode } from 'mode-watcher'
    import type { WorkflowDefinition } from '$lib/types/api_types/workflowSchemas'
    import type { TaskResponse } from '$lib/types/api_types/taskSchemas'
    import type { FlowWorkflowNode, FlowWorkflowEdge } from '$lib/types/api_types/nodeTypeSchemas'
    import type { PausedWorkflowResponse, PauseHistoryResponse, ResumeActionRequest } from '$lib/types/api_types/pausedWorkflowSchemas'
    import type { RunResponse } from '$lib/types/api_types/runSchemas'
    import { takePauseAction, runPartialWorkflow } from '$lib/utils/api'

    import LoadingSpinner from '$lib/components/LoadingSpinner.svelte'
    import Operator from './footer/Operator.svelte'
    import CustomEdge from './Edge.svelte'
    import NodeBottomPanel from '$lib/components/nodes/nodeBottomPanel/NodeBottomPanel.svelte'
    import PanViewportBridge from '$lib/components/nodes/nodeBottomPanel/PanViewportBridge.svelte'
    import HumanInputModal from '$lib/components/modals/HumanInputModal.svelte'
    import NodeOverviewSidebar from './NodeOverviewSidebar.svelte'
    import RunsOverviewSidebar from './RunsOverviewSidebar.svelte'

    // Node type components
    import DynamicNode from '$lib/components/nodes/DynamicNode.svelte'
    import InputNode from '$lib/components/nodes/InputNode.svelte'
    import RouterNode from '$lib/components/nodes/logic/RouterNode.svelte'
    import CoalesceNode from '$lib/components/nodes/logic/CoalesceNode.svelte'
    import DynamicGroupNode from '$lib/components/nodes/loops/DynamicGroupNode.svelte'
    import AgentNode from '$lib/components/nodes/agent/AgentNode.svelte'

    interface Props {
        workflowData?: { name: string; definition: WorkflowDefinition }
        workflowID?: string | null
        tasksData?: TaskResponse[]
        onDownloadImageInit?: (handler: () => void) => void
        projectName?: string
        runId?: string | null
        initialInputs?: Record<string, any>
    }

    let { workflowData, workflowID, tasksData = [], onDownloadImageInit, projectName = 'workflow', runId = null, initialInputs = {} }: Props = $props()

    // ── Pause-action modal state ───────────────────────────────────────────
    let pauseActionNodeId = $state<string | null>(null)
    let isPauseModalOpen = $state(false)

    const pausedTask = $derived(
        pauseActionNodeId ? tasksData.find((t) => t.node_id === pauseActionNodeId) ?? null : null
    )

    const pausedWorkflowForModal = $derived.by((): PausedWorkflowResponse | null => {
        if (!pausedTask || !workflowData) return null
        return {
            run: { id: pausedTask.run_id } as RunResponse,
            current_pause: {
                id: pausedTask.id,
                run_id: pausedTask.run_id,
                node_id: pausedTask.node_id,
                pause_message: (pausedTask.inputs as any)?.pause_message ?? null,
                pause_time: pausedTask.start_time ?? new Date().toISOString(),
                resume_time: null,
                resume_user_id: null,
                resume_action: null,
                input_data: pausedTask.inputs ?? null,
                comments: null,
            } as PauseHistoryResponse,
            workflow: workflowData.definition,
        }
    })

    async function handlePauseActionSubmit(
        action: 'APPROVE' | 'DECLINE' | 'OVERRIDE',
        inputData: Record<string, any>,
        comments: string
    ) {
        if (!pausedTask) return
        try {
            await takePauseAction(pausedTask.run_id, {
                action,
                inputs: inputData,
                user_id: 'current-user',
                comments,
            } as ResumeActionRequest)
        } catch (err) {
            console.error('Failed to take pause action', err)
        } finally {
            isPauseModalOpen = false
            pauseActionNodeId = null
        }
    }

    async function handleTracePartialRun(nodeId: string, _nodeTitle: string): Promise<void> {
        if (!workflowID) return

        const partialOutputs: Record<string, any> = {}
        flowStore.nodes.forEach((n) => {
            if (n.id !== nodeId && (n.data as any)?.run) {
                partialOutputs[n.id] = (n.data as any).run
            }
        })

        // Mark node as running optimistically
        flowStore.updateNodeDataOnly(nodeId, { taskStatus: 'RUNNING' })

        try {
            // Backend now runs async and returns the run ID immediately
            const data = await runPartialWorkflow(
                workflowID,
                initialInputs,
                partialOutputs,
                runId,
                [nodeId]
            )
            if (data?.id) {
                // Poll until done, then apply updated node statuses
                const { getRunStatus } = await import('$lib/utils/api')
                const poll = async () => {
                    try {
                        const status = await getRunStatus(data.id)
                        const isDone = status.status !== 'RUNNING' && status.status !== 'PENDING'
                        if (isDone) {
                            const precomputedNodeIds = new Set(Object.keys(partialOutputs))
                            ;(status.tasks ?? []).forEach((task: any) => {
                                if (precomputedNodeIds.has(task.node_id)) return
                                flowStore.updateNodeDataOnly(task.node_id, {
                                    run: task.outputs ?? {},
                                    error: task.error ?? null,
                                    taskStatus: task.status,
                                })
                            })
                        } else {
                            setTimeout(poll, 1500)
                        }
                    } catch { /* ignore poll errors */ }
                }
                setTimeout(poll, 1000)
            }
        } catch (err: any) {
            flowStore.updateNodeDataOnly(nodeId, { taskStatus: 'FAILED', error: err?.message ?? 'Unknown error' })
        }
    }

    // Provide trace context to all descendant node components
    setContext('traceContext', {
        readOnly: true,
        onPauseAction: (nodeId: string) => {
            pauseActionNodeId = nodeId
            isPauseModalOpen = true
        },
        onPartialRun: handleTracePartialRun,
    })

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

    const isDark = $derived($mode === 'dark')

    let hoveredNode: string | null = $state(null)
    let hoveredEdge: string | null = $state(null)

    // Initialize the flow synchronously (before SvelteFlow mounts) so that nodes
    // are present on the first render and fitView + node measurement work correctly.
    // The parent page guarantees both workflowData and nodeTypesStore.data are set
    // before TraceCanvas is ever rendered.
    if (workflowData && nodeTypesStore.data) {
        flowStore.initializeFlow({
            nodeTypes: nodeTypesStore.data,
            definition: workflowData.definition,
            workflowID: workflowID ?? undefined,
            name: workflowData.name,
        })
    }

    // Apply task status/outputs to nodes after initialization.
    // untrack() prevents flowStore.nodes (read inside updateNodeDataOnly) from
    // becoming a reactive dependency — otherwise the effect loops: it writes nodes,
    // which re-triggers it, which writes nodes again.
    $effect(() => {
        const tasks = tasksData  // tracked: re-run when tasksData changes
        if (tasks && tasks.length > 0) {
            untrack(() => {
                tasks.forEach((task: TaskResponse) => {
                    flowStore.updateNodeDataOnly(task.node_id, {
                        run: task.outputs || {},
                        error: task.error || null,
                        taskStatus: task.status,
                    })
                    if (task.subworkflow_output) {
                        Object.entries(task.subworkflow_output).forEach(([subNodeId, outputs]) => {
                            flowStore.updateNodeDataOnly(subNodeId, {
                                run: outputs,
                                taskStatus: 'COMPLETED',
                            })
                        })
                    }
                })
            })
        }
    })

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

    const styledEdges = $derived(
        getStyledEdges({
            edges: flowStore.edges as FlowWorkflowEdge[],
            hoveredNode,
            hoveredEdge,
            selectedEdgeId: null,
            isDark,
            readOnly: true,
        })
    )

    // Note: adjustGroupNodesZIndex is not applied here because @xyflow/svelte requires
    // bind:nodes for proper node measurement (visibility). ForLoopNode z-index is handled
    // via its own inline style in the component.

    function handlePaneClick(_: { event: MouseEvent }) {
        if (flowStore.selectedNode) {
            flowStore.setSelectedNode(null)
        }
    }

    function handleLayout() {
        const layouted = getLayoutedNodes(flowStore.nodes as FlowWorkflowNode[], flowStore.edges as FlowWorkflowEdge[])
        flowStore.setNodes(layouted)
    }

    function handleDownloadImage() {
        const imageWidth = 1200
        const imageHeight = 675
        const nodesBounds = getNodesBounds(flowStore.nodes)
        const zoomX = (imageWidth * 0.9) / (nodesBounds.width || 1)
        const zoomY = (imageHeight * 0.9) / (nodesBounds.height || 1)
        const optimalZoom = Math.min(zoomX, zoomY)
        const transform = getViewportForBounds(nodesBounds, imageWidth, imageHeight, optimalZoom, optimalZoom, 20)

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
                a.download = `${projectName}_trace.png`
                a.click()
            })
            .catch((err) => console.error('Failed to download image', err))
    }

    onMount(() => {
        if (onDownloadImageInit) onDownloadImageInit(handleDownloadImage)
    })
</script>

{#if isLoading}
    <LoadingSpinner />
{:else}
    <div class="flex flex-row w-full h-full">
        <!-- Left column: canvas + bottom panel -->
        <div class="flex-1 flex flex-col min-w-0">
        <div class="flex-1 min-h-0 overflow-hidden relative" style="z-index: 1;">
            <SvelteFlow
                bind:nodes={flowStore.nodes}
                edges={styledEdges}
                {nodeTypes}
                {edgeTypes}
                fitView
                fitViewOptions={{ maxZoom: 1, padding: 0.2 }}
                onnodepointerenter={({ node }) => (hoveredNode = (node as any).id)}
                onnodepointerleave={() => (hoveredNode = null)}
                onedgepointerenter={({ edge }) => (hoveredEdge = (edge as any).id)}
                onedgepointerleave={() => (hoveredEdge = null)}
                onnodeclick={({ node }) => flowStore.setSelectedNode((node as any).id)}
                onpaneclick={handlePaneClick}
                panOnScroll={true}
                zoomOnScroll={true}
                minZoom={0.1}
                maxZoom={2}
                connectionMode={ConnectionMode.Loose}
                proOptions={{ hideAttribution: true }}
                nodesDraggable={true}
                nodesConnectable={false}
                elementsSelectable={true}
            >
                <Background />
                <Operator {handleLayout} {handleDownloadImage} />
                <!-- Bridge to register panToNode with panelStore -->
                <Panel position="top-left" style="display:none;">
                    <PanViewportBridge />
                </Panel>
            </SvelteFlow>
        </div>

        <!-- Bottom panel: node properties (read-only in trace view) -->
        <NodeBottomPanel nodeID={flowStore.selectedNode} readOnly={true} />
        </div>

        <!-- Right column: sidebars stacked vertically -->
        {#if sidebarPanels.isOpen('nodes') || sidebarPanels.isOpen('runs')}
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div
                class="flex flex-col border-l border-border relative flex-shrink-0"
                style="width: {sidebarPanels.width}px; transition: {isSidebarDragging ? 'none' : 'width 0ms'};"
            >
                <!-- Resize handle: straddles the border (8 px into canvas, 8 px into sidebar) -->
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <div
                    class="absolute top-0 bottom-0 w-5 cursor-ew-resize z-10 touch-none group flex items-center justify-center"
                    style="left: -10px;"
                    title="Drag to resize"
                    onpointerdown={handleSidebarPointerDown}
                    onpointermove={handleSidebarPointerMove}
                    onpointerup={handleSidebarPointerUp}
                >
                    <div class="w-[4px] h-12 rounded-full bg-foreground/60 opacity-0 group-hover:opacity-100 {isSidebarDragging ? '!opacity-100' : ''} transition-opacity duration-150"></div>
                </div>
                <!-- Wrapper adds left breathing room so content clears the grip handle -->
                <div class="flex flex-col flex-1 min-h-0 pl-2">
                    {#if sidebarPanels.isOpen('nodes')}
                        <NodeOverviewSidebar onclose={() => sidebarPanels.toggle('nodes')} />
                    {/if}
                    {#if sidebarPanels.isOpen('runs')}
                        <RunsOverviewSidebar onclose={() => sidebarPanels.toggle('runs')} />
                    {/if}
                </div>
            </div>
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
