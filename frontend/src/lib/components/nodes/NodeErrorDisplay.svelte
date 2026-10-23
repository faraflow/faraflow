<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    interface Props {
        error: string
        grow?: boolean
    }

    let { error, grow = false }: Props = $props()

    const errorData = $derived.by(() => {
        try {
            const jsonMatch = error.match(/{[\s\S]*}/)
            if (jsonMatch) {
                return JSON.parse(jsonMatch[0])
            }
        } catch {
            // fall through
        }
        return null
    })
</script>

<div
    class="overflow-y-auto"
    style="touch-action: none;"
    onwheelcapture={(e) => e.stopPropagation()}
>
    <div class="my-2 flex flex-col items-start gap-2">
        {#if errorData?.type === 'invalid_json_format'}
            <p class="text-sm font-semibold text-destructive">LLM Response Error:</p>
            <p class="text-sm">The Large Language Model returned a response that doesn't match the expected JSON format.</p>

            {#if errorData.original_response}
                <div class="w-full">
                    <p class="text-sm font-semibold mb-1">Original LLM Response:</p>
                    <pre class="w-full bg-muted rounded-md p-2 text-xs overflow-auto {grow ? '' : 'max-h-40'}">{errorData.original_response}</pre>
                </div>
            {/if}

            {#if errorData.validation_error}
                <div class="w-full">
                    <p class="text-sm font-semibold mb-1">Validation Error:</p>
                    <p class="text-sm text-destructive ml-2">{errorData.validation_error}</p>
                </div>
            {/if}
        {:else}
            <p class="text-sm font-semibold text-destructive">Error:</p>
            <pre class="w-full bg-muted rounded-md p-2 text-xs overflow-auto {grow ? '' : 'max-h-40'} text-destructive">{error}</pre>
        {/if}
    </div>
</div>
