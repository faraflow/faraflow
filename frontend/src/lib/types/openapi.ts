export interface Parameter {
    name: string
    description?: string
    required: boolean
    type: string
    schema?: any
    format?: string
    items?: any
    enum?: string[]
    in: 'path' | 'query' | 'body' | 'formData' | 'header'
}

export interface OpenAPIEndpoint {
    path: string
    method: string
    summary?: string
    operationId?: string
    description?: string
    parameters: Parameter[]
    input_schema: any
    output_schema: any
}

export interface OpenAPISpec {
    id: string
    name: string
    description: string
    version: string
    raw_spec: any
    endpoints: OpenAPIEndpoint[]
}

export interface OpenAPIParserResult {
    endpoints: OpenAPIEndpoint[]
    error: string | null
}
