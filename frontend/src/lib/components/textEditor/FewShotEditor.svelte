<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import Icon from '@iconify/svelte'
    import TextEditor from './TextEditor.svelte'

    interface FewShotExample {
        input?: string
        output?: string
    }

    interface Props {
        nodeID: string
        examples: FewShotExample[]
        onChange: (examples: FewShotExample[]) => void
        readOnly?: boolean
    }

    let { nodeID, examples, onChange, readOnly = false }: Props = $props()

    let expandedIndex = $state<number | null>(null)
    let activeTab = $state<Record<number, 'input' | 'output'>>({})

    function addExample() {
        if (readOnly) return
        onChange([...examples, { input: '', output: '' }])
        expandedIndex = examples.length
    }

    function deleteExample(index: number) {
        if (readOnly) return
        onChange(examples.filter((_, i) => i !== index))
        if (expandedIndex === index) expandedIndex = null
    }

    function handleContentChange(index: number, tab: 'input' | 'output', content: string) {
        if (readOnly) return
        const updated = examples.map((ex, i) => (i === index ? { ...ex, [tab]: content } : ex))
        onChange(updated)
    }

    function toggleExpand(index: number) {
        expandedIndex = expandedIndex === index ? null : index
    }

    function getTab(index: number): 'input' | 'output' {
        return activeTab[index] || 'input'
    }

    function setTab(index: number, tab: 'input' | 'output') {
        activeTab = { ...activeTab, [index]: tab }
    }
</script>

<div class="space-y-3">
    {#each examples as example, index}
        <div class="border border-default-200 rounded-lg bg-default-50">
            <div class="flex items-center justify-between p-3">
                <div class="flex items-center gap-2">
                    <button
                        type="button"
                        class="p-1 rounded hover:bg-default-200 disabled:opacity-50"
                        disabled={readOnly}
                        onclick={() => toggleExpand(index)}
                    >
                        <Icon
                            icon={expandedIndex === index ? 'solar:alt-arrow-up-linear' : 'solar:alt-arrow-down-linear'}
                            width={18}
                        />
                    </button>
                    <span class="font-medium text-sm">Example {index + 1}</span>
                </div>
                {#if !readOnly}
                    <button
                        type="button"
                        class="p-1 rounded text-destructive hover:bg-destructive/10"
                        onclick={() => deleteExample(index)}
                    >
                        <Icon icon="solar:trash-bin-trash-linear" width={18} />
                    </button>
                {/if}
            </div>

            <!-- Collapsed preview -->
            {#if expandedIndex !== index}
                <div class="grid grid-cols-2 gap-3 px-3 pb-3">
                    <div class="text-xs text-foreground-500">
                        <div class="font-medium mb-1">Input</div>
                        <div class="truncate">{example.input || 'No input'}</div>
                    </div>
                    <div class="text-xs text-foreground-500">
                        <div class="font-medium mb-1">Output</div>
                        <div class="truncate">{example.output || 'No output'}</div>
                    </div>
                </div>
            {/if}

            <!-- Expanded editor -->
            {#if expandedIndex === index}
                <div class="px-3 pb-3">
                    <div class="flex gap-1 mb-2">
                        {#each ['input', 'output'] as tab}
                            <button
                                type="button"
                                class="px-3 py-1 text-sm rounded {getTab(index) === tab ? 'bg-primary text-primary-foreground' : 'bg-default-100 hover:bg-default-200'}"
                                disabled={readOnly}
                                onclick={() => setTab(index, tab as 'input' | 'output')}
                            >
                                {tab.charAt(0).toUpperCase() + tab.slice(1)}
                            </button>
                        {/each}
                    </div>
                    <TextEditor
                        nodeID={nodeID}
                        fieldName={`few_shot_examples[${index}][${getTab(index)}]`}
                        content={example[getTab(index)] || ''}
                        setContent={(content) => handleContentChange(index, getTab(index), content)}
                        isEditable={!readOnly}
                        fieldTitle={`Example ${index + 1} ${getTab(index)}`}
                        {readOnly}
                    />
                </div>
            {/if}
        </div>
    {/each}

    {#if !readOnly}
        <button
            type="button"
            class="w-full flex items-center justify-center gap-2 p-3 border-2 border-dashed border-default-200 rounded-lg text-sm hover:border-primary hover:text-primary transition-colors"
            onclick={addExample}
        >
            <Icon icon="solar:add-circle-linear" width={18} />
            Add Example
        </button>
    {/if}
</div>
