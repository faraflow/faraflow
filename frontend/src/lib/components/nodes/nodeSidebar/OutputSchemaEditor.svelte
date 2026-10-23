<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { onMount } from 'svelte'
    import Icon from '@iconify/svelte'
    import { extractSchemaFromJsonSchema, generateJsonSchemaFromSchema } from '$lib/utils/schemaUtils'
    import { jsonOptions } from '$lib/constants/jsonOptions'
    import SchemaEditor from './SchemaEditor.svelte'
    import CodeEditor from '$lib/components/textEditor/CodeEditor.svelte'
    import { generateSchema } from '$lib/utils/api'
    import { apiKeyStatus } from '$lib/stores/apiKeyStatus.svelte'

    interface Props {
        nodeID: string
        schema: string
        readOnly?: boolean
        error?: string
        onChange: (newSchema: string) => void
    }

    let { nodeID, schema, readOnly = false, error = '', onChange }: Props = $props()

    const parsedSchema = $derived(extractSchemaFromJsonSchema(schema || '').schema)

    let selectedTab = $state('simple')
    $effect(() => { if (error) selectedTab = 'json' })
    let isGenerating = $state(false)
    let description = $state('')
    let generationError = $state('')
    let hasOpenAIKey = $state(false)
    let generationType = $state<'new' | 'enhance'>('new')
    let isAIModalOpen = $state(false)

    // Check for OpenAI key
    onMount(async () => {
        try {
            await apiKeyStatus.ensureLoaded()
            hasOpenAIKey = apiKeyStatus.isConfigured('OPENAI_API_KEY')
        } catch {
            hasOpenAIKey = false
        }
    })

    function handleSchemaEditorChange(newValue: any) {
        if (readOnly) return
        if (typeof newValue === 'object' && !('type' in newValue)) {
            const jsonSchema = generateJsonSchemaFromSchema(newValue)
            if (jsonSchema) onChange(jsonSchema)
        } else {
            onChange(JSON.stringify(newValue, null, 2))
        }
    }

    async function handleGenerateSchema() {
        if (!description.trim()) {
            generationError = 'Please enter a description'
            return
        }
        isGenerating = true
        generationError = ''
        try {
            const result = await generateSchema(description, generationType === 'enhance' ? schema : undefined)
            onChange(JSON.stringify(result, null, 2))
            isAIModalOpen = false
            description = ''
            generationType = 'new'
        } catch (e: any) {
            generationError = e?.message || 'Failed to generate schema'
        } finally {
            isGenerating = false
        }
    }
</script>

<div>
    {#if error}
        <div class="flex items-center gap-2 text-sm text-destructive bg-destructive/10 px-3 py-2 rounded-lg mb-2">
            {error}
        </div>
    {/if}

    <!-- Tab bar -->
    <div class="flex border-b border-default-200 mb-2">
        {#each [['simple', 'Simple'], ['json', 'JSON Schema']] as [key, label]}
            <button
                type="button"
                class="px-3 py-1.5 text-sm border-b-2 -mb-px {selectedTab === key
                    ? 'border-primary text-primary font-medium'
                    : 'border-transparent text-foreground-500 hover:text-foreground'} disabled:opacity-50"
                disabled={readOnly}
                onclick={() => selectedTab = key}
            >
                {label}
            </button>
        {/each}
        {#if !readOnly && hasOpenAIKey}
            <button
                type="button"
                class="px-3 py-1.5 text-sm border-b-2 -mb-px border-transparent text-foreground-500 hover:text-foreground flex items-center gap-1"
                onclick={() => isAIModalOpen = true}
            >
                <Icon icon="solar:magic-stick-3-linear" width={14} />
                AI Generate
            </button>
        {/if}
    </div>

    <!-- Simple tab -->
    {#if selectedTab === 'simple'}
        <div class="border border-default-200 rounded-lg p-3 bg-default-50">
            {#if parsedSchema}
                <SchemaEditor
                    jsonValue={parsedSchema}
                    onChange={handleSchemaEditorChange}
                    options={jsonOptions}
                    nodeId={nodeID}
                    {readOnly}
                />
            {:else}
                <p class="text-sm text-foreground-500">No schema defined. Switch to JSON Schema tab to add one.</p>
            {/if}
        </div>
    {/if}

    <!-- JSON tab -->
    {#if selectedTab === 'json'}
        <div class="border border-default-200 rounded-lg overflow-hidden">
            <CodeEditor
                code={schema || ''}
                mode="json"
                onChange={(v) => { if (!readOnly) onChange(v) }}
                {readOnly}
                height="200px"
                label=""
            />
        </div>
    {/if}
</div>

<!-- AI Generation Modal -->
{#if isAIModalOpen}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        onclick={(e) => { if (e.target === e.currentTarget && !isGenerating) isAIModalOpen = false }}
    >
        <div class="bg-background rounded-xl shadow-xl w-[90vw] max-w-2xl flex flex-col max-h-[90vh]">
            <div class="flex items-center justify-between px-6 py-4 border-b">
                <h2 class="text-lg font-semibold">Generate Schema</h2>
                {#if !isGenerating}
                    <button type="button" class="p-1 rounded hover:bg-default-100" onclick={() => isAIModalOpen = false}>
                        <Icon icon="solar:close-circle-linear" width={20} />
                    </button>
                {/if}
            </div>
            <div class="flex-1 overflow-auto p-6 space-y-4">
                <div class="flex gap-4">
                    <label class="flex items-center gap-2 cursor-pointer">
                        <input type="radio" bind:group={generationType} value="new" disabled={isGenerating} />
                        <span class="text-sm">Create New Schema</span>
                    </label>
                    <label class="flex items-center gap-2 cursor-pointer {!schema ? 'opacity-50 pointer-events-none' : ''}">
                        <input type="radio" bind:group={generationType} value="enhance" disabled={isGenerating || !schema} />
                        <span class="text-sm">Enhance Existing Schema</span>
                    </label>
                </div>

                {#if generationType === 'enhance' && schema}
                    <div class="border border-default-200 rounded-lg overflow-hidden">
                        <CodeEditor code={schema} mode="json" readOnly={true} height="120px" onChange={() => {}} label="" />
                    </div>
                {/if}

                <div>
                    <label class="block text-sm font-medium mb-1">
                        {generationType === 'new' ? 'Describe the schema you want to generate' : 'Describe how to enhance'}
                        <textarea
                            class="w-full rounded-lg border border-default-200 bg-default-50 px-3 py-2 text-sm resize-y min-h-[80px] focus:outline-none focus:border-primary"
                            placeholder={generationType === 'new'
                                ? 'Example: A user profile with name, email, age'
                                : 'Example: Add a phone number field'}
                            bind:value={description}
                            disabled={isGenerating}
                        ></textarea>
                    </label>
                </div>

                {#if generationError}
                    <div class="text-sm text-destructive bg-destructive/10 px-3 py-2 rounded-lg">
                        {generationError}
                    </div>
                {/if}
            </div>
            <div class="flex justify-end gap-2 px-6 py-4 border-t">
                <button
                    type="button"
                    class="px-4 py-2 rounded-lg border hover:bg-default-100 text-sm"
                    disabled={isGenerating}
                    onclick={() => isAIModalOpen = false}
                >
                    Cancel
                </button>
                <button
                    type="button"
                    class="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm hover:opacity-90 flex items-center gap-2 disabled:opacity-50"
                    disabled={isGenerating}
                    onclick={handleGenerateSchema}
                >
                    {#if isGenerating}
                        <Icon icon="svg-spinners:ring-resize" width={16} />
                        Generating...
                    {:else}
                        <Icon icon="solar:magic-stick-3-linear" width={16} />
                        Generate
                    {/if}
                </button>
            </div>
        </div>
    </div>
{/if}
