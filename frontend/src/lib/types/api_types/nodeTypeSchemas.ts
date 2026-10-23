// Originally from PySpur (https://github.com/PySpur-Dev/pyspur), licensed under Apache-2.0.
// Modified by Alokin LLC, 2026; modifications licensed under FCL-1.0-ALv2.
// SPDX-License-Identifier: Apache-2.0 AND FCL-1.0-ALv2
import type { CoordinateExtent } from '@xyflow/svelte'

import type { RouteConditionGroup } from '$lib/types/api_types/routerSchemas'
import type { WorkflowNodeCoordinates } from '$lib/types/api_types/workflowSchemas'

import type { ModelConstraints } from './modelMetadataSchemas'

export interface NodeTypeSchema {
    node_type_name: string
    class_name: string
    module: string
}

export interface FlowWorkflowNodeType {
    name: string
    input: Record<string, any>
    output: Record<string, any>
    config: Record<string, any>
    visual_tag: {
        acronym: string
        color: string
    }
    has_fixed_output?: boolean
    logo?: string
    category?: string
    model_constraints?: Record<string, ModelConstraints>
}

export interface MinimumNodeConfigSchema {
    title: string
    type: string
    properties: Record<string, any>
    required?: string[]
}

export interface FlowWorkflowEdge {
    id: string
    key: string
    source: string
    target: string
    selected?: boolean
    sourceHandle: string
    targetHandle: string
    [key: string]: any
}

export interface FlowWorkflowNode {
    id: string
    type: string
    position: WorkflowNodeCoordinates
    parentId?: string
    extent?: 'parent' | CoordinateExtent
    data: {
        title: string
        acronym: string
        color: string
        run?: Record<string, any>
        error?: string
        taskStatus?: string
        [key: string]: any
    }
    measured?: {
        width: number
        height: number
    }
    [key: string]: any
}

export interface FlowWorkflowNodeConfig {
    title?: string
    type?: string
    input_schema?: Record<string, any>
    output_schema?: Record<string, any>
    output_json_schema?: string
    system_message?: string
    user_message?: string
    few_shot_examples?:
        | Array<{
              input: string
              output: string
          }>
        | Record<string, any>[]
    llm_info?: {
        model?: string
        api_base?: string
        [key: string]: any
    }
    route_map?: Record<string, RouteConditionGroup>
    preferences?: string[]
    [key: string]: any
}

export interface NodeTypes {
    [key: string]: any
}

export interface NodeTypesConfig {
    [category: string]: Array<FlowWorkflowNodeType>
}

export interface CreateNodeResult {
    node: FlowWorkflowNode
    config: FlowWorkflowNodeConfig
}

export interface Position {
    x: number
    y: number
}

export interface NodeData {
    title?: string
    acronym?: string
    color?: string
    logo?: string
    category?: string
}

export interface BaseNode {
    id: string
    position: Position
    type: string
    data?: NodeData
}

export interface FlowWorkflowNodeTypesByCategory {
    [category: string]: FlowWorkflowNodeType[]
}
