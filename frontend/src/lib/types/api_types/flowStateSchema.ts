// Originally from PySpur (https://github.com/PySpur-Dev/pyspur), licensed under Apache-2.0.
// Modified by Alokin LLC, 2026; modifications licensed under FCL-1.0-ALv2.
// SPDX-License-Identifier: Apache-2.0 AND FCL-1.0-ALv2
import type {
    FlowWorkflowEdge,
    FlowWorkflowNode,
    FlowWorkflowNodeConfig,
    NodeTypesConfig,
} from '$lib/types/api_types/nodeTypeSchemas'
import type { SpurType, TestInput } from '$lib/types/api_types/workflowSchemas'

export interface FlowState {
    nodeTypes: NodeTypesConfig
    nodes: FlowWorkflowNode[]
    edges: FlowWorkflowEdge[]
    nodeConfigs: Record<string, FlowWorkflowNodeConfig>
    workflowID: string | null
    selectedNode: string | null
    selectedEdgeId: string | null
    sidebarWidth: number
    projectName: string
    workflowInputVariables: Record<string, any>
    testInputs: TestInput[]
    inputNodeValues: Record<string, any>
    selectedTestInputId: string | null
    history: {
        past: Array<{ nodes: FlowWorkflowNode[]; edges: FlowWorkflowEdge[] }>
        future: Array<{ nodes: FlowWorkflowNode[]; edges: FlowWorkflowEdge[] }>
    }
    isRunModalOpen: boolean
    spurType: SpurType
}
