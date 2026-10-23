<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    interface Props {
        value?: string
        placeholder?: string
        disabled?: boolean
        isLoading?: boolean
        onSend?: (message: string) => void
    }

    let { value = $bindable(''), placeholder = 'Send a message...', disabled = false, isLoading = false, onSend }: Props = $props()

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSend()
        }
    }

    function handleSend() {
        const trimmed = value.trim()
        if (!trimmed || disabled || isLoading) return
        onSend?.(trimmed)
        value = ''
    }
</script>

<div class="flex gap-2 items-end">
    <textarea
        bind:value
        {placeholder}
        {disabled}
        rows={1}
        onkeydown={handleKeydown}
        oninput={(e) => {
            const el = e.currentTarget as HTMLTextAreaElement
            el.style.height = 'auto'
            el.style.height = Math.min(el.scrollHeight, 160) + 'px'
        }}
        class="flex-1 resize-none min-h-[40px] max-h-40 rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 disabled:cursor-not-allowed"
    ></textarea>
    <button
        onclick={handleSend}
        disabled={disabled || isLoading || !value.trim()}
        class="p-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex-none"
        title="Send message"
    >
        {#if isLoading}
            <div class="animate-spin h-4 w-4 border-2 border-primary-foreground border-t-transparent rounded-full"></div>
        {:else}
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" x2="11" y1="2" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        {/if}
    </button>
</div>
