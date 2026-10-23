// Copyright 2026 Alokin LLC
// SPDX-License-Identifier: FCL-1.0-ALv2
import type { Node } from '@xyflow/svelte'
import { v4 as uuidv4 } from 'uuid'
import { createNode } from '$lib/utils/nodeFactory'
import type { FlowWorkflowNodeTypesByCategory } from '$lib/types/api_types/nodeTypeSchemas'
import { flowStore } from '$lib/stores/flow.svelte'

export const GROUP_NODE_TYPES = ['ForLoopNode']

export const getId = (prefix = 'node') => `${prefix}_${uuidv4()}`

export const getNodePositionInsideParent = (node: Partial<Node>, groupNode: Node) => {
    const position = node.position ?? { x: 0, y: 0 }
    const nodeWidth = node.measured?.width ?? 0
    const nodeHeight = node.measured?.height ?? 0
    const groupWidth = groupNode.measured?.width ?? 0
    const groupHeight = groupNode.measured?.height ?? 0

    const newPosition = { x: position.x, y: position.y }

    if (position.x < groupNode.position.x) {
        newPosition.x = 0
    } else if (position.x + nodeWidth > groupNode.position.x + groupWidth) {
        newPosition.x = groupWidth - nodeWidth
    } else {
        newPosition.x = position.x - groupNode.position.x
    }

    if (position.y < groupNode.position.y) {
        newPosition.y = 0
    } else if (position.y + nodeHeight > groupNode.position.y + groupHeight) {
        newPosition.y = groupHeight - nodeHeight
    } else {
        newPosition.y = position.y - groupNode.position.y
    }

    return newPosition
}

interface Rect { x: number; y: number; width: number; height: number }

export const getRelativeNodesBounds = (nodes: Node[]): Rect => {
    if (nodes.length === 0) {
        return { x: 0, y: 0, width: 300, height: 150 }
    }

    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
    for (const node of nodes) {
        const x = node.position?.x ?? 0
        const y = node.position?.y ?? 0
        const w = node.measured?.width ?? 0
        const h = node.measured?.height ?? 0
        minX = Math.min(minX, x)
        minY = Math.min(minY, y)
        maxX = Math.max(maxX, x + w)
        maxY = Math.max(maxY, y + h)
    }

    return {
        x: minX === Infinity ? 0 : minX,
        y: minY === Infinity ? 0 : minY,
        width: maxX === -Infinity ? 300 : maxX - minX,
        height: maxY === -Infinity ? 150 : maxY - minY,
    }
}

export function createDynamicGroupNodeWithChildren(
    nodeTypes: FlowWorkflowNodeTypesByCategory,
    nodeType: string,
    id: string,
    position: { x: number; y: number },
    title?: string
) {
    const loopNodeAndConfig = createNode(nodeTypes, nodeType, id, position, null, { width: 1200, height: 600 }, title)
    if (!loopNodeAndConfig) return false

    const inputNodeId = uuidv4()
    const inputNodeTitle = title ? `${title}_input` : `${nodeType}_input`
    const inputNodeAndConfig = createNode(
        nodeTypes,
        'InputNode',
        inputNodeId,
        { x: 0, y: 300 },
        loopNodeAndConfig.node.id,
        null,
        inputNodeTitle
    )

    const outputNodeId = uuidv4()
    const outputNodeTitle = title ? `${title}_output` : `${nodeType}_output`
    const outputNodeAndConfig = createNode(
        nodeTypes,
        'OutputNode',
        outputNodeId,
        { x: 950, y: 300 },
        loopNodeAndConfig.node.id,
        null,
        outputNodeTitle
    )

    if (inputNodeAndConfig) {
        inputNodeAndConfig.config = {
            ...inputNodeAndConfig.config,
            has_fixed_output: true,
            output_schema: {},
        }
    }

    // Single batch call so the whole group is one undo step
    flowStore.addNodesWithConfigs(
        [loopNodeAndConfig, inputNodeAndConfig, outputNodeAndConfig].filter(
            (r): r is NonNullable<typeof r> => r != null
        )
    )
    return true
}
