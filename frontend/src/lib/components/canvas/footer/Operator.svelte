<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { Button } from '$lib/components/ui/button'
    import Icon from '@iconify/svelte'
    import { MiniMap, Panel } from '@xyflow/svelte'
    import { modeStore } from '$lib/stores/mode.svelte'
    import UndoRedo from './UndoRedo.svelte'
    import ZoomInOut from './ZoomInOut.svelte'

    interface Props {
        handleLayout: () => void
        handleDownloadImage: () => void
    }

    let { handleLayout, handleDownloadImage }: Props = $props()

    const isMac = typeof navigator !== 'undefined' && navigator.platform.includes('Mac')

    import { mode } from 'mode-watcher'
    const isDark = $derived($mode === 'dark')
</script>

<MiniMap
    position="bottom-right"
    width={102}
    height={72}
    nodeColor={() => (isDark ? '#777' : '#eee')}
    maskColor={isDark ? 'rgba(0,0,0,0.4)' : 'rgba(240,240,240,0.6)'}
    style="margin: 0; right: 1rem; bottom: 1rem; border: 1px solid hsl(var(--border)); border-radius: 0.5rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); overflow: hidden; z-index: 9;"
    class="bg-card"
/>

<Panel position="bottom-left" class="flex items-center gap-2 !left-1 !bottom-1 z-[9]">
    <ZoomInOut />
    <div class="flex gap-0 rounded-md border border-border bg-background overflow-hidden">
        <Button
            variant="ghost"
            size="icon"
            class="h-7 w-7 rounded-none border-r border-border"
            title="Select (V)"
            onclick={() => modeStore.setMode('pointer')}
        >
            <Icon
                class={modeStore.mode === 'pointer' ? 'text-foreground' : 'text-foreground/60'}
                icon={modeStore.mode === 'pointer' ? 'solar:cursor-bold' : 'solar:cursor-linear'}
                width={16}
            />
        </Button>
        <Button
            variant="ghost"
            size="icon"
            class="h-7 w-7 rounded-none border-r border-border"
            title="Pan (Space)"
            onclick={() => modeStore.setMode('hand')}
        >
            <Icon
                class={modeStore.mode === 'hand' ? 'text-foreground' : 'text-foreground/60'}
                icon={modeStore.mode === 'hand' ? 'solar:hand-shake-bold' : 'solar:hand-shake-linear'}
                width={16}
            />
        </Button>
        <Button
            variant="ghost"
            size="icon"
            class="h-7 w-7 rounded-none"
            title="Layout Nodes ({isMac ? '⌘' : 'Ctrl'}+L)"
            onclick={handleLayout}
        >
            <Icon class="text-foreground" icon="solar:ruler-angular-linear" width={16} />
        </Button>
    </div>
    <div class="flex rounded-md border border-border bg-background overflow-hidden">
        <UndoRedo />
    </div>
</Panel>
