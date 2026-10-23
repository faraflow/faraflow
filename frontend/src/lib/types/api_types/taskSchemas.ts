// Originally from PySpur (https://github.com/PySpur-Dev/pyspur), licensed under Apache-2.0.
// Modified by Alokin LLC, 2026; modifications licensed under FCL-1.0-ALv2.
// SPDX-License-Identifier: Apache-2.0 AND FCL-1.0-ALv2
import type { WorkflowDefinition } from './workflowSchemas'

export type TaskStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELED' | 'PAUSED'

export interface TaskResponse {
    id: string
    run_id: string
    node_id: string
    parent_task_id?: string
    status: TaskStatus
    inputs?: any
    outputs?: any
    error?: string
    start_time?: string
    end_time?: string
    subworkflow?: WorkflowDefinition
    subworkflow_output?: Record<string, any>
}
