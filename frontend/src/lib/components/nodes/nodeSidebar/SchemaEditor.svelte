<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import Icon from '@iconify/svelte'
    import { convertToPythonVariableName } from '$lib/utils/variableNameUtils'
    import { isReservedWord } from '$lib/utils/schemaValidation'

    interface Props {
        jsonValue: Record<string, any>
        onChange: (value: Record<string, any>) => void
        options: string[]
        nodeId: string
        availableFields?: string[]
        readOnly?: boolean
    }

    let { jsonValue, onChange, options, nodeId, availableFields = [], readOnly = false }: Props = $props()

    const VALID_TYPES = ['string', 'number', 'integer', 'boolean', 'array', 'object']

    function getFields(schema: Record<string, any>): Array<{ key: string; typeDef: any }> {
        if (!schema) return []
        // JSON Schema format with `properties`
        const props = schema.properties || schema
        if (!props || typeof props !== 'object') return []
        return Object.entries(props).map(([key, typeDef]) => ({ key, typeDef }))
    }

    function getType(typeDef: any): string {
        if (!typeDef) return 'string'
        if (typeof typeDef === 'string') return typeDef
        if (typeDef.type) return typeDef.type
        if (typeDef.properties) return 'object'
        return 'string'
    }

    function addField() {
        if (readOnly) return
        const baseKey = 'new_field'
        const props = jsonValue.properties || jsonValue || {}
        let key = baseKey
        let i = 1
        while (key in props) {
            key = `${baseKey}_${i++}`
        }

        if (jsonValue.properties !== undefined) {
            onChange({ ...jsonValue, properties: { ...jsonValue.properties, [key]: { type: 'string' } } })
        } else {
            onChange({ ...jsonValue, [key]: 'string' })
        }
    }

    function removeField(key: string) {
        if (readOnly) return
        if (jsonValue.properties !== undefined) {
            const { [key]: _, ...rest } = jsonValue.properties
            const required = (jsonValue.required || []).filter((r: string) => r !== key)
            onChange({ ...jsonValue, properties: rest, required })
        } else {
            const { [key]: _, ...rest } = jsonValue
            onChange(rest)
        }
    }

    function renameField(oldKey: string, newKey: string) {
        if (readOnly || !newKey.trim() || newKey === oldKey) return
        const validKey = convertToPythonVariableName(newKey)
        if (!validKey || isReservedWord(validKey)) return

        if (jsonValue.properties !== undefined) {
            const entries = Object.entries(jsonValue.properties)
            const idx = entries.findIndex(([k]) => k === oldKey)
            if (idx === -1) return
            entries[idx] = [validKey, entries[idx][1]]
            const newProps = Object.fromEntries(entries)
            const required = (jsonValue.required || []).map((r: string) => (r === oldKey ? validKey : r))
            onChange({ ...jsonValue, properties: newProps, required })
        } else {
            const entries = Object.entries(jsonValue)
            const idx = entries.findIndex(([k]) => k === oldKey)
            if (idx === -1) return
            entries[idx] = [validKey, entries[idx][1]]
            onChange(Object.fromEntries(entries))
        }
    }

    function changeType(key: string, newType: string) {
        if (readOnly) return
        let newTypeDef: any
        if (newType === 'object') {
            newTypeDef = { type: 'object', properties: {}, required: [] }
        } else if (newType === 'array') {
            newTypeDef = { type: 'array', items: { type: 'string' } }
        } else {
            newTypeDef = { type: newType }
        }

        if (jsonValue.properties !== undefined) {
            onChange({ ...jsonValue, properties: { ...jsonValue.properties, [key]: newTypeDef } })
        } else {
            onChange({ ...jsonValue, [key]: newTypeDef })
        }
    }

    let editingKey = $state<string | null>(null)
    let editKeyValue = $state('')

    function startEdit(key: string) {
        if (readOnly) return
        editingKey = key
        editKeyValue = key
    }

    function commitEdit(oldKey: string) {
        if (editKeyValue && editKeyValue !== oldKey) {
            renameField(oldKey, editKeyValue)
        }
        editingKey = null
    }

    const fields = $derived(getFields(jsonValue))
</script>

<div class="schema-editor space-y-2">
    {#each fields as { key, typeDef }}
        <div class="flex items-center gap-2 group">
            <!-- Field name -->
            {#if editingKey === key}
                <!-- svelte-ignore a11y_autofocus -->
                <input
                    class="flex-1 text-sm px-2 py-1 rounded border border-primary bg-default-100 outline-none"
                    bind:value={editKeyValue}
                    onblur={() => commitEdit(key)}
                    onkeydown={(e) => {
                        if (e.key === 'Enter') commitEdit(key)
                        if (e.key === 'Escape') { editingKey = null }
                    }}
                    autofocus
                />
            {:else}
                <!-- svelte-ignore a11y_click_events_have_key_events -->
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <span
                    class="flex-1 text-sm px-2 py-1 rounded bg-default-100 truncate cursor-pointer hover:bg-default-200"
                    onclick={() => startEdit(key)}
                    title={key}
                >
                    {key}
                </span>
            {/if}

            <!-- Type selector -->
            <select
                class="text-xs px-2 py-1 rounded border border-default-200 bg-background focus:outline-none focus:border-primary"
                value={getType(typeDef)}
                disabled={readOnly}
                onchange={(e) => changeType(key, e.currentTarget.value)}
            >
                {#each VALID_TYPES as t}
                    <option value={t}>{t}</option>
                {/each}
            </select>

            <!-- Delete -->
            {#if !readOnly}
                <button
                    type="button"
                    class="opacity-0 group-hover:opacity-100 p-1 rounded text-destructive hover:bg-destructive/10"
                    onclick={() => removeField(key)}
                    title="Remove field"
                >
                    <Icon icon="solar:trash-bin-trash-linear" width={16} />
                </button>
            {/if}
        </div>
    {/each}

    {#if !readOnly}
        <button
            type="button"
            class="flex items-center gap-1 text-sm text-primary hover:underline mt-1"
            onclick={addField}
        >
            <Icon icon="solar:add-circle-linear" width={16} />
            Add field
        </button>
    {/if}
</div>
