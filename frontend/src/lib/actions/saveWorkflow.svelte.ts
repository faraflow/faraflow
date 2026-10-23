// Copyright 2026 Alokin LLC
// SPDX-License-Identifier: FCL-1.0-ALv2
import { flowStore } from '$lib/stores/flow.svelte'
import { updateWorkflow } from '$lib/utils/api'
import type { WorkflowCreateRequest, WorkflowNode } from '$lib/types/api_types/workflowSchemas'
import type { FlowWorkflowEdge } from '$lib/types/api_types/nodeTypeSchemas'

let saveTimeout: ReturnType<typeof setTimeout> | null = null

/**
 * Debounced save — waits 1 s after the last call before persisting.
 */
export function saveWorkflow(): void {
    if (saveTimeout !== null) clearTimeout(saveTimeout)
    saveTimeout = setTimeout(doSave, 1000)
}

/**
 * Immediate (non-debounced) save. Returns a promise so callers can await it.
 */
export async function saveWorkflowNow(): Promise<void> {
    if (saveTimeout !== null) {
        clearTimeout(saveTimeout)
        saveTimeout = null
    }
    await doSave()
}

async function doSave(): Promise<void> {
    const {
        nodes,
        edges,
        nodeConfigs,
        workflowID,
        projectName,
        testInputs,
        spurType,
    } = flowStore

    if (!workflowID) return

    try {
        const updatedNodes = nodes
            .filter((n): n is NonNullable<typeof n> => n !== null && n !== undefined)
            .map((node) => {
                const config = nodeConfigs[node.id] ?? {}
                const title = config.title ?? node.data?.title

                if (node.type === 'RouterNode') {
                    return {
                        ...node,
                        config: { ...config, route_map: config.route_map ?? {} },
                        title,
                        parent_id: node.parentId ?? null,
                        dimensions: node.measured,
                    }
                }

                return {
                    ...node,
                    config,
                    title,
                    parent_id: node.parentId ?? null,
                    dimensions: node.type === 'ForLoopNode' ? node.measured : undefined,
                }
            })

        const updatedWorkflow: WorkflowCreateRequest = {
            name: projectName,
            description: '',
            definition: {
                nodes: updatedNodes.map(
                    (node) =>
                        ({
                            id: node.id,
                            title: node.title,
                            node_type: node.type,
                            config: node.config,
                            coordinates: node.position,
                            parent_id: node.parent_id ?? null,
                            dimensions: node.dimensions,
                        }) as WorkflowNode
                ),
                links: (edges as FlowWorkflowEdge[]).map((edge) => {
                    const sourceNode = updatedNodes.find((n) => n?.id === edge.source)
                    const targetNode = updatedNodes.find((n) => n?.id === edge.target)

                    if (sourceNode?.type === 'RouterNode') {
                        return {
                            source_id: sourceNode?.id ?? '',
                            target_id: targetNode?.id ?? '',
                            source_handle: edge.sourceHandle,
                            target_handle: edge.targetHandle,
                        }
                    }
                    return {
                        source_id: sourceNode?.id ?? '',
                        target_id: targetNode?.id ?? '',
                    }
                }),
                test_inputs: testInputs,
                spur_type: spurType,
            },
        }

        await updateWorkflow(workflowID, updatedWorkflow)
    } catch (err) {
        console.error('Error saving workflow:', err)
    }
}
