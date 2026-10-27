<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import Icon from '@iconify/svelte'

    interface ModelInfo {
        model: string
        max_tokens: number | null
        temperature: number | null
        top_p: number | null
    }

    interface Props {
        models: ModelInfo[]
        availableModels: string[]
        onChange: (models: ModelInfo[]) => void
        readOnly?: boolean
    }

    let { models, availableModels, onChange, readOnly = false }: Props = $props()

    let expandedIndex = $state<number | null>(0)

    function providerGroups(ids: string[]) {
        const groups: Record<string, string[]> = {
            OpenAI: [],
            Anthropic: [],
            Google: [],
            Deepseek: [],
            'IFM K2 Horizon': [],
            'IFM Jais 3': [],
            Ollama: [],
        }
        for (const id of ids) {
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

    function shortName(modelId: string) {
        return modelId.replace(/^(openai|anthropic|gemini|deepseek|ifm|ollama)\//, '')
    }

    function addModel() {
        if (readOnly) return
        const newModel: ModelInfo = {
            model: availableModels[0] ?? 'openai/gpt-4o',
            max_tokens: 16384,
            temperature: 0.7,
            top_p: 0.9,
        }
        onChange([...models, newModel])
        expandedIndex = models.length
    }

    function removeModel(i: number) {
        if (readOnly) return
        onChange(models.filter((_, idx) => idx !== i))
        if (expandedIndex === i) expandedIndex = null
        else if (expandedIndex !== null && expandedIndex > i) expandedIndex--
    }

    function patch(i: number, key: keyof ModelInfo, val: any) {
        if (readOnly) return
        onChange(models.map((m, idx) => (idx === i ? { ...m, [key]: val } : m)))
    }

    function toggle(i: number) {
        expandedIndex = expandedIndex === i ? null : i
    }
</script>

<div class="space-y-2">
    {#each models as model, i}
        {@const isOpen = expandedIndex === i}
        <div class="border border-default-200 rounded-lg bg-default-50">
            <!-- Header row -->
            <div class="flex items-center justify-between px-3 py-2">
                <button
                    type="button"
                    class="flex items-center gap-2 flex-1 min-w-0 text-left"
                    onclick={() => toggle(i)}
                    disabled={readOnly}
                >
                    <Icon
                        icon={isOpen ? 'solar:alt-arrow-up-linear' : 'solar:alt-arrow-down-linear'}
                        width={16}
                    />
                    <span class="text-sm font-medium truncate">{shortName(model.model)}</span>
                    {#if !isOpen}
                        <span class="text-xs text-foreground-400 shrink-0">
                            t={model.temperature ?? '—'} · max={model.max_tokens ?? '—'}
                        </span>
                    {/if}
                </button>
                {#if !readOnly}
                    <button
                        type="button"
                        class="ml-2 p-1 rounded text-destructive hover:bg-destructive/10 shrink-0"
                        onclick={() => removeModel(i)}
                        title="Remove model"
                    >
                        <Icon icon="solar:trash-bin-trash-linear" width={16} />
                    </button>
                {/if}
            </div>

            <!-- Expanded editor -->
            {#if isOpen}
                <div class="px-3 pb-3 space-y-3 border-t border-default-200 pt-3">
                    <!-- Model select -->
                    <label class="block text-xs font-medium text-foreground-500">
                        Model
                        <select
                            class="mt-1 w-full text-sm px-2 py-1.5 rounded border border-default-200 bg-background focus:outline-none disabled:opacity-50"
                            value={model.model}
                            disabled={readOnly}
                            onchange={(e) => patch(i, 'model', e.currentTarget.value)}
                        >
                            {#each Object.entries(providerGroups(availableModels)) as [provider, ids]}
                                {#if ids.length > 0}
                                    <optgroup label={provider}>
                                        {#each ids as id}
                                            <option value={id}>{shortName(id)}</option>
                                        {/each}
                                    </optgroup>
                                {/if}
                            {/each}
                        </select>
                    </label>

                    <!-- Max tokens -->
                    <div>
                        <div class="flex justify-between items-center mb-1">
                            <span class="text-xs font-medium text-foreground-500">Max Tokens</span>
                            <span class="text-xs">{model.max_tokens ?? '—'}</span>
                        </div>
                        <input
                            type="range"
                            min={1}
                            max={65536}
                            step={512}
                            value={model.max_tokens ?? 16384}
                            disabled={readOnly}
                            class="w-full accent-primary"
                            oninput={(e) => patch(i, 'max_tokens', parseInt(e.currentTarget.value))}
                        />
                    </div>

                    <!-- Temperature -->
                    <div>
                        <div class="flex justify-between items-center mb-1">
                            <span class="text-xs font-medium text-foreground-500">Temperature</span>
                            <span class="text-xs">{model.temperature ?? '—'}</span>
                        </div>
                        <input
                            type="range"
                            min={0}
                            max={1}
                            step={0.05}
                            value={model.temperature ?? 0.7}
                            disabled={readOnly}
                            class="w-full accent-primary"
                            oninput={(e) => patch(i, 'temperature', parseFloat(e.currentTarget.value))}
                        />
                    </div>

                    <!-- Top-p -->
                    <div>
                        <div class="flex justify-between items-center mb-1">
                            <span class="text-xs font-medium text-foreground-500">Top P</span>
                            <span class="text-xs">{model.top_p ?? '—'}</span>
                        </div>
                        <input
                            type="range"
                            min={0}
                            max={1}
                            step={0.05}
                            value={model.top_p ?? 0.9}
                            disabled={readOnly}
                            class="w-full accent-primary"
                            oninput={(e) => patch(i, 'top_p', parseFloat(e.currentTarget.value))}
                        />
                    </div>
                </div>
            {/if}
        </div>
    {/each}

    {#if !readOnly}
        <button
            type="button"
            class="w-full flex items-center justify-center gap-2 p-2.5 border-2 border-dashed border-default-200 rounded-lg text-sm hover:border-primary hover:text-primary transition-colors"
            onclick={addModel}
        >
            <Icon icon="solar:add-circle-linear" width={16} />
            Add Model
        </button>
    {/if}
</div>
