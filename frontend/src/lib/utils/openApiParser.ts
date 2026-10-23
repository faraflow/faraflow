// Originally from PySpur (https://github.com/PySpur-Dev/pyspur), licensed under Apache-2.0.
// Modified by Alokin LLC, 2026; modifications licensed under FCL-1.0-ALv2.
// SPDX-License-Identifier: Apache-2.0 AND FCL-1.0-ALv2
import type { OpenAPIEndpoint, OpenAPIParserResult, Parameter } from '../types/openapi'

// Helper function to resolve schema references
export const resolveSchemaRef = (schema: any, definitions: any): any => {
    if (!schema) return null

    if (schema.$ref) {
        const refPath = schema.$ref.split('/')
        const definition = refPath.reduce((obj: any, key: string) => {
            if (key === '#' || key === 'definitions') return obj
            return obj[key]
        }, definitions)
        return resolveSchemaRef(definition, definitions)
    }

    if (schema.type === 'array' && schema.items) {
        return {
            ...schema,
            items: resolveSchemaRef(schema.items, definitions),
        }
    }

    if (schema.type === 'object' && schema.properties) {
        const resolvedProperties: any = {}
        Object.entries(schema.properties).forEach(([key, value]: [string, any]) => {
            resolvedProperties[key] = resolveSchemaRef(value, definitions)
        })
        return {
            ...schema,
            properties: resolvedProperties,
        }
    }

    return schema
}

// Parse parameters and schemas
const parseParameters = (methodObj: any, definitions: any): Parameter[] => {
    const parameters: Parameter[] = []

    // Handle regular parameters (path, query, header, formData)
    if (methodObj.parameters) {
        methodObj.parameters.forEach((param: any) => {
            parameters.push({
                name: param.name,
                description: param.description,
                required: param.required || false,
                type: param.type || (param.schema ? resolveSchemaRef(param.schema, definitions).type : 'object'),
                schema: param.schema ? resolveSchemaRef(param.schema, definitions) : undefined,
                format: param.format,
                items: param.items ? resolveSchemaRef(param.items, definitions) : undefined,
                enum: param.enum,
                in: param.in || 'query', // Default to query if not specified
            })
        })
    }

    // Handle request body if present (OpenAPI v3)
    if (methodObj.requestBody) {
        const content = methodObj.requestBody.content
        const mediaType = Object.keys(content)[0]
        if (mediaType && content[mediaType].schema) {
            const bodySchema = resolveSchemaRef(content[mediaType].schema, definitions)
            parameters.push({
                name: 'body',
                description: methodObj.requestBody.description,
                required: methodObj.requestBody.required || false,
                type: 'object',
                schema: bodySchema,
                in: 'body',
            })
        }
    }

    // Handle body parameter (OpenAPI v2/Swagger)
    const bodyParam = methodObj.parameters?.find((p: any) => p.in === 'body')
    if (bodyParam && !methodObj.requestBody) {
        parameters.push({
            name: bodyParam.name,
            description: bodyParam.description,
            required: bodyParam.required || false,
            type: 'object',
            schema: bodyParam.schema ? resolveSchemaRef(bodyParam.schema, definitions) : undefined,
            in: 'body',
        })
    }

    return parameters
}

// Parse OpenAPI spec
export const parseOpenAPISpec = (rawSpec: any): OpenAPIParserResult => {
    try {
        const spec = typeof rawSpec === 'string' ? JSON.parse(rawSpec) : rawSpec
        const parsedEndpoints: OpenAPIEndpoint[] = []
        const definitions = spec.definitions || {}

        // Parse paths and methods from OpenAPI spec
        Object.entries(spec.paths || {}).forEach(([path, pathObj]: [string, any]) => {
            Object.entries(pathObj).forEach(([method, methodObj]: [string, any]) => {
                if (method === 'parameters') return // Skip path-level parameters

                // Get successful response schema (200 or 201)
                let output_schema = null
                const successResponse = methodObj.responses?.['200'] || methodObj.responses?.['201']
                if (successResponse?.schema) {
                    // Handle array responses
                    if (successResponse.schema.type === 'array' && successResponse.schema.items) {
                        output_schema = {
                            type: 'array',
                            items: resolveSchemaRef(successResponse.schema.items, definitions),
                        }
                    } else {
                        output_schema = resolveSchemaRef(successResponse.schema, definitions)
                    }
                } else if (successResponse?.content) {
                    // OpenAPI v3 format
                    const mediaType = Object.keys(successResponse.content)[0]
                    if (mediaType && successResponse.content[mediaType].schema) {
                        const schema = successResponse.content[mediaType].schema
                        if (schema.type === 'array' && schema.items) {
                            output_schema = {
                                type: 'array',
                                items: resolveSchemaRef(schema.items, definitions),
                            }
                        } else {
                            output_schema = resolveSchemaRef(schema, definitions)
                        }
                    }
                }

                parsedEndpoints.push({
                    path,
                    method: method.toUpperCase(),
                    summary: methodObj.summary,
                    operationId: methodObj.operationId,
                    description: methodObj.description,
                    parameters: parseParameters(methodObj, definitions),
                    input_schema: methodObj.requestBody
                        ? resolveSchemaRef(
                              methodObj.requestBody.content?.[Object.keys(methodObj.requestBody.content)[0]]?.schema,
                              definitions
                          )
                        : null,
                    output_schema,
                })
            })
        })

        return {
            endpoints: parsedEndpoints,
            error: null,
        }
    } catch (err) {
        return {
            endpoints: [],
            error: 'Invalid OpenAPI specification. Please check your JSON.',
        }
    }
}
