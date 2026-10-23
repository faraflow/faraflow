// Originally from PySpur (https://github.com/PySpur-Dev/pyspur), licensed under Apache-2.0.
// Modified by Alokin LLC, 2026; modifications licensed under FCL-1.0-ALv2.
// SPDX-License-Identifier: Apache-2.0 AND FCL-1.0-ALv2
export interface VectorIndexResponseSchema {
    id: string
    name: string
    description?: string
    collection_id: string
    status: string
    created_at: string
    updated_at: string
    document_count: number
    chunk_count: number
    error_message?: string
    embedding_model: string
    vector_db: string
}

export interface DocumentCollectionResponseSchema {
    id: string
    name: string
    description?: string
    status: string
    created_at: string
    updated_at: string
    document_count: number
    chunk_count: number
    error_message?: string
}

export interface ProcessingProgressSchema {
    id: string
    status: string
    progress: number
    current_step: string
    total_files?: number
    processed_files?: number
    total_chunks?: number
    processed_chunks?: number
    error_message?: string
    created_at: string
    updated_at: string
}

export interface RetrievalResultSchema {
    text: string
    score: number
    metadata: {
        document_id: string
        chunk_id: string
        document_title?: string
        page_number?: number
        chunk_number?: number
    }
}

export interface RetrievalResponseSchema {
    results: RetrievalResultSchema[]
    total_results: number
}

export interface DocumentChunkSchema {
    id: string
    text: string
    metadata?: Record<string, any>
}

export interface DocumentWithChunksSchema {
    id: string
    text: string
    metadata?: Record<string, any>
    chunks: DocumentChunkSchema[]
}

export interface ChunkPreviewSchema {
    original_text: string
    processed_text: string
    metadata: Record<string, string>
    chunk_index: number
}

export interface ChunkPreviewResponseSchema {
    chunks: ChunkPreviewSchema[]
    total_chunks: number
}

export interface ChunkTemplateSchema {
    enabled: boolean
    template: string
    metadata_template: { type: string } | Record<string, string>
}

export interface DocumentCollectionCreateRequestSchema {
    name: string
    description?: string
    text_processing: {
        chunk_token_size: number
        min_chunk_size_chars: number
        min_chunk_length_to_embed: number
        embeddings_batch_size?: number
        max_num_chunks: number
        use_vision_model: boolean
        vision_model?: string
        vision_provider?: string
        template?: ChunkTemplateSchema
    }
}

export interface VectorIndexCreateRequestSchema {
    name: string
    description?: string
    collection_id: string
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
