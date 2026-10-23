<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { onMount, onDestroy } from 'svelte'
    import { createTestSession, getSession } from '$lib/utils/api'
    import { chatState, executeChat, cleanupChat } from '$lib/actions/chatExecution.svelte'
    import MessageCard from './MessageCard.svelte'
    import PromptInput from './PromptInput.svelte'

    interface Message {
        role: string
        message: string
        runId?: string
    }

    interface Props {
        workflowID?: string
        sessionId?: string
        onClose?: () => void
    }

    let { workflowID, sessionId: providedSessionId, onClose }: Props = $props()

    let messages = $state<Message[]>([])
    let sessionId = $state<string | null>(null)
    let scrollContainer: HTMLDivElement

    // Init session on mount
    onMount(async () => {
        if (providedSessionId) {
            sessionId = providedSessionId
            await fetchSessionMessages(providedSessionId)
        } else if (workflowID) {
            await initTestSession()
        }
    })

    // Restore messages from sessionStorage for test sessions
    $effect(() => {
        if (workflowID && !providedSessionId && sessionId) {
            const stored = sessionStorage.getItem(`chat_messages_${sessionId}`)
            if (stored) {
                try {
                    messages = JSON.parse(stored)
                } catch { /* ignore */ }
            }
        }
    })

    // Persist messages for test sessions
    $effect(() => {
        if (workflowID && !providedSessionId && sessionId && messages.length > 0) {
            sessionStorage.setItem(`chat_messages_${sessionId}`, JSON.stringify(messages))
        }
    })

    // Auto-scroll on new messages
    $effect(() => {
        if (messages.length >= 0 || chatState.isLoading) {
            scrollToBottom()
        }
    })

    onDestroy(() => {
        cleanupChat()
    })

    async function initTestSession() {
        if (!workflowID || providedSessionId) return
        try {
            const session = await createTestSession(workflowID)
            sessionId = session.id
        } catch (err) {
            console.error('Error creating test session:', err)
        }
    }

    async function fetchSessionMessages(sid: string) {
        try {
            const session = await getSession(sid)
            messages = session.messages.map((msg: any) => ({
                role: msg.content.role,
                message: msg.content.content,
                runId: msg.run_id,
            }))
        } catch (err) {
            console.error('Error fetching session messages:', err)
        }
    }

    async function handleSend(messageText: string) {
        if (!messageText.trim()) return

        messages = [...messages, { role: 'user', message: messageText }]

        if (workflowID) {
            const response = await executeChat(messageText, { workflowID, sessionId })
            if (response) {
                messages = [...messages, response]
            }
        } else {
            setTimeout(() => {
                messages = [...messages, {
                    role: 'assistant',
                    message: `No workflow connected. You said: "${messageText}"`,
                }]
            }, 500)
        }
    }

    async function handleClearChat() {
        if (sessionId) {
            sessionStorage.removeItem(`chat_messages_${sessionId}`)
        }
        messages = []
        await initTestSession()
    }

    function scrollToBottom() {
        if (scrollContainer) {
            setTimeout(() => {
                scrollContainer.scrollTop = scrollContainer.scrollHeight
            }, 10)
        }
    }
</script>

<div class="flex h-full w-full flex-col overflow-hidden">
    <!-- Header -->
    <div class="flex items-center justify-between px-3 border-b border-border shrink-0 bg-muted/30" style="height: 44px;">
        <h2 class="text-sm font-semibold">Chat</h2>
        <div class="flex items-center gap-2">
            {#if messages.length > 0}
                <button
                    onclick={handleClearChat}
                    class="text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                    Clear chat
                </button>
            {/if}
            <span class="text-xs text-muted-foreground">
                {sessionId ? `Session: ${sessionId.slice(0, 8)}...` : ''}
            </span>
            {#if onClose}
                <button
                    type="button"
                    class="p-1.5 rounded hover:bg-muted transition-colors"
                    onclick={onClose}
                    title="Close chat"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/></svg>
                </button>
            {/if}
        </div>
    </div>

    <!-- Messages -->
    <div bind:this={scrollContainer} class="flex-1 overflow-y-auto p-3">
        {#if messages.length === 0 && !chatState.isLoading}
            <div class="flex flex-col items-center justify-center h-full text-center p-4">
                <img src="/faraflow-logomark.svg" alt="Faraflow" class="w-16 h-16 mb-4" />
                <h3 class="text-base font-semibold mb-2">Welcome to Flow Chat</h3>
                <p class="text-sm text-muted-foreground max-w-sm">
                    {workflowID
                        ? 'This chat is powered by your workflow. Send a message to get started!'
                        : 'No workflow is connected yet.'}
                </p>
            </div>
        {:else}
            <div class="flex flex-col gap-3">
                {#each messages as msg, i (i)}
                    <MessageCard
                        avatar={msg.role === 'assistant' ? '/faraflow-logomark.svg' : undefined}
                        message={msg.message}
                        runId={msg.role === 'assistant' ? msg.runId : undefined}
                        {workflowID}
                        messageClass={msg.role === 'user' ? 'bg-muted text-foreground' : ''}
                    />
                {/each}

                {#if chatState.isLoading}
                    <MessageCard
                        avatar="/faraflow-logomark.svg"
                        message="Thinking..."
                        status="loading"
                    />
                {/if}

                {#if chatState.error}
                    <MessageCard
                        avatar="/faraflow-logomark.svg"
                        message="Error: {chatState.error}"
                        messageClass="bg-destructive/10 text-destructive"
                    />
                {/if}
            </div>
        {/if}
    </div>

    <!-- Input -->
    <div class="p-3 border-t border-border flex-shrink-0">
        <PromptInput
            placeholder={workflowID ? 'Send a message...' : 'No workflow connected'}
            disabled={!workflowID}
            isLoading={chatState.isLoading}
            onSend={handleSend}
        />
    </div>
</div>
