<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import * as Dialog from '$lib/components/ui/dialog'
    import { Button } from '$lib/components/ui/button'

    interface Props {
        isOpen: boolean
        onClose: () => void
        onConfirm: () => void
        title: string
        message: string
        confirmText?: string
        cancelText?: string
        isDanger?: boolean
    }

    let {
        isOpen,
        onClose,
        onConfirm,
        title,
        message,
        confirmText = 'Confirm',
        cancelText = 'Cancel',
        isDanger = false,
    }: Props = $props()

    function handleConfirm() {
        onConfirm()
        onClose()
    }

    function handleKeydown(e: KeyboardEvent) {
        if (!isOpen) return
        if (e.key === 'Enter') handleConfirm()
        if (e.key === 'Escape') onClose()
    }
</script>

<svelte:window onkeydown={handleKeydown} />

<Dialog.Root open={isOpen} onOpenChange={(v) => { if (!v) onClose() }}>
    <Dialog.Content class="max-w-lg">
        <Dialog.Header>
            <Dialog.Title>{title}</Dialog.Title>
        </Dialog.Header>
        <p class="text-sm text-muted-foreground py-2">{message}</p>
        <Dialog.Footer>
            <Button variant="ghost" onclick={onClose}>
                {cancelText}
                <span class="ml-2 text-xs opacity-60">ESC</span>
            </Button>
            <Button
                variant={isDanger ? 'destructive' : 'default'}
                onclick={handleConfirm}
            >
                {confirmText}
                <span class="ml-2 text-xs opacity-60">↵</span>
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
