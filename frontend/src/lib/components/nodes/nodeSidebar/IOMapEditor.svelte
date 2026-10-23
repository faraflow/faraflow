<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import Icon from '@iconify/svelte'

    interface Props {
        leftOptions: string[]
        rightOptions: string[]
        value: Record<string, string>
        onChange: (value: Record<string, string>) => void
        readOnly?: boolean
        leftLabel?: string
        rightLabel?: string
    }

    let {
        leftOptions,
        rightOptions,
        value = {},
        onChange,
        readOnly = false,
        leftLabel = 'Input',
        rightLabel = 'Output',
    }: Props = $props()

    let newLeftKey = $state('')

    function addMapping() {
        if (!newLeftKey || value.hasOwnProperty(newLeftKey)) return
        onChange({ ...value, [newLeftKey]: rightOptions[0] || '' })
        newLeftKey = ''
    }

    function updateMapping(leftKey: string, rightValue: string) {
        onChange({ ...value, [leftKey]: rightValue })
    }

    function deleteMapping(leftKey: string) {
        const { [leftKey]: _, ...rest } = value
        onChange(rest)
    }

    const unusedLeftOptions = $derived(leftOptions.filter((o) => !value.hasOwnProperty(o)))
</script>

<div class="io-map-editor {readOnly ? 'opacity-75 cursor-not-allowed' : ''}">
    {#if !readOnly}
        <div class="mb-3 flex items-center gap-2">
            <select
                class="flex-1 text-sm px-2 py-1.5 rounded border border-default-200 bg-background focus:outline-none focus:border-primary"
                bind:value={newLeftKey}
            >
                <option value="">Select {leftLabel}</option>
                {#each unusedLeftOptions as option}
                    <option value={option}>{option}</option>
                {/each}
            </select>
            <button
                type="button"
                class="p-1.5 rounded-full text-primary hover:bg-primary/10 disabled:opacity-50"
                disabled={!newLeftKey}
                onclick={addMapping}
                title="Add mapping"
            >
                <Icon icon="solar:add-circle-linear" width={20} />
            </button>
        </div>
    {/if}

    {#each Object.entries(value) as [leftKey, rightValue]}
        <div class="mb-3 flex items-center gap-2">
            <div class="flex-1 flex items-center gap-2">
                <div class="truncate max-w-[160px] px-2 py-1 bg-default-100 rounded-lg text-sm" title={leftKey}>
                    {leftKey}
                </div>
                <Icon icon="solar:arrow-right-linear" class="text-default-400 shrink-0" width={18} />
                <select
                    class="flex-1 text-sm px-2 py-1.5 rounded border border-default-200 bg-background focus:outline-none focus:border-primary"
                    value={rightValue}
                    disabled={readOnly}
                    onchange={(e) => updateMapping(leftKey, e.currentTarget.value)}
                >
                    {#each rightOptions as option}
                        <option value={option}>{option}</option>
                    {/each}
                </select>
            </div>
            {#if !readOnly}
                <button
                    type="button"
                    class="p-1.5 rounded-full text-destructive hover:bg-destructive/10"
                    onclick={() => deleteMapping(leftKey)}
                    title="Delete mapping"
                >
                    <Icon icon="solar:trash-bin-trash-linear" width={18} />
                </button>
            {/if}
        </div>
    {/each}
</div>
