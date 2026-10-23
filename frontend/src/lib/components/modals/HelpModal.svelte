<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import Icon from '@iconify/svelte'
    import * as Dialog from '$lib/components/ui/dialog'
    import { Button } from '$lib/components/ui/button'

    interface Props {
        isOpen: boolean
        onOpenChange: (open: boolean) => void
    }

    let { isOpen, onOpenChange }: Props = $props()

    $effect(() => {
        if (!isOpen) return
        function onKeyDown(e: KeyboardEvent) {
            if (e.key === 'Escape') onOpenChange(false)
        }
        window.addEventListener('keydown', onKeyDown)
        return () => window.removeEventListener('keydown', onKeyDown)
    })
</script>

<Dialog.Root
    open={isOpen}
    onOpenChange={(open) => { if (!open) onOpenChange(false) }}
>
    <Dialog.Content class="max-w-2xl">
        <Dialog.Header>
            <Dialog.Title>How can we help you?</Dialog.Title>
        </Dialog.Header>

        <div class="space-y-6 py-2">
            <!-- Keyboard shortcuts -->
            <div>
                <h3 class="text-base font-semibold mb-3">Keyboard Shortcuts</h3>
                <div class="grid grid-cols-2 gap-6">
                    <div>
                        <h4 class="text-sm font-medium mb-2">Navigation</h4>
                        <ul class="space-y-2 text-sm text-muted-foreground">
                            <li class="flex items-center justify-between">
                                <span>Pan Canvas</span>
                                <kbd class="px-2 py-0.5 bg-muted rounded text-xs">Arrow Keys</kbd>
                            </li>
                            <li class="flex items-center justify-between">
                                <span>Pan Faster</span>
                                <kbd class="px-2 py-0.5 bg-muted rounded text-xs">Shift + Arrows</kbd>
                            </li>
                            <li class="flex items-center justify-between">
                                <span>Add Nodes</span>
                                <kbd class="px-2 py-0.5 bg-muted rounded text-xs">⌘ / Ctrl + K</kbd>
                            </li>
                        </ul>
                    </div>
                    <div>
                        <h4 class="text-sm font-medium mb-2">Actions</h4>
                        <ul class="space-y-2 text-sm text-muted-foreground">
                            <li class="flex items-center justify-between">
                                <span>Copy Selection</span>
                                <kbd class="px-2 py-0.5 bg-muted rounded text-xs">⌘ / Ctrl + C</kbd>
                            </li>
                            <li class="flex items-center justify-between">
                                <span>Cut Selection</span>
                                <kbd class="px-2 py-0.5 bg-muted rounded text-xs">⌘ / Ctrl + X</kbd>
                            </li>
                            <li class="flex items-center justify-between">
                                <span>Paste</span>
                                <kbd class="px-2 py-0.5 bg-muted rounded text-xs">⌘ / Ctrl + V</kbd>
                            </li>
                            <li class="flex items-center justify-between">
                                <span>Deselect</span>
                                <kbd class="px-2 py-0.5 bg-muted rounded text-xs">Esc</kbd>
                            </li>
                            <li class="flex items-center justify-between">
                                <span>Layout Workflow</span>
                                <kbd class="px-2 py-0.5 bg-muted rounded text-xs">⌘ / Ctrl + I</kbd>
                            </li>
                            <li class="flex items-center justify-between">
                                <span>Undo / Redo</span>
                                <kbd class="px-2 py-0.5 bg-muted rounded text-xs">⌘Z / ⌘⇧Z</kbd>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>

            <!-- Resource cards -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <button
                    type="button"
                    class="border rounded-xl p-6 flex flex-col items-center gap-3 text-center
                           hover:border-primary hover:bg-primary/5 transition-colors cursor-pointer"
                    onclick={() => window.open('https://github.com/faraflow/faraflow', '_blank')}
                >
                    <Icon icon="solar:book-linear" width={40} class="text-primary" />
                    <div>
                        <h3 class="font-semibold mb-1">Source and README</h3>
                        <p class="text-sm text-muted-foreground">
                            Read the README and browse the source on GitHub
                        </p>
                    </div>
                </button>
            </div>
        </div>

        <Dialog.Footer>
            <Button variant="outline" onclick={() => onOpenChange(false)}>
                Close
                <span class="ml-1 text-xs opacity-60">ESC</span>
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
