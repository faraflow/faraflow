// Copyright 2026 Alokin LLC
// SPDX-License-Identifier: FCL-1.0-ALv2
import type {
    MessageGenerationRequest,
    MessageGenerationResponse,
    SchemaGenerationResponse,
} from '$lib/types/api_types/aiGenerationSchemas'
import type { DatasetResponse } from '$lib/types/api_types/datasetSchemas'
import type { EvalRunRequest, EvalRunResponse } from '$lib/types/api_types/evalSchemas'
import type { NodeTypeSchema } from '$lib/types/api_types/nodeTypeSchemas'
import type { OutputFileResponse } from '$lib/types/api_types/outputFileSchemas'
import type {
    PauseHistoryResponse,
    PausedWorkflowResponse,
    ResumeActionRequest,
} from '$lib/types/api_types/pausedWorkflowSchemas'
import type {
    ChunkPreviewResponseSchema,
    ChunkTemplateSchema,
    DocumentCollectionCreateRequestSchema,
    DocumentCollectionResponseSchema,
    DocumentWithChunksSchema,
    ProcessingProgressSchema,
    VectorIndexCreateRequestSchema,
    VectorIndexResponseSchema,
} from '$lib/types/api_types/ragSchemas'
import type { RunListItem, RunResponse, RunStatus, RunStatusLight } from '$lib/types/api_types/runSchemas'
import type { SessionCreate, SessionListResponse, SessionResponse } from '$lib/types/api_types/sessionSchemas'
import type { UserCreate, UserListResponse, UserResponse, UserUpdate } from '$lib/types/api_types/userSchemas'
import type {
    SpurType,
    WorkflowCreateRequest,
    WorkflowDefinition,
    WorkflowResponse,
    WorkflowVersionResponse,
} from '$lib/types/api_types/workflowSchemas'

import JSPydanticModel from './JSPydanticModel'
import { apiKey } from '$lib/stores/apiKey.svelte'

// ---------------------------------------------------------------------------
// Base fetch wrapper
// ---------------------------------------------------------------------------

const API_BASE_URL =
    typeof window !== 'undefined'
        ? `${window.location.protocol}//${window.location.host}/api`
        : 'http://localhost:6080/api'

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(options.headers as Record<string, string>),
    }
    // Don't set Content-Type for FormData — let the browser set multipart boundary
    if (options.body instanceof FormData) {
        delete headers['Content-Type']
    }
    if (apiKey.current) {
        headers['Authorization'] = `Bearer ${apiKey.current}`
    }
    const res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers })
    if (!res.ok) {
        const detail = await res.text().catch(() => res.statusText)
        const err: any = new Error(`API error ${res.status}: ${detail}`)
        err.response = { status: res.status, data: { detail } }
        throw err
    }
    // 204 No Content
    if (res.status === 204) return undefined as unknown as T
    return res.json()
}

const api = {
    get: <T>(path: string) => request<T>(path),
    post: <T>(path: string, body?: unknown) =>
        request<T>(path, {
            method: 'POST',
            body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
        }),
    put: <T>(path: string, body?: unknown) =>
        request<T>(path, {
            method: 'PUT',
            body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
        }),
    patch: <T>(path: string, body?: unknown) =>
        request<T>(path, {
            method: 'PATCH',
            body: body !== undefined ? JSON.stringify(body) : undefined,
        }),
    delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}

// ---------------------------------------------------------------------------
// API types
// ---------------------------------------------------------------------------

export interface ApiKey {
    name: string
    value: string
}

// ---------------------------------------------------------------------------
// Node types
// ---------------------------------------------------------------------------

export const getNodeTypes = async (): Promise<{
    schema: Record<string, NodeTypeSchema>
    metadata: Record<string, any>
}> => {
    const data = await api.get<any>('/node/supported_types/')
    const model = new JSPydanticModel(data)
    return {
        schema: model.createObjectFromSchema(),
        metadata: model.getAllMetadata(),
    }
}

// ---------------------------------------------------------------------------
// Workflows
// ---------------------------------------------------------------------------

export const getWorkflows = async (page = 1, pageSize = 10): Promise<WorkflowResponse[]> =>
    api.get(`/wf/?page=${page}&page_size=${pageSize}`)

export const createWorkflow = async (workflowData: WorkflowCreateRequest): Promise<WorkflowResponse> =>
    api.post('/wf/', workflowData)

export const getWorkflow = async (workflowID: string): Promise<WorkflowResponse> =>
    api.get(`/wf/${workflowID}/`)

export const updateWorkflow = async (
    workflowId: string,
    workflowData: WorkflowCreateRequest
): Promise<WorkflowResponse> => api.put(`/wf/${workflowId}/`, workflowData)

export const resetWorkflow = async (workflowId: string): Promise<any> =>
    api.put(`/wf/${workflowId}/reset/`)

export const deleteWorkflow = async (workflowId: string): Promise<void> =>
    api.delete(`/wf/${workflowId}/`)

export const duplicateWorkflow = async (workflowId: string): Promise<WorkflowResponse> =>
    api.post(`/wf/${workflowId}/duplicate/`)

export const getWorkflowVersions = async (
    workflowId: string,
    page = 1,
    pageSize = 10
): Promise<WorkflowVersionResponse[]> =>
    api.get(`/wf/${workflowId}/versions/?page=${page}&page_size=${pageSize}`)

export const getWorkflowOutputVariables = async (workflowId: string): Promise<any> =>
    api.get(`/wf/${workflowId}/output_variables/`)

// ---------------------------------------------------------------------------
// Runs
// ---------------------------------------------------------------------------

export const startRun = async (
    workflowID: string,
    initialInputs: Record<string, any> = {},
    parentRunId: string | null = null,
    runType = 'interactive'
): Promise<any> =>
    api.post(`/wf/${workflowID}/start_run/?run_type=${runType}`, {
        initial_inputs: initialInputs,
        parent_run_id: parentRunId,
    })

export const startBatchRun = async (
    workflowID: string,
    datasetID: string,
    miniBatchSize = 10
): Promise<any> =>
    api.post(`/wf/${workflowID}/start_batch_run/`, {
        dataset_id: datasetID,
        mini_batch_size: miniBatchSize,
    })

export const getRunStatus = async (runID: string): Promise<RunResponse> =>
    api.get(`/run/${runID}/status/`)

// Lightweight heartbeat — poll this and compare `version` to decide whether to
// fetch the full run via getRunStatus().
export const getRunStatusLight = async (runID: string): Promise<RunStatusLight> =>
    api.get(`/run/${runID}/status/light/`)

export const getRun = async (runID: string): Promise<any> =>
    api.get(`/run/${runID}/`)

export const getWorkflowRuns = async (
    workflowId: string,
    page = 1,
    pageSize = 10,
    startDate?: Date,
    endDate?: Date,
    status?: RunStatus,
    inputQuery?: string
): Promise<RunListItem[]> => {
    let url = `/wf/${workflowId}/runs/?page=${page}&page_size=${pageSize}`
    if (startDate) url += `&start_date=${startDate.toISOString()}`
    if (endDate) url += `&end_date=${endDate.toISOString()}`
    if (status) url += `&status=${status}`
    if (inputQuery) url += `&input_query=${encodeURIComponent(inputQuery)}`
    return api.get(url)
}

export const getAllRuns = async (
    page = 1,
    pageSize = 10,
    parentOnly = true,
    runType?: string,
    status?: RunStatus,
    inputQuery?: string
): Promise<RunListItem[]> => {
    let url = `/run/?page=${page}&page_size=${pageSize}&parent_only=${parentOnly}`
    if (runType) url += `&run_type=${runType}`
    if (status) url += `&status=${status}`
    if (inputQuery) url += `&input_query=${encodeURIComponent(inputQuery)}`
    return api.get(url)
}

export const runPartialWorkflow = async (
    workflowId: string,
    initialInputs: Record<string, any>,
    partialOutputs: Record<string, any> | null,
    originalRunId?: string | null,
    nodeIds?: string[] | null,
    continueFromNodeId?: string | null
): Promise<any> =>
    api.post(`/wf/${workflowId}/run_partial/`, {
        node_ids: nodeIds ?? null,
        initial_inputs: initialInputs,
        partial_outputs: partialOutputs ?? null,
        original_run_id: originalRunId ?? null,
        continue_from_node_id: continueFromNodeId ?? null,
    })

// ---------------------------------------------------------------------------
// Paused workflows
// ---------------------------------------------------------------------------

export const listPausedWorkflows = async (page = 1, pageSize = 10): Promise<PausedWorkflowResponse[]> =>
    api.get(`/wf/paused_workflows/?page=${page}&page_size=${pageSize}`)

export const getPauseHistory = async (runId: string): Promise<PauseHistoryResponse[]> =>
    api.get(`/wf/pause_history/${runId}/`)

export const takePauseAction = async (runId: string, actionRequest: ResumeActionRequest): Promise<RunResponse> =>
    api.post(`/wf/process_pause_action/${runId}/`, actionRequest)

export const cancelWorkflow = async (runId: string): Promise<RunResponse> =>
    api.post(`/wf/cancel_workflow/${runId}/`)

// ---------------------------------------------------------------------------
// Output files
// ---------------------------------------------------------------------------

export const downloadOutputFile = async (outputFileID: string): Promise<void> => {
    const fileInfo = await api.get<OutputFileResponse>(`/of/${outputFileID}/`)
    const res = await fetch(`${API_BASE_URL}/of/${outputFileID}/download/`, {
        headers: apiKey.current ? { Authorization: `Bearer ${apiKey.current}` } : {},
    })
    if (!res.ok) throw new Error(`Download failed: ${res.status}`)
    const blob = await res.blob()
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', fileInfo.file_name)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
}

// ---------------------------------------------------------------------------
// Templates
// ---------------------------------------------------------------------------

export const getTemplates = async (): Promise<any> => api.get('/templates/')

export const instantiateTemplate = async (template: any): Promise<any> =>
    api.post('/templates/instantiate/', template)

// ---------------------------------------------------------------------------
// API keys / env management
// ---------------------------------------------------------------------------

export const listApiKeys = async (): Promise<string[]> => api.get('/env-mgmt/')

export const getApiKey = async (name: string): Promise<ApiKey> => api.get(`/env-mgmt/${name}`)

export const getProviders = async (): Promise<any[]> => api.get('/env-mgmt/providers')

export interface ApiKeyInfo {
    name: string
    /** Masked value. */
    value: string
    configured: boolean
}

/** Every key's masked value and whether it is set, in one call. */
export const listApiKeyInfo = async (): Promise<ApiKeyInfo[]> => api.get('/env-mgmt/keys')

export const setApiKey = async (name: string, value: string): Promise<any> =>
    api.post('/env-mgmt/', { name, value })

export const deleteApiKey = async (name: string): Promise<any> => api.delete(`/env-mgmt/${name}`)


export const getEmbeddingModels = async (): Promise<Record<string, EmbeddingModelConfig>> =>
    api.get('/env-mgmt/embedding-models/')

export const getVectorStores = async (): Promise<Record<string, VectorStoreConfig>> =>
    api.get('/env-mgmt/vector-stores/')

// ---------------------------------------------------------------------------
// Datasets
// ---------------------------------------------------------------------------

export const uploadDataset = async (name: string, description: string, file: File): Promise<DatasetResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    return request(`/ds/?name=${encodeURIComponent(name)}&description=${encodeURIComponent(description)}`, {
        method: 'POST',
        body: formData,
    })
}

export const listDatasets = async (): Promise<DatasetResponse[]> => api.get('/ds/')

export const getDataset = async (datasetId: string): Promise<DatasetResponse> => api.get(`/ds/${datasetId}/`)

export const deleteDataset = async (datasetId: string): Promise<{ message: string }> =>
    api.delete(`/ds/${datasetId}/`)

export const listDatasetRuns = async (datasetId: string): Promise<RunResponse[]> =>
    api.get(`/ds/${datasetId}/list_runs/`)

// ---------------------------------------------------------------------------
// Evals
// ---------------------------------------------------------------------------

export const getEvals = async (): Promise<any> => api.get('/evals/')

export const startEvalRun = async (
    workflowId: string,
    evalName: string,
    outputVariable: string,
    numSamples = 10
): Promise<EvalRunResponse> => {
    const request: EvalRunRequest = {
        workflow_id: workflowId,
        eval_name: evalName,
        output_variable: outputVariable,
        num_samples: numSamples,
    }
    return api.post('/evals/launch/', request)
}

export const getEvalRunStatus = async (evalRunId: string): Promise<EvalRunResponse> =>
    api.get(`/evals/runs/${evalRunId}`)

export const listEvalRuns = async (): Promise<EvalRunResponse[]> => api.get('/evals/runs/')

// ---------------------------------------------------------------------------
// AI generation
// ---------------------------------------------------------------------------

export const generateSchema = async (
    description: string,
    existingSchema?: string
): Promise<SchemaGenerationResponse> =>
    api.post('/ai/generate_schema/', { description, existing_schema: existingSchema })

export const generateMessage = async (req: MessageGenerationRequest): Promise<MessageGenerationResponse> =>
    api.post('/ai/generate_message/', req)

// ---------------------------------------------------------------------------
// Google
// ---------------------------------------------------------------------------

export interface StoreGoogleAccessTokenResponse {
    message: string
}

export interface GoogleAccessTokenValidationResponse {
    is_valid: boolean
}

export const storeGoogleAccessToken = async (accessToken: string, expiresIn: string): Promise<any> =>
    api.post('/google/store_token/', { access_token: accessToken, expires_in: expiresIn })

export const validateGoogleAccessToken = async (): Promise<GoogleAccessTokenValidationResponse> =>
    api.get('/google/validate_token/')

// ---------------------------------------------------------------------------
// OpenAPI specs
// ---------------------------------------------------------------------------

export interface OpenAPIEndpoint {
    path: string
    method: string
    summary?: string
    operationId?: string
    description?: string
    input_schema?: any
    output_schema?: any
}

export interface OpenAPISpec {
    id: string
    name: string
    description: string
    version: string
    endpoints: OpenAPIEndpoint[]
    raw_spec: any
}

export const createOpenAPISpec = async (fullSpec: any): Promise<OpenAPISpec> =>
    api.post('/openapi/specs/', { spec: fullSpec })

export const listOpenAPISpecs = async (): Promise<OpenAPISpec[]> => api.get('/openapi/specs/')

export const getOpenAPISpec = async (specId: string): Promise<OpenAPISpec> =>
    api.get(`/openapi/specs/${specId}`)

export const deleteOpenAPISpec = async (specId: string): Promise<void> =>
    api.delete(`/openapi/specs/${specId}`)

// ---------------------------------------------------------------------------
// RAG - Knowledge bases
// ---------------------------------------------------------------------------

export interface KnowledgeBaseCreationJob {
    id: string
    status: 'pending' | 'processing' | 'completed' | 'failed'
    progress: number
    current_step: string
    total_files: number
    processed_files: number
    total_chunks: number
    processed_chunks: number
    error_message?: string
    created_at: string
    updated_at: string
}

export interface KnowledgeBaseCreateRequest {
    name: string
    description?: string
    data_source: { type: 'upload' | 'sync'; tool?: string; files?: File[] }
    text_processing: { chunk_size: number; overlap: number }
    embedding: {
        model: string
        vector_db: string
        search_strategy: string
        semantic_weight?: number
        keyword_weight?: number
        top_k?: number
        score_threshold?: number
    }
}

export interface KnowledgeBaseResponse {
    id: string
    name: string
    description: string
    status: 'processing' | 'ready' | 'failed'
    created_at: string
    updated_at: string
    document_count: number
    chunk_count: number
    error_message?: string
    has_embeddings: boolean
    config?: {
        vector_db?: string
        embedding_model?: string
        chunk_token_size?: number
        embeddings_batch_size?: number
    }
}

export interface EmbeddingModelConfig {
    id: string
    provider: string
    name: string
    dimensions: number
    max_input_length: number
    supported_encoding_formats?: string[]
    required_env_vars: string[]
}

export interface VectorStoreConfig {
    id: string
    name: string
    description: string
    requires_api_key: boolean
    api_key_env_var?: string
    required_env_vars: string[]
}

export const createKnowledgeBase = async (data: KnowledgeBaseCreateRequest): Promise<KnowledgeBaseResponse> => {
    const formData = new FormData()
    formData.append(
        'metadata',
        JSON.stringify({
            name: data.name,
            description: data.description,
            text_processing: data.text_processing,
            embedding: data.embedding,
        })
    )
    if (data.data_source?.type === 'upload' && data.data_source.files) {
        data.data_source.files.forEach((file) => formData.append('files', file))
    }
    if (data.data_source?.type === 'sync' && data.data_source.tool) {
        formData.append('sync_tool', data.data_source.tool)
    }
    return request('/rag/', { method: 'POST', body: formData })
}

export const listKnowledgeBases = async (): Promise<KnowledgeBaseResponse[]> => api.get('/rag/')

export const getKnowledgeBase = async (id: string): Promise<KnowledgeBaseResponse> => api.get(`/rag/${id}/`)

export const deleteKnowledgeBase = async (id: string): Promise<void> => api.delete(`/rag/${id}/`)

export const updateKnowledgeBase = async (
    id: string,
    data: Partial<KnowledgeBaseCreateRequest>
): Promise<KnowledgeBaseResponse> => api.put(`/rag/${id}/`, data)

export const syncKnowledgeBase = async (id: string): Promise<void> => api.post(`/rag/${id}/sync/`)

export const getKnowledgeBaseJobStatus = async (id: string): Promise<KnowledgeBaseCreationJob> =>
    api.get(`/rag/${id}/job/`)

export const addDocumentsToKnowledgeBase = async (id: string, files: File[]): Promise<any> => {
    const formData = new FormData()
    files.forEach((file) => formData.append('files', file))
    return request(`/rag/${id}/documents/`, { method: 'POST', body: formData })
}

// ---------------------------------------------------------------------------
// RAG - Document collections
// ---------------------------------------------------------------------------

export const createDocumentCollection = async (
    data: DocumentCollectionCreateRequestSchema,
    files?: File[]
): Promise<DocumentCollectionResponseSchema> => {
    const formData = new FormData()
    formData.append('metadata', JSON.stringify(data))
    if (files) files.forEach((file) => formData.append('files', file))
    return request('/rag/collections/', { method: 'POST', body: formData })
}

export const listDocumentCollections = async (): Promise<DocumentCollectionResponseSchema[]> =>
    api.get('/rag/collections/')

export const getDocumentCollection = async (id: string): Promise<DocumentCollectionResponseSchema> =>
    api.get(`/rag/collections/${id}/`)

export const deleteDocumentCollection = async (id: string): Promise<void> =>
    api.delete(`/rag/collections/${id}/`)

export const addDocumentsToCollection = async (id: string, files: File[]): Promise<any> => {
    const formData = new FormData()
    files.forEach((file) => formData.append('files', file))
    return request(`/rag/collections/${id}/documents/`, { method: 'POST', body: formData })
}

export const getCollectionDocuments = async (id: string): Promise<DocumentWithChunksSchema[]> =>
    api.get(`/rag/collections/${id}/documents/`)

export const previewChunk = async (
    file: File,
    config: {
        chunk_token_size: number
        min_chunk_size_chars: number
        min_chunk_length_to_embed: number
        template: ChunkTemplateSchema
    }
): Promise<ChunkPreviewResponseSchema> => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append(
        'chunking_config',
        JSON.stringify({
            chunk_token_size: config.chunk_token_size,
            min_chunk_size_chars: config.min_chunk_size_chars,
            min_chunk_length_to_embed: config.min_chunk_length_to_embed,
            template: config.template,
        })
    )
    return request('/rag/collections/preview_chunk/', { method: 'POST', body: formData })
}

// ---------------------------------------------------------------------------
// RAG - Vector indices
// ---------------------------------------------------------------------------

export const createVectorIndex = async (data: VectorIndexCreateRequestSchema): Promise<VectorIndexResponseSchema> =>
    api.post('/rag/indices/', data)

export const listVectorIndices = async (): Promise<VectorIndexResponseSchema[]> => api.get('/rag/indices/')

export const getVectorIndex = async (id: string): Promise<VectorIndexResponseSchema> =>
    api.get(`/rag/indices/${id}/`)

export const deleteVectorIndex = async (id: string): Promise<void> => api.delete(`/rag/indices/${id}/`)

export const getIndexProgress = async (indexId: string): Promise<ProcessingProgressSchema | null> => {
    try {
        return await api.get<ProcessingProgressSchema>(`/rag/indices/${indexId}/progress/`)
    } catch (err: any) {
        if (err?.response?.status === 404) return null
        throw err
    }
}

// ---------------------------------------------------------------------------
// Test files
// ---------------------------------------------------------------------------

export const uploadTestFiles = async (
    workflowId: string,
    nodeId: string,
    files: File[]
): Promise<Record<string, string[]>> => {
    const formData = new FormData()
    formData.append('workflow_id', workflowId)
    formData.append('node_id', nodeId)
    files.forEach((file) => formData.append('files', file))
    return request('/wf/upload_test_files/', { method: 'POST', body: formData })
}

// ---------------------------------------------------------------------------
// Users
// ---------------------------------------------------------------------------

export const createUser = async (userData: UserCreate): Promise<UserResponse> => api.post('/user/', userData)

export const listUsers = async (skip = 0, limit = 10): Promise<UserListResponse> =>
    api.get(`/user/?skip=${skip}&limit=${limit}`)

export const getUser = async (userId: string): Promise<UserResponse> => api.get(`/user/${userId}/`)

export const updateUser = async (userId: string, userData: UserUpdate): Promise<UserResponse> =>
    api.patch(`/user/${userId}/`, userData)

export const deleteUser = async (userId: string): Promise<void> => api.delete(`/user/${userId}/`)

// ---------------------------------------------------------------------------
// Sessions
// ---------------------------------------------------------------------------

export const createSession = async (sessionData: SessionCreate): Promise<SessionResponse> =>
    api.post('/session/', sessionData)

export const listSessions = async (
    skip = 0,
    limit = 10,
    userId?: string,
    workflowId?: string
): Promise<SessionListResponse> => {
    let url = `/session/?skip=${skip}&limit=${limit}`
    if (userId) url += `&user_id=${userId}`
    if (workflowId) url += `&workflow_id=${workflowId}`
    return api.get(url)
}

export const getSession = async (sessionId: string): Promise<SessionResponse> =>
    api.get(`/session/${sessionId}/`)

export const deleteSession = async (sessionId: string): Promise<void> =>
    api.delete(`/session/${sessionId}/`)

export const createTestSession = async (workflowId: string): Promise<SessionResponse> =>
    api.post(`/session/test/?workflow_id=${workflowId}`)

// ---------------------------------------------------------------------------
// Slack
// ---------------------------------------------------------------------------

export interface SlackAgent {
    id: number
    name: string
    slack_team_id: string
    slack_team_name: string
    workflow_id?: string
    spur_type: SpurType
    is_active: boolean
    trigger_enabled: boolean
    trigger_on_mention: boolean
    trigger_on_direct_message: boolean
    trigger_on_channel_message: boolean
    trigger_keywords?: string[]
    created_at: string
    has_bot_token: boolean
    has_user_token: boolean
    has_app_token?: boolean
    last_token_update?: string
    socket_mode_enabled?: boolean
}

export interface SlackOAuthResponse {
    success: boolean
    message: string
    team_name?: string
}

export interface SlackMessageResponse {
    success: boolean
    message: string
    ts?: string
}

export interface SlackSocketModeResponse {
    agent_id: number
    socket_mode_active: boolean
    message: string
}

export interface AlertFunction {
    (message: string, color: 'success' | 'danger' | 'warning' | 'default'): void
}

export const getSlackAgents = async (forceRefresh = false): Promise<SlackAgent[]> => {
    const maxRetries = 2
    let lastError: any = null
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            const cacheBuster = forceRefresh || attempt > 1 ? `?_=${Date.now()}` : ''
            return await api.get(`/slack/agents${cacheBuster}`)
        } catch (error) {
            lastError = error
            if (attempt < maxRetries) await new Promise((r) => setTimeout(r, 300 * attempt))
        }
    }
    console.warn('Returning empty array after failed Slack agents fetch attempts')
    return []
}

export const associateWorkflow = async (agentId: number, workflowId: string | null): Promise<SlackAgent> => {
    const maxRetries = 3
    let lastError: any = null
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            const res = await api.put<SlackAgent>(`/slack/agents/${agentId}/workflow`, {
                workflow_id: workflowId,
            })
            const expected = workflowId ? String(workflowId) : ''
            const received = res.workflow_id ? String(res.workflow_id) : ''
            if (expected && received && expected !== received) {
                if (attempt === maxRetries) throw new Error('Server returned a different workflow ID than requested')
                await new Promise((r) => setTimeout(r, 500))
                continue
            }
            return res
        } catch (error) {
            lastError = error
            if (attempt < maxRetries) await new Promise((r) => setTimeout(r, 500))
        }
    }
    throw lastError || new Error('Failed to associate workflow after multiple attempts')
}

export const updateTriggerConfig = async (
    agentId: number,
    config: {
        trigger_on_mention: boolean
        trigger_on_direct_message: boolean
        trigger_on_channel_message: boolean
        trigger_keywords: string[]
        trigger_enabled: boolean
    }
): Promise<SlackAgent> => api.put(`/slack/agents/${agentId}/trigger-config`, config)

export const sendTestMessage = async (
    channel: string,
    text: string,
    agentId?: number
): Promise<SlackMessageResponse> => {
    let url = `/slack/test-message?channel=${encodeURIComponent(channel)}`
    if (agentId) url += `&agent_id=${agentId}`
    return api.post(url, { text })
}

export const handleSlackCallback = async (code: string): Promise<SlackOAuthResponse> =>
    api.get(`/slack/oauth/callback?code=${code}`)

export const setSlackToken = async (botToken: string): Promise<SlackOAuthResponse> =>
    api.post('/slack/set-token', { token: botToken })

export const createSlackAgent = async (
    name: string,
    config: {
        trigger_on_mention?: boolean
        trigger_on_direct_message?: boolean
        trigger_on_channel_message?: boolean
        trigger_keywords?: string[]
        trigger_enabled?: boolean
        workflow_id: string
        spur_type?: SpurType
        bot_token?: string
        user_token?: string
        app_token?: string
    }
): Promise<SlackAgent | null> => {
    if (!config.workflow_id) {
        console.error('Cannot create a Slack agent without a workflow_id')
        return null
    }
    const { bot_token, user_token, app_token, ...agentConfig } = config
    const agent = await api.post<SlackAgent>('/slack/agents', { name, ...agentConfig })

    const tokenPromises: Promise<any>[] = []
    if (bot_token?.trim())
        tokenPromises.push(api.post(`/slack/agents/${agent.id}/tokens/bot_token`, { token: bot_token.trim() }))
    if (user_token?.trim())
        tokenPromises.push(api.post(`/slack/agents/${agent.id}/tokens/user_token`, { token: user_token.trim() }))
    if (app_token?.trim())
        tokenPromises.push(api.post(`/slack/agents/${agent.id}/tokens/app_token`, { token: app_token.trim() }))

    if (tokenPromises.length > 0) {
        try {
            await Promise.all(tokenPromises)
            return api.get(`/slack/agents/${agent.id}`)
        } catch (err) {
            console.error('Error setting tokens:', err)
        }
    }
    return agent
}

export const deleteSlackAgent = async (agentId: number, onAlert?: AlertFunction): Promise<boolean> => {
    try {
        await api.delete(`/slack/agents/${agentId}`)
        onAlert?.('Slack agent deleted successfully!', 'success')
        return true
    } catch (error) {
        console.error('Error deleting Slack agent:', error)
        onAlert?.('Failed to delete Slack agent', 'danger')
        return false
    }
}

export const toggleSlackTrigger = async (
    agentId: number,
    field: string,
    value: boolean,
    agents: SlackAgent[],
    updateAgentsCallback: (updater: (agents: SlackAgent[]) => SlackAgent[]) => void,
    onAlert?: AlertFunction
): Promise<void> => {
    try {
        const agent = agents.find((a) => a.id === agentId)
        if (!agent) return
        const config = {
            trigger_on_mention: field === 'trigger_on_mention' ? value : agent.trigger_on_mention,
            trigger_on_direct_message:
                field === 'trigger_on_direct_message' ? value : agent.trigger_on_direct_message,
            trigger_on_channel_message:
                field === 'trigger_on_channel_message' ? value : agent.trigger_on_channel_message,
            trigger_keywords: agent.trigger_keywords || [],
            trigger_enabled: field === 'trigger_enabled' ? value : agent.trigger_enabled,
        }
        const updatedAgent = await updateTriggerConfig(agentId, config)
        updateAgentsCallback((agents) => agents.map((a) => (a.id === agentId ? updatedAgent : a)))
        onAlert?.('Agent trigger settings updated successfully!', 'success')
    } catch (error) {
        console.error('Error updating agent trigger configuration:', error)
        onAlert?.('Failed to update agent configuration', 'danger')
    }
}

export const getSlackAgent = async (agentId: number): Promise<SlackAgent> =>
    api.get(`/slack/agents/${agentId}`)

export type SlackTokenType = 'bot_token' | 'user_token' | 'app_token'

export interface MaskedTokenResponse {
    masked_token: string
    updated_at: string | null
}

export const fetchMaskedToken = async (
    agentId: number,
    tokenType: SlackTokenType
): Promise<MaskedTokenResponse> => {
    try {
        return await api.get(`/slack/agents/${agentId}/tokens/${tokenType}`)
    } catch (err: any) {
        if (err?.response?.status === 404) return { masked_token: '', updated_at: null }
        throw err
    }
}

export const saveSlackTokens = async (
    agentId: number,
    tokens: { bot_token?: string; user_token?: string; app_token?: string }
): Promise<void> => {
    const requests = (Object.entries(tokens) as Array<[SlackTokenType, string | undefined]>)
        .filter(([, token]) => token?.trim())
        .map(([type, token]) => api.post(`/slack/agents/${agentId}/tokens/${type}`, { token: token!.trim() }))
    await Promise.all(requests)
}

export const deleteSlackToken = async (agentId: number, tokenType: SlackTokenType): Promise<void> =>
    api.delete(`/slack/agents/${agentId}/tokens/${tokenType}`)

export interface SlackConnectionTestResult {
    success: boolean
    message: string
    team_id?: string
    bot_id?: string
    user_id?: string
}

export const testSlackConnection = async (agentId: number): Promise<SlackConnectionTestResult> => {
    try {
        return await api.post(`/slack/agents/${agentId}/test-connection`)
    } catch (err: any) {
        let detail: string | undefined = err?.response?.data?.detail
        if (detail) {
            try {
                detail = JSON.parse(detail)?.detail ?? detail
            } catch {
                /* not JSON */
            }
        }
        return { success: false, message: detail || 'Failed to test Slack connection' }
    }
}

// Socket Mode requires an app-level token (xapp-). Failures are returned as a
// response object (not thrown) so the UI can render the actionable message.
const socketModeError = (err: any, agentId: number): SlackSocketModeResponse => {
    let detail: string = err?.response?.data?.detail ?? err?.message ?? ''
    try {
        detail = JSON.parse(detail)?.detail ?? detail
    } catch {
        /* not JSON */
    }
    if (/xapp|not_allowed_token_type|app.level|app token/i.test(detail)) {
        detail = 'Socket Mode requires an app-level token (xapp-...). Add one in the agent token settings.'
    }
    return {
        agent_id: agentId,
        socket_mode_active: false,
        message: detail || 'Socket Mode request failed',
    }
}

export const startSocketMode = async (agentId: number): Promise<SlackSocketModeResponse> => {
    try {
        return await api.post(`/slack/agents/${agentId}/socket-mode/start`)
    } catch (err) {
        return socketModeError(err, agentId)
    }
}

export const stopSocketMode = async (agentId: number): Promise<SlackSocketModeResponse> => {
    try {
        return await api.post(`/slack/agents/${agentId}/socket-mode/stop`)
    } catch (err) {
        return socketModeError(err, agentId)
    }
}

export const getSocketModeStatus = async (agentId: number): Promise<SlackSocketModeResponse | null> => {
    try {
        return await api.get(`/slack/agents/${agentId}/socket-mode/status`)
    } catch {
        return null
    }
}
