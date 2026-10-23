// Copyright 2026 Alokin LLC
// SPDX-License-Identifier: FCL-1.0-ALv2
import { getNodeTypes } from '$lib/utils/api'
import type { FieldMetadata } from '$lib/types/api_types/modelMetadataSchemas'

export interface NodeMetadata {
    name: string
    config?: Record<string, FieldMetadata>
    visual_tag?: {
        color: string
        acronym: string
    }
    [key: string]: any
}

class NodeTypesStore {
    data = $state<Record<string, any> | null>(null)
    metadata = $state<Record<string, NodeMetadata[]>>({})
    status = $state<'idle' | 'loading' | 'succeeded' | 'failed'>('idle')
    error = $state<string | null>(null)

    async fetch() {
        this.status = 'loading'
        try {
            const response = await getNodeTypes()
            this.data = response.schema
            this.metadata = response.metadata
            this.status = 'succeeded'
        } catch (e: any) {
            this.status = 'failed'
            this.error = e?.message ?? 'An error occurred'
        }
    }

    /** Return the metadata value at a dotted path like "NodeType.config.fieldName" */
    selectPropertyMetadata(propertyPath: string): any | null {
        if (!propertyPath) return null
        const [nodeType, ...pathParts] = propertyPath.split('.')
        const remainingPath = pathParts.join('.')
        return findMetadataInCategory(this.metadata, nodeType, remainingPath)
    }

    /** Return list of missing required field names for a given node. */
    getMissingRequiredFields(nodeType: string, nodeConfig: Record<string, any>): string[] {
        return getNodeMissingRequiredFields(nodeType, nodeConfig, this.metadata)
    }
}

function findMetadataInCategory(
    metadata: Record<string, NodeMetadata[]> | null,
    nodeType: string,
    path: string
): any | null {
    if (!metadata) return null
    for (const category of Object.keys(metadata)) {
        const nodes = metadata[category]
        if (!nodes) continue
        const node = nodes.find((n: NodeMetadata) => n.name === nodeType)
        if (!node) continue
        const parts = path.split('.')
        let current: any = node
        for (const part of parts) {
            if (current && typeof current === 'object' && part in current) {
                current = current[part]
            } else {
                return null
            }
        }
        return current
    }
    return null
}

export function getNodeMissingRequiredFields(
    nodeType: string,
    nodeConfig: Record<string, any>,
    metadata: Record<string, NodeMetadata[]>
): string[] {
    for (const category of Object.keys(metadata)) {
        const nodeMetadata = metadata[category]?.find((md) => md.name === nodeType)
        if (!nodeMetadata) continue

        const missingFields: string[] = []
        if (!nodeMetadata.config) return missingFields

        for (const [field, fieldMetadata] of Object.entries(nodeMetadata.config)) {
            if (field.toLowerCase().includes('schema')) continue

            if (field === 'llm_info' || field === 'ModelInfo') {
                if (nodeConfig.llm_info === undefined) missingFields.push('ModelInfo')
                continue
            }

            if (fieldMetadata.required) {
                const value = nodeConfig[field]
                if (
                    value === undefined ||
                    value === null ||
                    value === '' ||
                    (typeof value === 'string' && value.trim() === '') ||
                    (Array.isArray(value) && value.length === 0)
                ) {
                    missingFields.push(field)
                }
            }

            if (fieldMetadata.properties && field !== 'llm_info') {
                for (const [nestedField, nestedMeta] of Object.entries(fieldMetadata.properties)) {
                    if (nestedField.toLowerCase().includes('schema')) continue
                    if (nestedMeta.required) {
                        const nestedValue = nodeConfig[field]?.[nestedField]
                        if (
                            nestedValue === undefined ||
                            nestedValue === null ||
                            nestedValue === '' ||
                            (typeof nestedValue === 'string' && nestedValue.trim() === '') ||
                            (Array.isArray(nestedValue) && nestedValue.length === 0)
                        ) {
                            missingFields.push(`${field}.${nestedField}`)
                        }
                    }
                }
            }
        }
        return missingFields
    }
    return []
}

export const nodeTypesStore = new NodeTypesStore()
