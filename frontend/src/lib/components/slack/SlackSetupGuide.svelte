<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import * as Dialog from '$lib/components/ui/dialog'
    import { Button } from '$lib/components/ui/button'

    interface Props {
        isOpen: boolean
        onOpenChange: (open: boolean) => void
    }

    let { isOpen, onOpenChange }: Props = $props()

    const steps = [
        {
            title: 'Create a Slack app',
            body: 'Go to api.slack.com/apps and click "Create New App" → "From scratch". Pick a name and the workspace to install into.',
        },
        {
            title: 'Add bot token scopes',
            body: 'Under "OAuth & Permissions" → "Bot Token Scopes", add: app_mentions:read, chat:write, channels:history, channels:read, im:history, im:read, im:write.',
        },
        {
            title: 'Install to workspace',
            body: 'Click "Install to Workspace" at the top of OAuth & Permissions and authorize. Copy the Bot User OAuth Token (starts with xoxb-).',
        },
        {
            title: 'Enable Socket Mode (recommended)',
            body: 'Under "Socket Mode", enable it and create an app-level token with the connections:write scope (starts with xapp-). This lets Faraflow receive events without a public URL.',
        },
        {
            title: 'Subscribe to events',
            body: 'Under "Event Subscriptions", enable events and subscribe to the bot events: app_mention and message.im.',
        },
        {
            title: 'Create the agent in Faraflow',
            body: 'Use "Create New Agent", paste your tokens, choose a chatbot workflow, and configure when it should respond.',
        },
    ]
</script>

<Dialog.Root open={isOpen} onOpenChange={(open) => { if (!open) onOpenChange(false) }}>
    <Dialog.Content class="max-w-lg">
        <Dialog.Header>
            <Dialog.Title>Slack Setup Guide</Dialog.Title>
            <Dialog.Description>Connect a Slack workspace to your Faraflow workflows.</Dialog.Description>
        </Dialog.Header>

        <ol class="space-y-4 py-2 max-h-[60vh] overflow-y-auto">
            {#each steps as step, i}
                <li class="flex gap-3">
                    <div class="w-6 h-6 shrink-0 rounded-full bg-primary text-primary-foreground text-xs font-semibold flex items-center justify-center mt-0.5">
                        {i + 1}
                    </div>
                    <div>
                        <p class="text-sm font-medium">{step.title}</p>
                        <p class="text-sm text-muted-foreground mt-0.5">{step.body}</p>
                    </div>
                </li>
            {/each}
        </ol>

        <Dialog.Footer>
            <Button
                variant="outline"
                onclick={() => window.open('https://api.slack.com/apps', '_blank')}
            >
                Open api.slack.com
            </Button>
            <Button onclick={() => onOpenChange(false)}>Got it</Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
