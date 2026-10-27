<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { onMount } from 'svelte'
    import Icon from '@iconify/svelte'
    import Ajv from 'ajv'
    import { flowStore } from '$lib/stores/flow.svelte'
    import { nodeTypesStore } from '$lib/stores/nodeTypes.svelte'
    import type { FlowWorkflowNode, FlowWorkflowNodeConfig } from '$lib/types/api_types/nodeTypeSchemas'
    import type { FieldMetadata, ModelConstraints } from '$lib/types/api_types/modelMetadataSchemas'
    import { extractSchemaFromJsonSchema, generateJsonSchemaFromSchema } from '$lib/utils/schemaUtils'
    import { convertToPythonVariableName } from '$lib/utils/variableNameUtils'
    import { isReservedWord } from '$lib/utils/schemaValidation'
    import { listVectorIndices } from '$lib/utils/api'
    import NodeOutputDisplay from '../NodeOutputDisplay.svelte'
    import NodeErrorDisplay from '../NodeErrorDisplay.svelte'
    import TextEditor from '$lib/components/textEditor/TextEditor.svelte'
    import CodeEditor from '$lib/components/textEditor/CodeEditor.svelte'
    import OutputSchemaEditor from './OutputSchemaEditor.svelte'
    import IOMapEditor from './IOMapEditor.svelte'
    import FewShotExamplesEditor from '$lib/components/textEditor/FewShotExamplesEditor.svelte'
    import ModelListEditor from './ModelListEditor.svelte'


    interface Props {
        nodeID: string
        readOnly?: boolean
        rightOffset?: number
        embedded?: boolean
        activeTab?: 'outputs' | 'config'
    }

    let { nodeID, readOnly = false, rightOffset = 16, embedded = false, activeTab = undefined }: Props = $props()

    // ─── Derived state from stores ──────────────────────────────────────────────
    const node = $derived(flowStore.nodes.find((n) => n.id === nodeID) || null)
    const nodeConfig = $derived(flowStore.nodeConfigs[nodeID] || {})
    const nodeType = $derived(node?.type || '')

    const nodeSchema = $derived.by(() => {
        if (!nodeType || !nodeTypesStore.data) return null
        for (const category of Object.keys(nodeTypesStore.data)) {
            const found = nodeTypesStore.data[category]?.find((n: any) => n.name === nodeType)
            if (found) return found
        }
        return null
    })

    // ─── Local state ────────────────────────────────────────────────────────────
    let currentNodeConfig = $state<FlowWorkflowNodeConfig>({})
    let jsonSchemaError = $state('')
    let showTitleError = $state(false)
    let vectorIndices = $state<any[]>([])
    let isLoadingIndices = $state(false)
    let messageVersions = $state<Record<string, number>>({})
    let width = $state(flowStore.sidebarWidth || 400)
    let isResizing = $state(false)

    // Sync nodeConfig -> local state whenever the nodeConfig changes
    $effect(() => {
        currentNodeConfig = { ...nodeConfig }
    })

    // Auto-initialize output_json_schema from output_schema
    $effect(() => {
        if (nodeConfig.output_schema && !nodeConfig.output_json_schema) {
            const jsonSchema = generateJsonSchemaFromSchema(nodeConfig.output_schema)
            if (jsonSchema) {
                flowStore.updateNodeConfigOnly(nodeID, { ...nodeConfig, output_json_schema: jsonSchema })
            }
        }
    })

    // Fetch vector indices for RetrieverNode
    $effect(() => {
        if (nodeType === 'RetrieverNode') {
            fetchVectorIndices()
        }
    })

    // Validate json schema when it changes
    $effect(() => {
        if (currentNodeConfig.output_json_schema) {
            jsonSchemaError = validateJsonSchema(currentNodeConfig.output_json_schema) || ''
        }
    })

    async function fetchVectorIndices() {
        isLoadingIndices = true
        try {
            vectorIndices = await listVectorIndices()
        } catch (e) {
            console.error('Error fetching vector indices:', e)
        } finally {
            isLoadingIndices = false
        }
    }

    // ─── Incoming schema computation ─────────────────────────────────────────────
    const incomingSchema = $derived.by(() => {
        const result: string[] = []
        const incomingEdges = flowStore.edges.filter((e) => e.target === nodeID)

        for (const edge of incomingEdges) {
            const srcNode = flowStore.nodes.find((n) => n.id === edge.source)
            if (!srcNode) continue
            const config = flowStore.nodeConfigs[srcNode.id]

            // 1. Saved output_json_schema
            // 2. Generate from output_schema
            // 3. Fixed-output nodes: use the output schema from the node type definition
            let jsonSchema: string | null = config?.output_json_schema
                ?? (config?.output_schema ? generateJsonSchemaFromSchema(config.output_schema) : null)

            if (!jsonSchema && srcNode.type && nodeTypesStore.data) {
                for (const nodes of Object.values(nodeTypesStore.data)) {
                    const nodeTypeDef = (nodes as any[]).find((n: any) => n.name === srcNode.type)
                    if (nodeTypeDef?.has_fixed_output && nodeTypeDef.output) {
                        jsonSchema = JSON.stringify(nodeTypeDef.output)
                        break
                    }
                }
            }

            if (!jsonSchema) continue

            const nodeTitle = config?.title || srcNode.id
            const { schema, error } = extractSchemaFromJsonSchema(jsonSchema)
            if (error || !schema || typeof schema !== 'object') continue

            if (srcNode.type === 'RouterNode') {
                Object.entries(schema).forEach(([routeKey, routeValue]) => {
                    if (routeValue && typeof routeValue === 'object') {
                        const routeProps = (routeValue as any).properties
                        if (routeProps) {
                            Object.keys(routeProps).forEach((propKey) => {
                                result.push(`${nodeTitle}.${routeKey}.${propKey}`)
                            })
                        }
                    }
                })
            } else {
                Object.keys(schema).forEach((key) => result.push(`${nodeTitle}.${key}`))
            }
        }
        return result
    })

    // ─── Model constraints ───────────────────────────────────────────────────────
    const currentModelConstraints: ModelConstraints | null = $derived.by(() => {
        const modelId = currentNodeConfig?.llm_info?.model
        if (!modelId || !nodeSchema?.model_constraints) return null
        return nodeSchema.model_constraints[modelId] || null
    })

    // ─── AJV for schema validation ───────────────────────────────────────────────
    const ajv = new Ajv({ strict: false, allErrors: true })

    function validateJsonSchema(schema: string): string | null {
        if (!schema?.trim()) return 'Schema cannot be empty'
        let parsed: any
        try {
            parsed = JSON.parse(schema)
        } catch (e: any) {
            return `Invalid JSON: ${e.message}`
        }
        if (!parsed.properties) return 'Schema must have a properties field'
        if (typeof parsed.properties !== 'object') return 'properties must be an object'
        const reservedProps = Object.keys(parsed.properties).filter((p) => isReservedWord(p))
        if (reservedProps.length > 0) {
            return `Property names [${reservedProps.join(', ')}] are Python reserved keywords`
        }
        return null
    }

    // ─── Field helpers ────────────────────────────────────────────────────────────
    function getFieldMetadata(fullPath: string): FieldMetadata | undefined {
        return nodeTypesStore.selectPropertyMetadata(fullPath) as FieldMetadata
    }

    function isTemplateField(key: string, meta?: FieldMetadata): boolean {
        if (meta?.template === true) return true
        return ['template', 'message', 'prompt'].some((p) => key === p || key.endsWith(p))
    }

    // ─── Input change handler ──────────────────────────────────────────────────
    let debounceTimer: ReturnType<typeof setTimeout> | null = null

    function handleInputChange(key: string, value: any, isSlider = false) {
        if (readOnly) return

        let updated: FlowWorkflowNodeConfig
        if (key.includes('.')) {
            updated = JSON.parse(JSON.stringify(currentNodeConfig))
            const parts = key.split('.')
            let obj: any = updated
            for (let i = 0; i < parts.length - 1; i++) {
                if (obj[parts[i]] === undefined) obj[parts[i]] = {}
                obj = obj[parts[i]]
            }
            obj[parts[parts.length - 1]] = value
        } else {
            updated = { ...currentNodeConfig, [key]: value }
        }

        currentNodeConfig = updated

        if (isSlider) {
            if (debounceTimer) clearTimeout(debounceTimer)
            debounceTimer = setTimeout(() => {
                flowStore.updateNodeConfigOnly(nodeID, updated)
            }, 300)
        } else {
            flowStore.updateNodeConfigOnly(nodeID, updated)
        }
    }

    function handleTitleChangeComplete(value: string) {
        if (readOnly) return
        const validTitle = convertToPythonVariableName(value)
        if (validTitle !== value) {
            showTitleError = true
            setTimeout(() => (showTitleError = false), 3000)
        }
        flowStore.updateNodeTitle(nodeID, validTitle)
    }

    // ─── Resize logic ─────────────────────────────────────────────────────────
    function handleMouseDown(e: MouseEvent) {
        isResizing = true
        e.preventDefault()
    }

    function handleMouseMove(e: MouseEvent) {
        if (!isResizing) return
        const newWidth = window.innerWidth - e.clientX
        width = Math.min(Math.max(newWidth, 300), 800)
    }

    function handleMouseUp() {
        if (isResizing) {
            isResizing = false
            flowStore.setSidebarWidth(width)
        }
    }

    // ─── Config field ordering ────────────────────────────────────────────────
    const SCHEMA_KEYWORDS = new Set(['$defs', 'properties', 'additionalProperties', '$ref', 'required',
        'description', 'anyOf', 'oneOf', 'allOf', 'items', 'definitions'])

    const orderedConfigKeys = $derived.by(() => {
        if (!nodeSchema?.config || !currentNodeConfig) return []
        const properties = nodeSchema.config
        const keys = Object.keys(properties).filter((k) => k !== 'title' && k !== 'type' && !SCHEMA_KEYWORDS.has(k))
        const priorityFields = ['system_message', 'user_message']
        const templateFields = keys.filter(
            (k) =>
                (k.includes('template') || k.includes('message') || k.includes('prompt')) &&
                !['enable_message_history', 'message_history_variable'].includes(k) &&
                !priorityFields.includes(k)
        )
        const isClaudeSonnet37 = currentNodeConfig?.llm_info?.model === 'anthropic/claude-3-7-sonnet-latest'
        const remaining = keys
            .filter((k) => !priorityFields.includes(k) && !templateFields.includes(k))
            .filter((k) => {
                if (!isClaudeSonnet37 && (k === 'enable_thinking' || k === 'thinking_budget_tokens')) return false
                if (k === 'enable_message_history' || k === 'message_history_variable') return false
                return true
            })
        return [...priorityFields.filter((k) => keys.includes(k)), ...templateFields, ...remaining]
    })

    // Index after which to insert message history config section
    const messageHistoryInsertIndex = $derived.by(() => {
        if (!nodeSchema?.config) return -1
        const keys = orderedConfigKeys
        const priorityFields = ['system_message', 'user_message']
        const priorityPresent = priorityFields.filter((k) => keys.includes(k))
        const templateFields = keys.filter(
            (k, i) => i >= priorityPresent.length &&
                (k.includes('template') || k.includes('message') || k.includes('prompt')) &&
                !['enable_message_history', 'message_history_variable'].includes(k) &&
                !priorityFields.includes(k)
        )
        return priorityPresent.length + templateFields.length - 1
    })

    // ─── Output schema derived props ─────────────────────────────────────────
    const isOutputSchemaReadOnly = $derived.by(() => {
        return (
            !!currentNodeConfig?.has_fixed_output ||
            (currentNodeConfig?.llm_info?.model && !currentModelConstraints?.supports_JSON_output) ||
            nodeType === 'RouterNode' ||
            nodeType === 'CoalesceNode' ||
            readOnly ||
            false
        )
    })

    // ─── Output schema properties for mapping ────────────────────────────────
    const outputSchemaProperties = $derived.by(() => {
        try {
            if (!currentNodeConfig?.output_json_schema) return []
            const parsed =
                typeof currentNodeConfig.output_json_schema === 'string'
                    ? JSON.parse(currentNodeConfig.output_json_schema)
                    : currentNodeConfig.output_json_schema
            return Object.keys(parsed?.properties || {})
        } catch {
            return []
        }
    })

    // ─── Model grouping helpers ───────────────────────────────────────────────
    function groupModelsByProvider(modelIds: string[]) {
        const groups: Record<string, string[]> = {
            OpenAI: [],
            Anthropic: [],
            Google: [],
            Deepseek: [],
            'IFM K2 Horizon': [],
            'IFM Jais 3': [],
            Ollama: [],
        }
        for (const id of modelIds) {
            if (id.startsWith('ollama/')) groups.Ollama.push(id)
            else if (id.startsWith('anthropic')) groups.Anthropic.push(id)
            else if (id.startsWith('gemini')) groups.Google.push(id)
            else if (id.startsWith('deepseek')) groups.Deepseek.push(id)
            else if (id.startsWith('ifm/Jais')) groups['IFM Jais 3'].push(id)
            else if (id.startsWith('ifm/')) groups['IFM K2 Horizon'].push(id)
            else groups.OpenAI.push(id)
        }
        return groups
    }

    const hasRunOutput = $derived(!!node?.data?.run)

    // Enum of all available model IDs — reused for AskNode's ModelListEditor
    const availableModelIds = $derived.by(() => {
        const meta = getFieldMetadata('SingleLLMCallNode.config.llm_info.model')
        return (meta as any)?.enum as string[] ?? []
    })
    const hasError = $derived(!!node?.data?.error)
    let accordionOpen = $state<Record<string, boolean>>({
        output: false,
        config: true,
    })

    $effect(() => {
        if (embedded) {
            // In embedded mode, always show the relevant section open
            accordionOpen = { output: true, config: true }
        } else {
            accordionOpen = { output: hasRunOutput || hasError, config: !hasRunOutput && !hasError }
        }
    })
</script>

<svelte:window
    onmousemove={!embedded ? handleMouseMove : undefined}
    onmouseup={!embedded ? handleMouseUp : undefined}
/>

{#snippet sidebarContent()}
    {#if showTitleError}
        <div class="flex items-center gap-2 text-sm text-destructive bg-destructive/10 px-3 py-2 rounded-lg mb-3">
            Title cannot contain whitespace. Use underscores instead.
        </div>
    {/if}

    <!-- Output section -->
    {#if !activeTab || activeTab === 'outputs'}
        <div class="mb-2">
            {#if embedded}
                {#if node?.data?.error}
                    <NodeErrorDisplay error={node.data.error} grow={embedded} />
                {/if}
                {#if node?.data?.run && Object.keys(node.data.run).length > 0}
                    <NodeOutputDisplay output={node.data.run} grow={embedded} />
                {:else if !node?.data?.error}
                    <p class="text-sm text-muted-foreground text-center py-4">No output yet</p>
                {/if}
            {:else}
                <button
                    type="button"
                    class="w-full flex items-center justify-between py-2 text-sm font-medium"
                    onclick={() => (accordionOpen.output = !accordionOpen.output)}
                >
                    <span>Outputs</span>
                    <Icon icon={accordionOpen.output ? 'solar:alt-arrow-up-linear' : 'solar:alt-arrow-down-linear'} width={18} />
                </button>
                {#if accordionOpen.output}
                    <div class="border border-default-200 rounded-lg p-3 bg-default-50">
                        {#if node?.data?.error}
                            <NodeErrorDisplay error={node.data.error} />
                        {/if}
                        {#if node?.data?.run && Object.keys(node.data.run).length > 0}
                            <NodeOutputDisplay output={node.data.run} />
                        {/if}
                    </div>
                {/if}
            {/if}
        </div>
    {/if}

    <!-- Configuration section -->
    {#if !activeTab || activeTab === 'config'}
    <div>
            {#if !embedded}
                <button
                    type="button"
                    class="w-full flex items-center justify-between py-2 text-sm font-medium"
                    onclick={() => (accordionOpen.config = !accordionOpen.config)}
                >
                    <span>Node Configuration</span>
                    <Icon icon={accordionOpen.config ? 'solar:alt-arrow-up-linear' : 'solar:alt-arrow-down-linear'} width={18} />
                </button>
            {/if}
            {#if embedded || accordionOpen.config}
                <div class="space-y-4">
                    <!-- Title input -->
                    <div>
                        <label class="block text-xs font-medium text-foreground-500 mb-1">
                            Node Title
                            <input
                                type="text"
                                class="w-full text-sm px-3 py-2 rounded-lg border border-default-200 bg-background focus:outline-none focus:border-primary disabled:opacity-50"
                                value={nodeConfig?.title || node?.id || ''}
                                disabled={readOnly}
                                onblur={(e) => handleTitleChangeComplete(e.currentTarget.value)}
                                onkeydown={(e) => {
                                    if (e.key === 'Enter') e.currentTarget.blur()
                                }}
                                placeholder="Enter node title"
                            />
                        </label>
                        <p class="text-xs text-foreground-500 mt-0.5">Use underscores instead of spaces</p>
                    </div>
                    <hr class="border-default-200" />

                    <!-- Config fields -->
                    {#if nodeSchema?.config && currentNodeConfig}
                        {#each orderedConfigKeys as key, keyIndex}
                            {@const field = nodeSchema.config[key]}
                            {@const value = currentNodeConfig[key]}
                            {@const fullPath = `${nodeType}.config.${key}`}
                            {@const fieldMeta = getFieldMetadata(fullPath)}
                            {@const isLast = keyIndex === orderedConfigKeys.length - 1}

                            <!-- Skip hidden fields -->
                            {#if key !== 'output_schema' && key !== 'has_fixed_output'}
                                <!-- Special: output_json_schema -->
                                {#if key === 'output_json_schema'}
                                    <div class="my-3">
                                        <div class="flex items-center gap-2 mb-2">
                                            <h3 class="font-semibold text-sm">Output Schema</h3>
                                            {#if !currentNodeConfig?.has_fixed_output && currentNodeConfig?.llm_info?.model}
                                                <button
                                                    type="button"
                                                    class="p-0.5 rounded hover:bg-default-100"
                                                    title="Reset to default schema"
                                                    onclick={() => {
                                                        const def = JSON.stringify({ type: 'object', properties: { output: { type: 'string' } }, required: ['output'] }, null, 2)
                                                        handleInputChange('output_json_schema', def)
                                                    }}
                                                >
                                                    <Icon icon="solar:restart-linear" width={18} />
                                                </button>
                                            {/if}
                                        </div>
                                        <OutputSchemaEditor
                                            nodeID={nodeID}
                                            schema={currentNodeConfig.output_json_schema || ''}
                                            readOnly={isOutputSchemaReadOnly}
                                            error={jsonSchemaError}
                                            onChange={(s) => {
                                                handleInputChange('output_json_schema', s)
                                                jsonSchemaError = validateJsonSchema(s) || ''
                                            }}
                                        />
                                    </div>
                                <!-- Special: input_map -->
                                {:else if key === 'input_map'}
                                    <div class="my-3">
                                        <div class="flex items-center gap-2 mb-2">
                                            <h3 class="font-semibold text-sm">Input Mapping</h3>
                                        </div>
                                        <IOMapEditor
                                            leftOptions={incomingSchema}
                                            rightOptions={outputSchemaProperties}
                                            value={value || {}}
                                            onChange={(v) => handleInputChange(key, v)}
                                            {readOnly}
                                            leftLabel="Incoming Field"
                                            rightLabel="Input Field"
                                        />
                                    </div>
                                <!-- Special: output_map -->
                                {:else if key === 'output_map'}
                                    <div class="my-3">
                                        <div class="flex items-center gap-2 mb-2">
                                            <h3 class="font-semibold text-sm">Output Mapping</h3>
                                        </div>
                                        <IOMapEditor
                                            leftOptions={outputSchemaProperties}
                                            rightOptions={incomingSchema}
                                            value={value || {}}
                                            onChange={(v) => handleInputChange(key, v)}
                                            {readOnly}
                                            leftLabel="Output Field"
                                            rightLabel="Target Field"
                                        />
                                    </div>
                                <!-- Special: code field -->
                                {:else if key === 'code'}
                                    <div class="my-3">
                                        <CodeEditor
                                            code={value || ''}
                                            mode="python"
                                            onChange={(v) => handleInputChange(key, v)}
                                            {readOnly}
                                        />
                                    </div>
                                <!-- Special: api_base (Ollama only) -->
                                {:else if key === 'api_base'}
                                    {#if currentNodeConfig?.llm_info?.model?.startsWith?.('ollama/')}
                                        <div class="my-3">
                                            <label class="block text-xs font-medium text-foreground-500 mb-1">
                                                {fieldMeta?.title || key}
                                                <input
                                                    type="text"
                                                    class="w-full text-sm px-3 py-2 rounded-lg border border-default-200 bg-background focus:outline-none"
                                                    value={value || 'http://localhost:11434'}
                                                    disabled={readOnly}
                                                    onchange={(e) => handleInputChange(key, e.currentTarget.value)}
                                                    placeholder="Enter API base URL"
                                                />
                                            </label>
                                        </div>
                                    {/if}
                                <!-- Special: vector_index_id (RetrieverNode) -->
                                {:else if key === 'vector_index_id' && nodeType === 'RetrieverNode'}
                                    <div class="my-3">
                                        <label class="block text-sm font-semibold mb-2">
                                            Vector Index
                                            <select
                                                class="w-full text-sm px-2 py-1.5 rounded border border-default-200 bg-background focus:outline-none disabled:opacity-50"
                                                value={value || ''}
                                                disabled={readOnly}
                                                onchange={(e) => handleInputChange(key, e.currentTarget.value)}
                                            >
                                                <option value="">Select a vector index</option>
                                                {#each vectorIndices as idx}
                                                    <option value={idx.id} disabled={idx.status !== 'ready'}>{idx.name} ({idx.status})</option>
                                                {/each}
                                            </select>
                                        </label>
                                    </div>
                                <!-- Enum field -->
                                {:else if fieldMeta?.enum}
                                    <div class="my-3">
                                        {#if key === 'model' && fullPath.includes('llm_info')}
                                            <!-- Grouped model select -->
                                            <label class="block text-xs font-medium text-foreground-500 mb-1">
                                                {fieldMeta?.title || key}
                                                <select
                                                    class="w-full text-sm px-2 py-1.5 rounded border border-default-200 bg-background focus:outline-none"
                                                    value={currentNodeConfig?.llm_info?.model || fieldMeta?.default || ''}
                                                    disabled={readOnly}
                                                    onchange={(e) => {
                                                        const selectedModelId = e.currentTarget.value
                                                        const constraints = nodeSchema?.model_constraints?.[selectedModelId] || null
                                                        const updatedModel = {
                                                            ...currentNodeConfig,
                                                            llm_info: {
                                                                ...currentNodeConfig.llm_info,
                                                                model: selectedModelId,
                                                                ...(constraints && {
                                                                    max_tokens: Math.min(
                                                                        currentNodeConfig.llm_info?.max_tokens || constraints.max_tokens,
                                                                        constraints.max_tokens
                                                                    ),
                                                                    temperature: Math.min(
                                                                        Math.max(currentNodeConfig.llm_info?.temperature || 0.7, constraints.min_temperature),
                                                                        constraints.max_temperature
                                                                    ),
                                                                }),
                                                            },
                                                        }
                                                        currentNodeConfig = updatedModel
                                                        flowStore.updateNodeConfigOnly(nodeID, updatedModel)
                                                    }}
                                                >
                                                    {#each Object.entries(groupModelsByProvider(fieldMeta.enum)) as [provider, models]}
                                                        {#if models.length > 0}
                                                            <optgroup label={provider}>
                                                                {#each models as modelId}
                                                                    <option value={modelId}>{modelId.replace('ollama/', '')}</option>
                                                                {/each}
                                                            </optgroup>
                                                        {/if}
                                                    {/each}
                                                </select>
                                            </label>
                                        {:else}
                                            <label class="block text-xs font-medium text-foreground-500 mb-1">
                                                {fieldMeta?.title || key}
                                                <select
                                                    class="w-full text-sm px-2 py-1.5 rounded border border-default-200 bg-background focus:outline-none"
                                                    value={value || fieldMeta?.default || ''}
                                                    disabled={readOnly}
                                                    onchange={(e) => handleInputChange(key, e.currentTarget.value)}
                                                >
                                                    {#each fieldMeta.enum as option}
                                                        <option value={option}>{option}</option>
                                                    {/each}
                                                </select>
                                            </label>
                                        {/if}
                                    </div>
                                <!-- Template/message fields - use TextEditor -->
                                {:else if isTemplateField(key, fieldMeta)}
                                    <div class="my-3">
                                        <div class="flex items-center gap-2 mb-2">
                                            <h3 class="font-semibold text-sm">{fieldMeta?.title || key}</h3>
                                        </div>
                                        <TextEditor
                                            {nodeID}
                                            fieldName={key}
                                            inputSchema={incomingSchema}
                                            fieldTitle={key}
                                            content={currentNodeConfig[key] || ''}
                                            setContent={(v) => handleInputChange(key, v)}
                                            disableFormatting={key.endsWith('_template')}
                                            isTemplateEditor={true}
                                            {readOnly}
                                            enableAIGeneration={key === 'system_message' || key === 'user_message'}
                                            messageType={key === 'system_message' ? 'system' : 'user'}
                                        />
                                        {#if key === 'user_message'}
                                            <div class="mt-4">
                                                <FewShotExamplesEditor
                                                    {nodeID}
                                                    examples={nodeConfig?.few_shot_examples || []}
                                                    onChange={(examples) => {
                                                        flowStore.updateNodeConfigOnly(nodeID, { ...nodeConfig, few_shot_examples: examples })
                                                    }}
                                                    {readOnly}
                                                />
                                            </div>
                                        {/if}
                                    </div>
                                <!-- Number field with slider -->
                                {:else if typeof field === 'number' || typeof value === 'number' || fieldMeta?.type === 'number' || fieldMeta?.type === 'integer'}
                                    {#if fieldMeta && (fieldMeta.minimum !== undefined || fieldMeta.maximum !== undefined || (key === 'temperature' && currentModelConstraints) || (key === 'max_tokens' && currentModelConstraints))}
                                        {@const min = (key === 'temperature' && currentModelConstraints) ? currentModelConstraints.min_temperature : (fieldMeta?.minimum ?? 0)}
                                        {@const max = (key === 'max_tokens' && currentModelConstraints) ? currentModelConstraints.max_tokens : ((key === 'temperature' && currentModelConstraints) ? currentModelConstraints.max_temperature : (fieldMeta?.maximum ?? 100))}
                                        {@const disabled = (key === 'max_tokens' && currentModelConstraints && !currentModelConstraints.supports_max_tokens) || (key === 'temperature' && currentModelConstraints && !currentModelConstraints.supports_temperature) || readOnly}
                                        <div class="my-3">
                                            <div class="flex justify-between items-center mb-1">
                                                <label for="range-{key}" class="font-semibold text-sm">{fieldMeta?.title || key}</label>
                                                <span class="text-sm">{value}</span>
                                            </div>
                                            <input
                                                id="range-{key}"
                                                type="range"
                                                class="w-full accent-primary"
                                                value={value}
                                                {min}
                                                {max}
                                                step={fieldMeta?.type === 'integer' ? 1 : 0.1}
                                                disabled={disabled}
                                                oninput={(e) => handleInputChange(key, parseFloat(e.currentTarget.value), true)}
                                            />
                                        </div>
                                    {:else}
                                        <div class="my-3">
                                            <label class="block text-xs font-medium text-foreground-500 mb-1">
                                                {fieldMeta?.title || key}
                                                <input
                                                    type="number"
                                                    class="w-full text-sm px-3 py-2 rounded-lg border border-default-200 bg-background focus:outline-none"
                                                    value={value}
                                                    disabled={readOnly}
                                                    onchange={(e) => handleInputChange(key, parseFloat(e.currentTarget.value) || 0)}
                                                />
                                            </label>
                                        </div>
                                    {/if}
                                <!-- Boolean field -->
                                {:else if typeof field === 'boolean' || typeof value === 'boolean' || fieldMeta?.type === 'boolean'}
                                    <div class="my-3">
                                        <div class="flex justify-between items-center">
                                            <span class="font-semibold text-sm">{fieldMeta?.title || key}</span>
                                            <button
                                                type="button"
                                                role="switch"
                                                aria-checked={!!value}
                                                aria-label={fieldMeta?.title || key}
                                                class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors {value ? 'bg-primary' : 'bg-default-200'} disabled:opacity-50"
                                                disabled={readOnly}
                                                onclick={() => handleInputChange(key, !value)}
                                            >
                                                <span class="inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform {value ? 'translate-x-6' : 'translate-x-1'}"></span>
                                            </button>
                                        </div>
                                    </div>
                                <!-- String field -->
                                {:else if typeof value === 'string' || typeof field === 'string' || fieldMeta?.type === 'string'}
                                    <div class="my-3">
                                        <label class="block text-xs font-medium text-foreground-500 mb-1">
                                            {fieldMeta?.title || key}{fieldMeta?.required ? ' *' : ''}
                                            <textarea
                                                class="w-full text-sm px-3 py-2 rounded-lg border border-default-200 bg-background focus:outline-none resize-y min-h-[60px] disabled:opacity-50"
                                                value={value || ''}
                                                disabled={readOnly}
                                                onchange={(e) => handleInputChange(key, e.currentTarget.value)}
                                                placeholder="Enter your input"
                                            ></textarea>
                                        </label>
                                    </div>
                                <!-- AskNode: models list -->
                                {:else if key === 'models' && nodeType === 'AskNode'}
                                    <div class="my-3">
                                        <div class="flex items-center gap-2 mb-2">
                                            <h3 class="font-semibold text-sm">Models</h3>
                                            <span class="text-xs text-foreground-400">{(value as any[])?.length ?? 0} configured</span>
                                        </div>
                                        <ModelListEditor
                                            models={value ?? []}
                                            availableModels={availableModelIds}
                                            onChange={(updated) => handleInputChange('models', updated)}
                                            {readOnly}
                                        />
                                    </div>
                                <!-- Object field — recurse (simplified) -->
                                {:else if typeof value === 'object' && value !== null && !Array.isArray(value)}
                                    <div class="my-2">
                                        {#each Object.keys(field || value) as subKey}
                                            {@const subValue = value?.[subKey]}
                                            {@const subMeta = getFieldMetadata(`${nodeType}.config.${key}.${subKey}`) as FieldMetadata}
                                            <div class="my-2">
                                                {#if subMeta?.enum}
                                                    <label class="block text-xs font-medium text-foreground-500 mb-1">
                                                        {subMeta?.title || subKey}
                                                        <select
                                                            class="w-full text-sm px-2 py-1.5 rounded border border-default-200 bg-background"
                                                            value={subValue || subMeta?.default || ''}
                                                            disabled={readOnly}
                                                            onchange={(e) => handleInputChange(`${key}.${subKey}`, e.currentTarget.value)}
                                                        >
                                                            {#each subMeta.enum as opt}
                                                                <option value={opt}>{opt}</option>
                                                            {/each}
                                                        </select>
                                                    </label>
                                                {:else if typeof subValue === 'boolean'}
                                                    <span class="block text-xs font-medium text-foreground-500 mb-1">{subMeta?.title || subKey}</span>
                                                    <button
                                                        type="button"
                                                        role="switch"
                                                        aria-checked={!!subValue}
                                                        aria-label={subMeta?.title || subKey}
                                                        class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors {subValue ? 'bg-primary' : 'bg-default-200'}"
                                                        disabled={readOnly}
                                                        onclick={() => handleInputChange(`${key}.${subKey}`, !subValue)}
                                                    >
                                                        <span class="inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform {subValue ? 'translate-x-6' : 'translate-x-1'}"></span>
                                                    </button>
                                                {:else if typeof subValue === 'number'}
                                                    <label class="block text-xs font-medium text-foreground-500 mb-1">
                                                        {subMeta?.title || subKey}
                                                        <input
                                                            type="number"
                                                            class="w-full text-sm px-3 py-2 rounded-lg border border-default-200 bg-background"
                                                            value={subValue}
                                                            disabled={readOnly}
                                                            onchange={(e) => handleInputChange(`${key}.${subKey}`, parseFloat(e.currentTarget.value) || 0)}
                                                        />
                                                    </label>
                                                {:else}
                                                    <label class="block text-xs font-medium text-foreground-500 mb-1">
                                                        {subMeta?.title || subKey}
                                                        <input
                                                            type="text"
                                                            class="w-full text-sm px-3 py-2 rounded-lg border border-default-200 bg-background"
                                                            value={subValue || ''}
                                                            disabled={readOnly}
                                                            onchange={(e) => handleInputChange(`${key}.${subKey}`, e.currentTarget.value)}
                                                        />
                                                    </label>
                                                {/if}
                                            </div>
                                        {/each}
                                    </div>
                                {/if}

                                <!-- URL variable config + Message history config (after message fields) -->
                                {#if keyIndex === messageHistoryInsertIndex}
                                    <!-- URL variable config for Gemini models -->
                                    {#if currentNodeConfig?.llm_info?.model?.startsWith?.('gemini')}
                                        <div class="my-3">
                                            <div class="flex items-center gap-2 mb-2">
                                                <h3 class="font-semibold text-sm">File Input</h3>
                                            </div>
                                            <select
                                                class="w-full text-sm px-2 py-1.5 rounded border border-default-200 bg-background focus:outline-none"
                                                value={currentNodeConfig?.url_variables?.file || ''}
                                                disabled={readOnly}
                                                onchange={(e) => {
                                                    const v = e.currentTarget.value
                                                    handleInputChange('url_variables', v ? { file: v } : {})
                                                }}
                                            >
                                                <option value="">None</option>
                                                {#each incomingSchema as variable}
                                                    <option value={variable}>{variable}</option>
                                                {/each}
                                            </select>
                                        </div>
                                    {/if}
                                    {#if (nodeType === 'SingleLLMCallNode' || nodeType === 'AgentNode')}
                                        <div class="my-3">
                                            <div class="flex items-center gap-2 mb-2">
                                                <h3 class="font-semibold text-sm">Message History</h3>
                                            </div>
                                            <div class="flex items-center gap-3 mb-2">
                                                <button
                                                    type="button"
                                                    role="switch"
                                                    aria-checked={!!currentNodeConfig.enable_message_history}
                                                    aria-label="Enable Message History"
                                                    class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors {currentNodeConfig.enable_message_history ? 'bg-primary' : 'bg-default-200'}"
                                                    onclick={() => handleInputChange('enable_message_history', !currentNodeConfig.enable_message_history)}
                                                >
                                                    <span class="inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform {currentNodeConfig.enable_message_history ? 'translate-x-6' : 'translate-x-1'}"></span>
                                                </button>
                                                <span class="text-sm">Enable Message History</span>
                                            </div>
                                            {#if currentNodeConfig.enable_message_history}
                                                <select
                                                    class="w-full text-sm px-2 py-1.5 rounded border border-default-200 bg-background"
                                                    value={currentNodeConfig.message_history_variable || ''}
                                                    onchange={(e) => handleInputChange('message_history_variable', e.currentTarget.value)}
                                                >
                                                    <option value="">None</option>
                                                    {#each incomingSchema as variable}
                                                        <option value={variable}>{variable}</option>
                                                    {/each}
                                                </select>
                                            {/if}
                                        </div>
                                    {/if}
                                {/if}

                                {#if !isLast}
                                    <hr class="border-default-200" />
                                {/if}
                            {/if}
                        {/each}
                    {/if}
                </div>
            {/if}
        </div>
    {/if}
{/snippet}

{#if embedded}
    <!-- Embedded: render content directly without fixed positioning -->
    <div class="px-5 py-4 overflow-auto h-full">
        {@render sidebarContent()}
    </div>
{:else}
    <!-- Standalone: fixed right-side overlay panel -->
    <div
        class="fixed top-16 bottom-4 rounded-xl border border-solid border-default-200 dark:border-default-100 overflow-auto bg-background/70 dark:bg-default-100/50 z-20"
        style="width: {width}px; right: {rightOffset}px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); backdrop-filter: blur(8px);"
    >
        <!-- Resize handle -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
            class="absolute left-0 top-0 h-full w-1 cursor-ew-resize hover:bg-primary/50 z-10 {isResizing ? 'bg-primary' : ''}"
            onmousedown={handleMouseDown}
        ></div>

        <div class="px-6 py-4 overflow-auto max-h-screen">
            <!-- Header -->
            <div class="flex justify-between items-center mb-3">
                <div>
                    <h1 class="text-lg font-semibold">{nodeConfig?.title || node?.id || 'Node Details'}</h1>
                    <h2 class="text-xs text-foreground-500">{nodeType}</h2>
                </div>
                <button
                    type="button"
                    class="p-1.5 rounded-full hover:bg-default-100"
                    onclick={() => flowStore.setSelectedNode(null)}
                >
                    <Icon icon="solar:close-circle-linear" class="text-foreground-500" width={22} />
                </button>
            </div>

            {@render sidebarContent()}
        </div>
    </div>
{/if}
