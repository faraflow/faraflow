// Originally from PySpur (https://github.com/PySpur-Dev/pyspur), licensed under Apache-2.0.
// Modified by Alokin LLC, 2026; modifications licensed under FCL-1.0-ALv2.
// SPDX-License-Identifier: Apache-2.0 AND FCL-1.0-ALv2
import type { TaskResponse } from './taskSchemas'
import type { WorkflowVersionResponse } from './workflowSchemas'

export type RunStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED' | 'PAUSED'

export interface StartRunRequest {
    initial_inputs?: Record<string, Record<string, any>>
    parent_run_id?: string
}

export interface RunResponse {
    id: string
    workflow_id: string
    workflow_version_id: string
    workflow_version: WorkflowVersionResponse
    status: RunStatus
    run_type: string
    initial_inputs?: Record<string, Record<string, any>>
    input_dataset_id?: string
    outputs?: Record<string, any>
    output_file_id?: string
    start_time?: string
    end_time?: string
    tasks: TaskResponse[]
    percentage_complete?: number
    parent_run_id?: string | null
}

// Lightweight heartbeat returned by GET /run/{id}/status/light/ — no tasks.
// Poll this and compare `version` to decide whether to fetch the full run.
export interface RunStatusLight {
    id: string
    status: RunStatus
    version: number
    start_time?: string
    end_time?: string
}

// Lightweight run row returned by the list endpoints — no tasks/outputs.
export interface RunListItem {
    id: string
    workflow_id?: string
    status: RunStatus
    version: number
    run_type: string
    start_time?: string
    end_time?: string
    initial_inputs?: Record<string, Record<string, any>>
    parent_run_id?: string | null
}

export interface PartialRunRequest {
    node_ids?: string[] | null
    initial_inputs?: Record<string, Record<string, any>>
    partial_outputs?: Record<string, Record<string, any>>
    original_run_id?: string | null
    continue_from_node_id?: string | null
}

export interface BatchRunRequest {
    dataset_id: string
    mini_batch_size: number
}
