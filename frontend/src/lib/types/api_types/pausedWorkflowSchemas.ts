// Originally from PySpur (https://github.com/PySpur-Dev/pyspur), licensed under Apache-2.0.
// Modified by Alokin LLC, 2026; modifications licensed under FCL-1.0-ALv2.
// SPDX-License-Identifier: Apache-2.0 AND FCL-1.0-ALv2
import type { RunResponse } from './runSchemas'
import type { WorkflowDefinition, WorkflowResponse } from './workflowSchemas'

export interface PauseHistoryResponse {
    id: string
    run_id: string
    node_id: string
    pause_message: string | null
    pause_time: string
    resume_time: string | null
    resume_user_id: string | null
    resume_action: 'APPROVE' | 'DECLINE' | 'OVERRIDE' | null
    input_data: Record<string, any> | null
    comments: string | null
}

export interface PausedWorkflowResponse {
    run: RunResponse
    current_pause: PauseHistoryResponse
    workflow: WorkflowDefinition | WorkflowResponse
}

export interface ResumeActionRequest {
    action: 'APPROVE' | 'DECLINE' | 'OVERRIDE'
    inputs?: Record<string, any>
    comments?: string
    user_id: string
}
