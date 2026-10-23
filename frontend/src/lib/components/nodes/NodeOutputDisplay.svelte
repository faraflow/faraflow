<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import Icon from '@iconify/svelte'

    interface Props {
        output?: Record<string, any>
        maxHeight?: string | number
        grow?: boolean
    }

    let { output, maxHeight = '500px', grow = false }: Props = $props()

    let copiedKey: string | null = $state(null)

    async function copyToClipboard(text: any, key: string) {
        try {
            await navigator.clipboard.writeText(typeof text === 'string' ? text : JSON.stringify(text, null, 2))
            copiedKey = key
            setTimeout(() => (copiedKey = null), 2000)
        } catch {
            // ignore
        }
    }

    function renderValue(value: any): string {
        if (typeof value === 'string') return value
        return JSON.stringify(value, null, 2)
    }
</script>

{#if output && Object.keys(output).length > 0}
    <div
        class="mt-2 flex flex-col gap-2 overflow-y-auto"
        style="{grow ? '' : `max-height: ${maxHeight};`} touch-action: none;"
        onwheelcapture={(e) => e.stopPropagation()}
    >
        {#each Object.entries(output) as [key, value]}
            <div class="flex flex-col gap-1">
                <div class="flex items-center justify-between">
                    <span class="text-xs font-semibold text-muted-foreground">{key}</span>
                    <button
                        class="p-0.5 rounded hover:bg-muted transition-colors"
                        title="Copy"
                        onclick={(e) => { e.stopPropagation(); copyToClipboard(value, key) }}
                    >
                        <Icon
                            icon={copiedKey === key ? 'solar:check-circle-linear' : 'solar:copy-linear'}
                            width={14}
                            class={copiedKey === key ? 'text-green-500' : 'text-muted-foreground'}
                        />
                    </button>
                </div>
                <div class="bg-muted rounded-md p-2 text-xs overflow-auto {grow ? '' : 'max-h-40'}">
                    {#if typeof value === 'string'}
                        <span class="whitespace-pre-wrap">{value}</span>
                    {:else}
                        <pre class="whitespace-pre-wrap">{JSON.stringify(value, null, 2)}</pre>
                    {/if}
                </div>
            </div>
        {/each}
    </div>
{/if}
