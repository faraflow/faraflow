<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { Button } from '$lib/components/ui/button'
    import Icon from '@iconify/svelte'
    import LoadingSpinner from '$lib/components/LoadingSpinner.svelte'

    interface Props {
        id: string
        isRunning: boolean
        loading: boolean
        isInputNode: boolean
        hasRun: boolean
        handlePartialRun: () => void
        handleDelete?: () => void
        handleDuplicate?: () => void
        handleDetach?: () => void
        readOnly?: boolean
        taskStatus?: string
        onPauseAction?: () => void
    }

    let {
        id,
        isRunning,
        loading,
        isInputNode,
        hasRun,
        handlePartialRun,
        handleDelete,
        handleDuplicate,
        handleDetach,
        readOnly = false,
        taskStatus,
        onPauseAction,
    }: Props = $props()
</script>

<div
    class="absolute -top-11 right-0 flex flex-row gap-1 p-1.5 rounded-xl border border-border bg-background/80 backdrop-blur-sm shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-auto z-10"
    role="presentation"
    onclick={(e) => e.stopPropagation()}
>
    {#if handlePartialRun}
        <Button
            variant="ghost"
            size="icon"
            class="h-7 w-7 rounded-lg hover:bg-primary/20"
            disabled={loading || isRunning}
            title="Run node"
            onclick={handlePartialRun}
        >
            {#if isRunning}
                <LoadingSpinner size="sm" />
            {:else}
                <Icon class="text-muted-foreground" icon="solar:play-linear" width={18} />
            {/if}
        </Button>
    {/if}

    {#if !readOnly && handleDuplicate}
        <Button
            variant="ghost"
            size="icon"
            class="h-7 w-7 rounded-lg"
            title="Duplicate"
            onclick={handleDuplicate}
        >
            <Icon class="text-muted-foreground" icon="solar:copy-linear" width={18} />
        </Button>
    {/if}

    {#if !readOnly && handleDetach}
        <Button
            variant="ghost"
            size="icon"
            class="h-7 w-7 rounded-lg"
            title="Detach from group"
            onclick={handleDetach}
        >
            <Icon class="text-muted-foreground" icon="solar:link-broken-linear" width={18} />
        </Button>
    {/if}

{#if taskStatus === 'PAUSED' && onPauseAction}
        <Button
            variant="ghost"
            size="icon"
            class="h-7 w-7 rounded-lg hover:bg-green-500/20"
            title="Approve / Decline / Override"
            onclick={onPauseAction}
        >
            <Icon class="text-yellow-500" icon="solar:hand-shake-linear" width={18} />
        </Button>
    {/if}

    {#if !readOnly && handleDelete}
        <Button
            variant="ghost"
            size="icon"
            class="h-7 w-7 rounded-lg"
            title="Delete"
            onclick={handleDelete}
        >
            <Icon class="text-muted-foreground" icon="solar:trash-bin-trash-linear" width={18} />
        </Button>
    {/if}
</div>
