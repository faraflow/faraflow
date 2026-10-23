<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import NodeStatusCard from '$lib/components/canvas/NodeStatusCard.svelte'

    interface ModelInfo {
        model: string
    }

    interface Props {
        nodeConfig: Record<string, any>
        nodeData: Record<string, any>
        grow?: boolean
    }

    let { nodeConfig, nodeData, grow = false }: Props = $props()

    // ── helpers ────────────────────────────────────────────────────────────────

    function modelSlug(model: string): string {
        return model.split('/').pop()!.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '')
    }

    function fieldId(prefix: string, model: string): string {
        return `${prefix}_${modelSlug(model)}`
    }

    function makeAcronym(id: string): string {
        return id.split('_').map(s => s[0] ?? '').join('').toUpperCase().slice(0, 4)
    }

    function providerColor(model: string): string {
        const m = model.toLowerCase()
        if (m.includes('gpt') || m.includes('o1') || m.includes('o3') || m.includes('openai')) return '#28A745'
        if (m.includes('claude') || m.includes('anthropic')) return '#FD7E14'
        if (m.includes('gemini') || m.includes('google')) return '#007BFF'
        if (m.includes('llama') || m.includes('meta')) return '#6F42C1'
        if (m.includes('mistral')) return '#20C997'
        return '#17A2B8'
    }

    function modelLabel(model: string): string {
        return model.split('/').pop() ?? model
    }

    // ── derived state ──────────────────────────────────────────────────────────

    type StatusKey = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'

    const taskStatus = $derived<string>(nodeData?.taskStatus ?? 'PENDING')
    const subOut     = $derived<Record<string, any>>(nodeData?.subworkflow_output ?? {})
    const subErrors  = $derived<Record<string, string>>(nodeData?.subworkflow_errors ?? {})
    const models     = $derived<ModelInfo[]>(nodeConfig?.models ?? [])
    const prefix     = $derived<string>(nodeConfig?.output_key_prefix ?? 'ask')

    interface ModelRow {
        id: string
        fakeNode: any
        statusKey: StatusKey
        output: any
        error: string | null
    }

    const rows = $derived<ModelRow[]>(
        models.map((m) => {
            const id        = fieldId(prefix, m.model)
            const hasOutput = id in subOut
            let statusKey: StatusKey
            if (hasOutput)                       statusKey = 'COMPLETED'
            else if (taskStatus === 'RUNNING')   statusKey = 'RUNNING'
            else if (taskStatus === 'FAILED')    statusKey = 'FAILED'
            else if (taskStatus === 'COMPLETED') statusKey = 'FAILED'
            else                                 statusKey = 'PENDING'

            return {
                id,
                fakeNode: {
                    id,
                    type: 'SingleLLMCallNode',
                    data: {
                        color: providerColor(m.model),
                        acronym: makeAcronym(id),
                        title: modelLabel(m.model),
                        taskStatus: statusKey,
                        error: subErrors[id] ?? null,
                    },
                },
                statusKey,
                output: subOut[id] ?? null,
                error: subErrors[id] ?? null,
            }
        })
    )

    let expandedId = $state<string | null>(null)

    function toggleExpand(id: string) {
        expandedId = expandedId === id ? null : id
    }

    function outputText(output: any): string {
        if (!output) return ''
        return typeof output === 'object' ? JSON.stringify(output, null, 2) : String(output)
    }
</script>

{#if models.length === 0}
    <p class="text-sm text-muted-foreground text-center py-4">No models configured.</p>
{:else if taskStatus !== 'PENDING'}
    <div class="rows" class:rows--grow={grow}>
        {#each rows as row (row.id)}
            {@const hasContent = !!(row.output || row.error)}
            {#if hasContent}
                <NodeStatusCard
                    node={row.fakeNode}
                    isSelected={expandedId === row.id}
                    onclick={() => toggleExpand(row.id)}
                >
                    {#if row.error}
                        <pre class="output-pre output-pre--error">{row.error}</pre>
                    {:else}
                        <pre class="output-pre">{outputText(row.output)}</pre>
                    {/if}
                </NodeStatusCard>
            {:else}
                <NodeStatusCard
                    node={row.fakeNode}
                    isSelected={false}
                    onclick={() => {}}
                />
            {/if}
        {/each}
    </div>
{/if}

<style>
    .rows {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }

    .rows--grow {
        flex: 1;
        overflow-y: auto;
    }

    .output-pre {
        font-size: 0.7rem;
        white-space: pre-wrap;
        word-break: break-word;
        color: #374151;
        margin: 0;
        max-height: 240px;
        overflow-y: auto;

        &--error {
            color: rgb(185, 28, 28);
        }
    }
</style>
