// Copyright 2026 Alokin LLC
// SPDX-License-Identifier: FCL-1.0-ALv2
import { getConnectedEdges } from '@xyflow/svelte'
import isEqual from 'lodash.isequal'
import { v4 as uuidv4 } from 'uuid'

import type { CreateNodeResult, FlowWorkflowEdge, FlowWorkflowNode, FlowWorkflowNodeTypesByCategory } from '$lib/types/api_types/nodeTypeSchemas'
import { createNode } from '$lib/utils/nodeFactory'
import { flowStore } from '$lib/stores/flow.svelte'

// ─── pure helpers ─────────────────────────────────────────────────────────────

export function getNodeTitle(data: FlowWorkflowNode['data']): string {
    return data?.config?.title || data?.title || data?.type || 'Untitled'
}

export function generateNewNodeTitle(nodes: FlowWorkflowNode[], nodeType: string): string {
    const existingTitles = nodes.map((n) => n.data?.title)
    const sanitizedType = nodeType.replace(/\s+/g, '_')
    let counter = 1
    let newTitle = `${sanitizedType}_${counter}`
    while (existingTitles.includes(newTitle)) {
        counter++
        newTitle = `${sanitizedType}_${counter}`
    }
    return newTitle
}

export function nodeComparator(prevNode: FlowWorkflowNode, nextNode: FlowWorkflowNode): boolean {
    if (!prevNode || !nextNode) return false
    const { position: _pp, measured: _pm, ...prevRest } = prevNode
    const { position: _np, measured: _nm, ...nextRest } = nextNode
    return isEqual(prevRest, nextRest)
}

export function getPredecessorFields(nodeId: string, nodes: FlowWorkflowNode[], edges: FlowWorkflowEdge[]): string[] {
    const incomingEdges = edges.filter((e) => e.target === nodeId)
    const predecessors = incomingEdges
        .map((e) => nodes.find((n) => n.id === e.source))
        .filter((n): n is FlowWorkflowNode => n !== undefined)

    const fields: string[] = []
    predecessors.forEach((node) => {
        const nodeTitle = getNodeTitle(node.data)
        const outputSchema = node.data?.config?.output_schema || node.data?.output_schema || []
        outputSchema.forEach((field: { name: string }) => {
            fields.push(`${nodeTitle}.${field.name}`)
        })
    })
    return fields.sort()
}

/** Adjust ForLoopNode z-index so they render behind child nodes. */
export function adjustGroupNodesZIndex(nodes: FlowWorkflowNode[]): FlowWorkflowNode[] {
    return nodes.map((node) => {
        if (node.type === 'ForLoopNode') {
            return { ...node, style: { ...node.style, zIndex: -1 } }
        }
        return node
    })
}

/** Apply mode (pointer/hand) draggability/selectability to nodes. */
export function applyModeToNodes(nodes: FlowWorkflowNode[], mode: 'pointer' | 'hand'): FlowWorkflowNode[] {
    return nodes.filter(Boolean).map((node) => ({
        ...node,
        draggable: true,
        selectable: mode === 'pointer',
    }))
}

interface StyledEdgesOptions {
    edges: FlowWorkflowEdge[]
    hoveredNode: string | null
    hoveredEdge: string | null
    selectedEdgeId: string | null
    isDark: boolean
    handlePopoverOpen?: (params: { sourceNode: FlowWorkflowNode; targetNode: FlowWorkflowNode; edgeId: string }) => void
    onEdgeLabelEnter?: () => void
    onEdgeLabelLeave?: () => void
    readOnly?: boolean
}

export function getStyledEdges({
    edges,
    hoveredNode,
    hoveredEdge,
    selectedEdgeId,
    isDark,
    handlePopoverOpen,
    onEdgeLabelEnter,
    onEdgeLabelLeave,
    readOnly = false,
}: StyledEdgesOptions): FlowWorkflowEdge[] {
    return edges.map((edge) => {
        const isHovered = edge.id === hoveredEdge || edge.id === selectedEdgeId
        const isEndpointHovered = edge.source === hoveredNode || edge.target === hoveredNode

        let stroke: string
        let strokeWidth: number

        if (readOnly) {
            stroke = isHovered || isEndpointHovered ? (isDark ? '#fff' : '#000') : isDark ? '#888' : '#555'
            strokeWidth = isHovered || isEndpointHovered ? 4 : 2
        } else {
            stroke = isHovered || isEndpointHovered ? (isDark ? '#fff' : '#555') : isDark ? '#666' : '#999'
            strokeWidth = isHovered || isEndpointHovered ? 3 : 1.5
        }

        return {
            ...edge,
            type: 'custom',
            style: { stroke, strokeWidth },
            data: {
                ...edge.data,
                showPlusButton: edge.id === hoveredEdge || edge.id === selectedEdgeId,
                onPopoverOpen: handlePopoverOpen,
                onLabelEnter: onEdgeLabelEnter,
                onLabelLeave: onEdgeLabelLeave,
            },
        }
    })
}

/** Apply run output status to nodes (used in trace/read-only canvas). */
export function applyNodeOutputStatus(
    nodes: FlowWorkflowNode[],
    nodeOutputs?: Record<string, any>
): FlowWorkflowNode[] {
    return nodes.filter(Boolean).map((node) => {
        const title = node.data?.title || node.id
        if (node.data?.taskStatus) return node
        if (!nodeOutputs || !(title in nodeOutputs)) {
            return { ...node, data: { ...node.data, taskStatus: 'PENDING' } }
        }
        const output = nodeOutputs[title]
        if (output.__paused) {
            return { ...node, data: { ...node.data, taskStatus: 'PAUSED', run: output } }
        }
        return { ...node, data: { ...node.data, taskStatus: 'COMPLETED', run: output } }
    })
}

// ─── throttled position update (for canvas performance) ─────────────────────

export function createThrottledPositionChange() {
    let lastUpdate = 0
    const throttleInterval = 32 // ~30fps
    let pendingChanges: any[] = []
    let animationFrame: number | null = null

    return {
        handlePositionChange(changes: any[], onDispatch: (changes: any[]) => void) {
            const now = Date.now()
            pendingChanges = [...pendingChanges, ...changes]
            if (animationFrame !== null) return
            if (now - lastUpdate >= throttleInterval) {
                animationFrame = requestAnimationFrame(() => {
                    const latestPositions = new Map<string, any>()
                    pendingChanges.forEach((c) => {
                        if (c.type === 'position' && c.id) latestPositions.set(c.id, c)
                    })
                    const nonPosition = pendingChanges.filter((c) => c.type !== 'position')
                    const optimized = [...latestPositions.values(), ...nonPosition]
                    if (optimized.length > 0) onDispatch(optimized)
                    pendingChanges = []
                    lastUpdate = now
                    animationFrame = null
                })
            }
        },

        flushChanges(onDispatch: (changes: any[]) => void) {
            if (animationFrame !== null) {
                cancelAnimationFrame(animationFrame)
                animationFrame = null
            }
            if (pendingChanges.length === 0) return
            const latestPositions = new Map<string, any>()
            pendingChanges.forEach((c) => {
                if (c.type === 'position' && c.id) latestPositions.set(c.id, c)
            })
            const nonPosition = pendingChanges.filter((c) => c.type !== 'position')
            const optimized = [...latestPositions.values(), ...nonPosition]
            if (optimized.length > 0) onDispatch(optimized)
            pendingChanges = []
            lastUpdate = Date.now()
        },
    }
}

// ─── store-aware actions ──────────────────────────────────────────────────────
// These functions read/write the flow store directly instead of dispatching Redux actions.

export function createNodeAtCenter(
    nodeType: string,
    getSvelteFlowPosition: (screen: { x: number; y: number }) => { x: number; y: number }
): void {
    const id = uuidv4()
    const nodeTitle = generateNewNodeTitle(flowStore.nodes, nodeType)
    const center = getSvelteFlowPosition({ x: window.innerWidth / 2, y: window.innerHeight / 2 })

    const result = createNode(flowStore.nodeTypes, nodeType, id, center, null, null, nodeTitle)
    if (result) flowStore.addNodeWithConfig(result)
}

export function duplicateNode(nodeId: string): void {
    const nodes = flowStore.nodes
    const edges = flowStore.edges

    const sourceNode = nodes.find((n) => n.id === nodeId)
    if (!sourceNode?.data) return

    const connectedEdges = getConnectedEdges([{ id: nodeId, position: sourceNode.position, data: sourceNode.data }], edges)
    const newNodeId = uuidv4()
    const newTitle = generateNewNodeTitle(nodes, sourceNode.type || 'default')

    const newNode: FlowWorkflowNode = {
        ...sourceNode,
        id: newNodeId,
        position: { x: sourceNode.position.x + 20, y: sourceNode.position.y + 20 },
        data: { ...sourceNode.data, title: newTitle },
        selected: false,
    }

    const sourceConfig = flowStore.nodeConfigs[nodeId]
    if (!sourceConfig) return

    const nodeConfig: CreateNodeResult = {
        node: newNode,
        config: { ...sourceConfig, title: newTitle },
    }

    const childNodes = nodes.filter((n) => n.parentId === nodeId)

    if (childNodes.length > 0) {
        const childEdges = edges.filter((e) =>
            childNodes.some((c) => c.id === e.source || c.id === e.target)
        )
        const idMapping: Record<string, string> = { [nodeId]: newNodeId }

        flowStore.addNodeWithConfig(nodeConfig)

        const newChildEdges: FlowWorkflowEdge[] = []
        childNodes.forEach((child) => {
            const newChildId = uuidv4()
            idMapping[child.id] = newChildId
            const newChildTitle = generateNewNodeTitle(nodes, child.type || 'default')
            const newChild: FlowWorkflowNode = {
                ...child,
                id: newChildId,
                parentId: newNodeId,
                data: { ...child.data, title: newChildTitle },
                selected: false,
            }
            const childConfig = flowStore.nodeConfigs[child.id]
            if (childConfig) {
                flowStore.addNodeWithConfig({ node: newChild, config: { ...childConfig, title: newChildTitle } })
            }
        })

        childEdges.forEach((e) => {
            const newSrc = idMapping[e.source]
            const newTgt = idMapping[e.target]
            if (newSrc && newTgt) {
                newChildEdges.push({ ...e, id: uuidv4(), source: newSrc, target: newTgt })
            }
        })

        flowStore.setEdges([...edges, ...newChildEdges])
    } else {
        const newEdges = connectedEdges.map((e) => ({
            ...e,
            id: uuidv4(),
            source: e.source === nodeId ? newNodeId : e.source,
            target: e.target === nodeId ? newNodeId : e.target,
        }))
        flowStore.addNodeWithConfig(nodeConfig)
        flowStore.setEdges([...edges, ...newEdges])
    }
}

export function insertNodeBetweenNodes(
    nodeType: string,
    sourceNode: FlowWorkflowNode,
    targetNode: FlowWorkflowNode,
    edgeId: string,
    onComplete?: () => void
): void {
    if (!sourceNode?.position || !targetNode?.position) return

    const id = uuidv4()
    const nodeTitle = generateNewNodeTitle(flowStore.nodes, nodeType)
    const newPosition = {
        x: (sourceNode.position.x + targetNode.position.x) / 2,
        y: (sourceNode.position.y + targetNode.position.y) / 2,
    }

    const result = createNode(flowStore.nodeTypes, nodeType, id, newPosition, null, null, nodeTitle)
    if (!result) return

    flowStore.deleteEdge(edgeId)
    flowStore.addNodeWithConfig(result)
    flowStore.connect({ source: sourceNode.id, target: id, sourceHandle: sourceNode.id, targetHandle: sourceNode.id })
    flowStore.connect({ source: id, target: targetNode.id, sourceHandle: id, targetHandle: id })

    onComplete?.()
}
