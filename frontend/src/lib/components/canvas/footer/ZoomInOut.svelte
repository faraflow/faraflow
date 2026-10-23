<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { Button } from '$lib/components/ui/button'
    import Icon from '@iconify/svelte'
    import { useSvelteFlow, useStore } from '@xyflow/svelte'

    const { zoomIn, zoomOut } = useSvelteFlow()
    const store = $derived(useStore())
    const zoom = $derived(store.viewport.zoom)

    const isMac = typeof navigator !== 'undefined' && navigator.platform.includes('Mac')
</script>

<div class="flex items-center justify-center shadow-none bg-background rounded-md border border-border px-1">
    <div class="zoom-controls flex items-center gap-1">
        <Button
            variant="ghost"
            size="icon"
            class="h-7 w-7"
            title="Zoom Out ({isMac ? '⌘' : 'Ctrl'}+-)"
            onclick={() => zoomOut()}
        >
            <Icon icon="solar:minimize-square-linear" width={16} class="text-foreground" />
        </Button>
        <span class="text-sm text-foreground w-12 text-center">{(zoom * 100).toFixed(0)}%</span>
        <Button
            variant="ghost"
            size="icon"
            class="h-7 w-7"
            title="Zoom In ({isMac ? '⌘' : 'Ctrl'}++)"
            onclick={() => zoomIn()}
        >
            <Icon icon="solar:maximize-square-linear" width={16} class="text-foreground" />
        </Button>
    </div>
</div>
