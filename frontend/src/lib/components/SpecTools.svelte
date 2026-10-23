<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { onMount } from 'svelte'
    import { toast } from 'svelte-sonner'
    import { listOpenAPISpecs, deleteOpenAPISpec, createOpenAPISpec } from '$lib/utils/api'
    import { parseOpenAPISpec } from '$lib/utils/openApiParser'
    import { Button } from '$lib/components/ui/button'
    import CodeEditor from '$lib/components/textEditor/CodeEditor.svelte'
    import type { OpenAPISpec } from '$lib/types/openapi'

    let selectedTab = $state<'create' | 'registered'>('create')
    let specs = $state<OpenAPISpec[]>([])
    let isLoading = $state(false)
    let expandedSpecId = $state<string | null>(null)

    // Create tab state
    let jsonInput = $state('')
    let parsedSpec = $state<any>(null)
    let parseError = $state<string | null>(null)
    let endpoints = $state<any[]>([])

    onMount(() => {
        fetchSpecs()
    })

    async function fetchSpecs() {
        try {
            isLoading = true
            const raw = await listOpenAPISpecs()
            specs = raw.map((spec: any) => {
                const result = parseOpenAPISpec(spec.raw_spec)
                return { ...spec, endpoints: result.endpoints }
            })
        } catch {
            toast.error('Failed to load registered specifications')
        } finally {
            isLoading = false
        }
    }

    async function handleDelete(specId: string) {
        try {
            await deleteOpenAPISpec(specId)
            toast.success('Specification deleted')
            await fetchSpecs()
        } catch {
            toast.error('Failed to delete specification')
        }
    }

    function handleParse() {
        const result = parseOpenAPISpec(jsonInput)
        endpoints = result.endpoints
        parseError = result.error ?? null
        if (!parseError) {
            try {
                parsedSpec = JSON.parse(jsonInput)
            } catch {
                parsedSpec = null
                parseError = 'Invalid JSON'
            }
        } else {
            parsedSpec = null
        }
    }

    async function handleCreateSpec() {
        if (!parsedSpec) return
        try {
            await createOpenAPISpec(parsedSpec)
            toast.success('OpenAPI specification stored successfully!')
            jsonInput = ''
            parsedSpec = null
            endpoints = []
            parseError = null
        } catch {
            toast.error('Failed to store OpenAPI specification')
        }
    }
</script>

<div class="w-full">
    <!-- Tabs -->
    <div class="flex gap-1 mb-6 border-b border-border">
        {#each [{ key: 'create', label: 'Create New' }, { key: 'registered', label: 'Registered' }] as tab}
            <button
                onclick={() => (selectedTab = tab.key as any)}
                class="px-4 py-2 text-sm font-medium border-b-2 transition-colors
                    {selectedTab === tab.key
                        ? 'border-primary text-primary'
                        : 'border-transparent text-muted-foreground hover:text-foreground'}"
            >
                {tab.label}
            </button>
        {/each}
    </div>

    {#if selectedTab === 'create'}
        <div class="border border-border rounded-xl p-6 space-y-4">
            <div>
                <h3 class="text-lg font-semibold mb-1">Store OpenAPI Specification</h3>
                <p class="text-sm text-muted-foreground">Parse and store OpenAPI specifications</p>
            </div>

            <div class="min-h-[200px]">
                <CodeEditor
                    code={jsonInput}
                    onChange={(v) => (jsonInput = v)}
                    mode="json"
                    label="OpenAPI Specification (JSON)"
                />
            </div>

            {#if parseError}
                <div class="text-sm text-destructive p-3 rounded-lg bg-destructive/10">{parseError}</div>
            {/if}

            {#if endpoints.length > 0 && !parseError}
                <div class="border border-border rounded-lg p-4">
                    <p class="text-sm font-medium mb-2">{endpoints.length} endpoints parsed</p>
                    <div class="space-y-1 max-h-40 overflow-y-auto">
                        {#each endpoints as ep}
                            <div class="text-xs flex gap-2">
                                <span class="font-mono font-bold text-primary uppercase">{ep.method}</span>
                                <span class="font-mono text-muted-foreground">{ep.path}</span>
                            </div>
                        {/each}
                    </div>
                </div>
            {/if}

            <div class="flex gap-3">
                <Button variant="outline" onclick={handleParse} disabled={!jsonInput.trim()}>
                    Parse Spec
                </Button>
                {#if parsedSpec}
                    <Button onclick={handleCreateSpec}>Store Specification</Button>
                {/if}
            </div>
        </div>
    {:else}
        {#if isLoading}
            <div class="flex justify-center py-8">
                <div class="animate-spin h-6 w-6 border-2 border-primary border-t-transparent rounded-full"></div>
            </div>
        {:else if specs.length === 0}
            <div class="text-center py-8 text-muted-foreground text-sm">No registered specifications found</div>
        {:else}
            <div class="space-y-4">
                {#each specs as spec}
                    <div class="border border-border rounded-xl overflow-hidden">
                        <div class="flex items-start justify-between px-4 py-3 bg-muted/30">
                            <div>
                                <h3 class="font-semibold">{spec.name}</h3>
                                <p class="text-xs text-muted-foreground">Version: {spec.version}</p>
                            </div>
                            <div class="flex gap-2">
                                <button
                                    onclick={() => (expandedSpecId = expandedSpecId === spec.id ? null : spec.id)}
                                    class="text-xs px-3 py-1 rounded border border-border hover:bg-muted transition-colors"
                                >
                                    {expandedSpecId === spec.id ? 'Collapse' : 'Expand'}
                                </button>
                                <button
                                    onclick={() => handleDelete(spec.id)}
                                    class="text-xs px-3 py-1 rounded border border-destructive text-destructive hover:bg-destructive/10 transition-colors"
                                >
                                    Delete
                                </button>
                            </div>
                        </div>

                        {#if expandedSpecId === spec.id}
                            <div class="p-4 space-y-2 border-t border-border">
                                {#if spec.endpoints?.length > 0}
                                    {#each spec.endpoints as ep}
                                        <div class="text-xs flex gap-2 items-center">
                                            <span class="font-mono font-bold text-primary uppercase w-12">{ep.method}</span>
                                            <span class="font-mono text-muted-foreground">{ep.path}</span>
                                            {#if ep.summary}
                                                <span class="text-muted-foreground">— {ep.summary}</span>
                                            {/if}
                                        </div>
                                    {/each}
                                {:else}
                                    <p class="text-sm text-muted-foreground">No endpoints found</p>
                                {/if}
                            </div>
                        {/if}
                    </div>
                {/each}
            </div>
        {/if}
    {/if}
</div>
