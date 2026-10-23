<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import Icon from '@iconify/svelte'
    import FewShotEditor from './FewShotEditor.svelte'
    import CodeEditor from './CodeEditor.svelte'

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

    let editorMode = $state<'visual' | 'json'>('visual')
    let jsonError = $state('')

    function handleJsonChange(jsonContent: string) {
        if (readOnly) return
        try {
            const parsed = JSON.parse(jsonContent)
            if (!Array.isArray(parsed)) {
                jsonError = 'JSON must be an array of examples'
                return
            }
            const isValid = parsed.every(
                (ex: any) =>
                    typeof ex === 'object' &&
                    (ex.input === undefined || typeof ex.input === 'string') &&
                    (ex.output === undefined || typeof ex.output === 'string')
            )
            if (!isValid) {
                jsonError = 'Each example must have optional "input" and "output" string fields'
                return
            }
            jsonError = ''
            onChange(parsed)
        } catch (e) {
            jsonError = e instanceof Error ? e.message : 'Invalid JSON'
        }
    }
</script>

<div class="few-shot-examples-editor">
    <div class="flex flex-col gap-3 mb-3">
        <div class="flex items-center gap-2">
            <h3 class="text-base font-semibold">Few Shot Examples</h3>
            <span
                class="cursor-help"
                title="Few-Shot prompting helps the AI understand patterns through examples. Each example should have an input and expected output."
            >
                <Icon icon="solar:question-circle-linear" class="text-default-400" width={18} />
            </span>
        </div>
        <div class="flex gap-1">
            {#each [['visual', 'Visual Editor'], ['json', 'JSON Editor']] as [key, label]}
                <button
                    type="button"
                    class="px-3 py-1 text-sm rounded {editorMode === key ? 'bg-primary text-primary-foreground' : 'bg-default-100 hover:bg-default-200'} disabled:opacity-50"
                    disabled={readOnly}
                    onclick={() => editorMode = key as 'visual' | 'json'}
                >
                    {label}
                </button>
            {/each}
        </div>
    </div>

    {#if editorMode === 'visual'}
        <FewShotEditor {nodeID} {examples} {onChange} {readOnly} />
    {:else}
        <div class="border border-default-200 rounded-lg overflow-hidden">
            {#if jsonError}
                <div class="flex items-center gap-2 text-sm text-destructive bg-destructive/10 px-3 py-2">
                    <Icon icon="solar:danger-triangle-bold" width={16} />
                    {jsonError}
                </div>
            {/if}
            <p class="text-xs text-foreground-500 px-3 pt-2 pb-0">
                Edit all examples in JSON format. Each example should have "input" and "output" fields.
            </p>
            <CodeEditor
                code={JSON.stringify(examples, null, 2)}
                onChange={handleJsonChange}
                mode="json"
                label=""
                {readOnly}
            />
        </div>
    {/if}
</div>
