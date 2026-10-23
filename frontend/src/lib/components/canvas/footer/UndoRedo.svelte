<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { Button } from '$lib/components/ui/button'
    import Icon from '@iconify/svelte'
    import { flowStore } from '$lib/stores/flow.svelte'

    const isMac = typeof navigator !== 'undefined' && navigator.platform.includes('Mac')

    function handleUndo() {
        if (flowStore.history.past.length > 0) {
            flowStore.undo()
        }
    }

    function handleRedo() {
        if (flowStore.history.future.length > 0) {
            flowStore.redo()
        }
    }
</script>

<svelte:window
    onkeydown={(e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
            e.preventDefault()
            handleUndo()
        } else if (
            ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'z') ||
            ((e.ctrlKey || e.metaKey) && e.key === 'y')
        ) {
            e.preventDefault()
            handleRedo()
        }
    }}
/>

<Button
    variant="ghost"
    size="icon"
    class="h-7 w-7 bg-background"
    disabled={flowStore.history.past.length === 0}
    title="Undo ({isMac ? '⌘' : 'Ctrl'}+Z)"
    onclick={handleUndo}
>
    <Icon icon="solar:undo-left-linear" width={16} class="text-foreground" />
</Button>
<Button
    variant="ghost"
    size="icon"
    class="h-7 w-7 bg-background"
    disabled={flowStore.history.future.length === 0}
    title="Redo ({isMac ? '⌘' : 'Ctrl'}+Shift+Z)"
    onclick={handleRedo}
>
    <Icon icon="solar:undo-right-linear" width={16} class="text-foreground" />
</Button>
