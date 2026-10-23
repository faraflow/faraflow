<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { toast } from 'svelte-sonner'
    import * as Dialog from '$lib/components/ui/dialog'
    import { Button } from '$lib/components/ui/button'
    import {
        sendTestMessage,
        testSlackConnection,
        type SlackAgent,
        type SlackConnectionTestResult,
    } from '$lib/utils/api'

    interface Props {
        agent: SlackAgent
        isOpen: boolean
        onOpenChange: (open: boolean) => void
    }

    let { agent, isOpen, onOpenChange }: Props = $props()

    let result = $state<SlackConnectionTestResult | null>(null)
    let isTesting = $state(false)
    let channel = $state('')
    let message = $state('Hello from Faraflow!')
    let isSending = $state(false)

    // Run the connection test each time the dialog opens
    $effect(() => {
        if (!isOpen) return
        result = null
        isTesting = true
        testSlackConnection(agent.id)
            .then((r) => (result = r))
            .finally(() => (isTesting = false))
    })

    async function handleSendTestMessage() {
        if (!channel.trim()) { toast.error('Enter a channel name'); return }
        try {
            isSending = true
            const res = await sendTestMessage(channel.trim(), message, agent.id)
            if (res.success) toast.success(res.message || 'Test message sent')
            else toast.error(res.message || 'Failed to send test message')
        } catch {
            toast.error('Failed to send test message')
        } finally {
            isSending = false
        }
    }
</script>

<Dialog.Root open={isOpen} onOpenChange={(open) => { if (!open) onOpenChange(false) }}>
    <Dialog.Content class="max-w-md">
        <Dialog.Header>
            <Dialog.Title>Test Connection — {agent.name}</Dialog.Title>
        </Dialog.Header>

        <div class="space-y-4 py-2">
            {#if isTesting}
                <div class="flex items-center gap-2 text-sm text-muted-foreground">
                    <div class="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full"></div>
                    Testing connection...
                </div>
            {:else if result}
                <div
                    class="p-3 rounded-md text-sm {result.success
                        ? 'bg-green-50 text-green-800 dark:bg-green-900/20 dark:text-green-300'
                        : 'bg-destructive/10 text-destructive'}"
                >
                    <p class="font-medium">{result.success ? 'Connection successful' : 'Connection failed'}</p>
                    <p class="mt-1">{result.message}</p>
                    {#if result.success}
                        <div class="mt-2 space-y-0.5 font-mono text-xs">
                            {#if result.team_id}<p>Team: {result.team_id}</p>{/if}
                            {#if result.bot_id}<p>Bot: {result.bot_id}</p>{/if}
                            {#if result.user_id}<p>User: {result.user_id}</p>{/if}
                        </div>
                    {/if}
                </div>
            {/if}

            <div class="border-t border-border pt-4 space-y-3">
                <p class="text-sm font-medium">Send a test message</p>
                <div>
                    <label for="test-channel" class="block text-sm mb-1">Channel</label>
                    <input
                        id="test-channel"
                        type="text"
                        bind:value={channel}
                        placeholder="#general"
                        class="w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                </div>
                <div>
                    <label for="test-message" class="block text-sm mb-1">Message</label>
                    <input
                        id="test-message"
                        type="text"
                        bind:value={message}
                        class="w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                </div>
                <Button size="sm" onclick={handleSendTestMessage} disabled={isSending}>
                    {isSending ? 'Sending...' : 'Send Test Message'}
                </Button>
            </div>
        </div>

        <Dialog.Footer>
            <Button variant="outline" onclick={() => onOpenChange(false)}>Close</Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
