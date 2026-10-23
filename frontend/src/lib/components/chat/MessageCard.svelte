<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { marked } from 'marked'
    import { goto } from '$app/navigation'
    import { page } from '$app/stores'
    import { getRunStatusLight } from '$lib/utils/api'
    import { loadRunIntoCanvas } from '$lib/actions/workflowExecution.svelte'

    interface Props {
        avatar?: string
        message?: string
        status?: 'success' | 'failed' | 'loading'
        messageClass?: string
        runId?: string
        workflowID?: string
        class?: string
    }

    let { avatar, message, status, messageClass = '', runId, workflowID, class: className = '' }: Props = $props()

    async function handleRunClick(e: MouseEvent) {
        if (!runId) return
        if (e.metaKey || e.ctrlKey) {
            window.open(`/trace/${runId}`, '_blank')
            return
        }
        if (workflowID && $page.params.id === workflowID) {
            await loadRunIntoCanvas(runId)
        } else if (workflowID) {
            await goto(`/workflows/${workflowID}?runId=${runId}`)
        } else {
            window.open(`/trace/${runId}`, '_blank')
        }
    }

    let copied = $state(false)
    let durationLabel = $state<string | null>(null)

    function formatDuration(startTime: string, endTime: string): string {
        const ms = new Date(endTime).getTime() - new Date(startTime).getTime()
        if (ms < 1000) return `${ms}ms`
        const totalSeconds = ms / 1000
        if (totalSeconds < 60) return `${totalSeconds.toFixed(1)}s`
        const minutes = Math.floor(totalSeconds / 60)
        const seconds = Math.round(totalSeconds % 60)
        return `${minutes}m ${seconds}s`
    }

    $effect(() => {
        durationLabel = null
        if (!runId) return
        const id = runId
        getRunStatusLight(id)
            .then((run) => {
                if (id !== runId) return
                if (run.start_time && run.end_time) {
                    durationLabel = formatDuration(run.start_time, run.end_time)
                }
            })
            .catch(() => {
                // Duration is a nice-to-have; ignore failures silently
            })
    })

    async function handleCopy() {
        if (message) {
            await navigator.clipboard.writeText(message)
            copied = true
            setTimeout(() => (copied = false), 2000)
        }
    }

    const hasFailed = $derived(status === 'failed')
    const isLoading = $derived(status === 'loading')

    const renderedMessage = $derived.by(() => {
        if (!message || hasFailed || isLoading) return ''
        try {
            return marked.parse(message) as string
        } catch {
            return message
        }
    })
</script>

<div class="flex gap-3 {className}">
    <!-- Avatar -->
    <div class="flex-none">
        {#if avatar}
            <img src={avatar} alt="avatar" class="w-5 h-5 rounded-full object-cover" />
        {:else}
            <div class="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-xs font-medium">U</div>
        {/if}
    </div>

    <!-- Message bubble -->
    <div class="flex flex-col gap-2 flex-1 min-w-0">
        <div
            class="relative rounded-lg px-4 py-3 text-sm
                {hasFailed ? 'bg-destructive/10 border border-destructive/20 text-foreground' : ''}
                {isLoading ? 'bg-muted border border-border text-foreground' : ''}
                {!hasFailed && !isLoading ? 'bg-muted/50 text-foreground ' + messageClass : ''}"
        >
            <!-- Content -->
            <div class="pr-16 text-sm">
                {#if hasFailed}
                    <p>Something went wrong. Please try again.</p>
                {:else if isLoading}
                    <div class="flex items-center gap-2">
                        <div class="animate-spin h-3 w-3 border-2 border-muted-foreground border-t-transparent rounded-full"></div>
                        <span>Generating response...</span>
                    </div>
                {:else}
                    {@html renderedMessage}
                {/if}
            </div>

            <!-- Copy button (shown on hover) -->
            {#if !hasFailed && !isLoading && message}
                <div class="absolute right-2 top-2">
                    <button
                        onclick={handleCopy}
                        class="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                        title="Copy message"
                    >
                        {#if copied}
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                        {:else}
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
                        {/if}
                    </button>
                </div>
            {/if}

            <!-- Run ID link -->
            {#if runId}
                <div class="flex items-center justify-end gap-2 mt-2">
                    {#if durationLabel}
                        <span class="text-xs text-muted-foreground">{durationLabel}</span>
                    {/if}
                    <button
                        onclick={handleRunClick}
                        title="Click to load onto canvas · ⌘-click to open trace"
                        class="text-xs text-muted-foreground hover:text-foreground border border-border rounded px-1.5 py-0.5 transition-colors"
                    >
                        {runId}
                    </button>
                </div>
            {/if}
        </div>
    </div>
</div>
