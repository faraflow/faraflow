<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { toast } from 'svelte-sonner'
    import * as Dialog from '$lib/components/ui/dialog'
    import { Button } from '$lib/components/ui/button'
    import ConfirmationModal from '$lib/components/modals/ConfirmationModal.svelte'
    import SlackTestConnection from './SlackTestConnection.svelte'
    import {
        associateWorkflow,
        deleteSlackToken,
        fetchMaskedToken,
        getSlackAgent,
        getSocketModeStatus,
        getWorkflows,
        saveSlackTokens,
        startSocketMode,
        stopSocketMode,
        updateTriggerConfig,
        type SlackAgent,
        type SlackTokenType,
    } from '$lib/utils/api'
    import type { WorkflowResponse } from '$lib/types/api_types/workflowSchemas'

    interface Props {
        agent: SlackAgent
        isOpen: boolean
        onOpenChange: (open: boolean) => void
        onUpdated: (agent: SlackAgent) => void
    }

    let { agent, isOpen, onOpenChange, onUpdated }: Props = $props()

    type Tab = 'triggers' | 'tokens' | 'socket-mode'
    let activeTab = $state<Tab>('triggers')

    // ── Triggers tab ─────────────────────────────────────────────────────
    let triggerEnabled = $state(false)
    let triggerOnMention = $state(false)
    let triggerOnDM = $state(false)
    let triggerOnChannel = $state(false)
    let keywords = $state('')
    let workflowId = $state('')
    let workflows = $state<WorkflowResponse[]>([])
    let isSavingTriggers = $state(false)

    // ── Tokens tab ───────────────────────────────────────────────────────
    const tokenTypes: Array<{ type: SlackTokenType; label: string; hint: string }> = [
        { type: 'bot_token', label: 'Bot Token', hint: 'xoxb-' },
        { type: 'user_token', label: 'User Token', hint: 'xoxp-' },
        { type: 'app_token', label: 'App Token (Socket Mode)', hint: 'xapp-' },
    ]
    let maskedTokens = $state<Record<string, string>>({})
    let tokenInputs = $state<Record<string, string>>({})
    let isSavingTokens = $state(false)
    let tokenToDelete = $state<SlackTokenType | null>(null)

    // ── Socket mode tab ──────────────────────────────────────────────────
    let socketModeActive = $state<boolean | null>(null)
    let socketModeMessage = $state('')
    let isSocketBusy = $state(false)

    let isTestOpen = $state(false)

    // Initialize form state each time the dialog opens
    $effect(() => {
        if (!isOpen) return
        activeTab = 'triggers'
        triggerEnabled = agent.trigger_enabled
        triggerOnMention = agent.trigger_on_mention
        triggerOnDM = agent.trigger_on_direct_message
        triggerOnChannel = agent.trigger_on_channel_message
        keywords = (agent.trigger_keywords ?? []).join(', ')
        workflowId = agent.workflow_id ?? ''
        maskedTokens = {}
        tokenInputs = {}
        socketModeActive = null
        socketModeMessage = ''

        getWorkflows(1, 100)
            .then((w) => (workflows = w))
            .catch(() => {})
        loadMaskedTokens()
    })

    function hasToken(type: SlackTokenType): boolean {
        if (type === 'bot_token') return agent.has_bot_token
        if (type === 'user_token') return agent.has_user_token
        return agent.has_app_token ?? false
    }

    async function loadMaskedTokens() {
        for (const { type } of tokenTypes) {
            if (!hasToken(type)) continue
            fetchMaskedToken(agent.id, type)
                .then((res) => (maskedTokens = { ...maskedTokens, [type]: res.masked_token }))
                .catch(() => {})
        }
    }

    async function refreshAgent() {
        try {
            const fresh = await getSlackAgent(agent.id)
            agent = fresh
            onUpdated(fresh)
        } catch {
            /* keep stale agent on transient errors */
        }
    }

    async function handleSaveTriggers() {
        try {
            isSavingTriggers = true
            const updated = await updateTriggerConfig(agent.id, {
                trigger_enabled: triggerEnabled,
                trigger_on_mention: triggerOnMention,
                trigger_on_direct_message: triggerOnDM,
                trigger_on_channel_message: triggerOnChannel,
                trigger_keywords: keywords.split(',').map((k) => k.trim()).filter(Boolean),
            })
            if (workflowId && workflowId !== agent.workflow_id) {
                await associateWorkflow(agent.id, workflowId)
                await refreshAgent()
            } else {
                agent = updated
                onUpdated(updated)
            }
            toast.success('Trigger settings saved')
        } catch {
            toast.error('Failed to save trigger settings')
        } finally {
            isSavingTriggers = false
        }
    }

    async function handleSaveTokens() {
        const toSave = Object.fromEntries(
            Object.entries(tokenInputs).filter(([, v]) => v?.trim())
        )
        if (Object.keys(toSave).length === 0) {
            toast.error('Enter a token to save')
            return
        }
        try {
            isSavingTokens = true
            await saveSlackTokens(agent.id, toSave)
            toast.success('Tokens saved')
            tokenInputs = {}
            await refreshAgent()
            await loadMaskedTokens()
        } catch {
            toast.error('Failed to save tokens')
        } finally {
            isSavingTokens = false
        }
    }

    async function handleDeleteToken() {
        if (!tokenToDelete) return
        try {
            await deleteSlackToken(agent.id, tokenToDelete)
            toast.success('Token deleted')
            maskedTokens = { ...maskedTokens, [tokenToDelete]: '' }
            tokenToDelete = null
            await refreshAgent()
        } catch {
            toast.error('Failed to delete token')
        }
    }

    async function loadSocketStatus() {
        const status = await getSocketModeStatus(agent.id)
        if (status) {
            socketModeActive = status.socket_mode_active
            socketModeMessage = ''
        } else {
            socketModeActive = null
            socketModeMessage = 'Could not fetch Socket Mode status'
        }
    }

    function selectTab(tab: Tab) {
        activeTab = tab
        if (tab === 'socket-mode') loadSocketStatus()
    }

    async function handleSocketToggle(start: boolean) {
        try {
            isSocketBusy = true
            const res = start ? await startSocketMode(agent.id) : await stopSocketMode(agent.id)
            socketModeActive = res.socket_mode_active
            socketModeMessage = res.message
            if (res.socket_mode_active === start) {
                toast.success(start ? 'Socket Mode started' : 'Socket Mode stopped')
            }
            await refreshAgent()
        } finally {
            isSocketBusy = false
        }
    }
</script>

<Dialog.Root open={isOpen} onOpenChange={(open) => { if (!open) onOpenChange(false) }}>
    <Dialog.Content class="max-w-xl">
        <Dialog.Header>
            <Dialog.Title>Edit Agent — {agent.name}</Dialog.Title>
            {#if agent.slack_team_name}
                <Dialog.Description>Workspace: {agent.slack_team_name}</Dialog.Description>
            {/if}
        </Dialog.Header>

        <!-- Tab bar -->
        <div class="flex gap-1 border-b border-border">
            {#each [{ id: 'triggers', label: 'Triggers' }, { id: 'tokens', label: 'Tokens' }, { id: 'socket-mode', label: 'Socket Mode' }] as tab}
                <button
                    onclick={() => selectTab(tab.id as Tab)}
                    class="px-3 py-2 text-sm border-b-2 -mb-px transition-colors {activeTab === tab.id
                        ? 'border-primary font-medium'
                        : 'border-transparent text-muted-foreground hover:text-foreground'}"
                >
                    {tab.label}
                </button>
            {/each}
        </div>

        <div class="py-3 min-h-64 max-h-[55vh] overflow-y-auto">
            {#if activeTab === 'triggers'}
                <div class="space-y-4">
                    {#each [
                        { label: 'Triggers enabled', get: () => triggerEnabled, set: (v: boolean) => (triggerEnabled = v) },
                        { label: 'Respond to @mentions', get: () => triggerOnMention, set: (v: boolean) => (triggerOnMention = v) },
                        { label: 'Respond to direct messages', get: () => triggerOnDM, set: (v: boolean) => (triggerOnDM = v) },
                        { label: 'Respond to channel messages', get: () => triggerOnChannel, set: (v: boolean) => (triggerOnChannel = v) },
                    ] as sw}
                        <div class="flex items-center justify-between">
                            <span class="text-sm">{sw.label}</span>
                            <button
                                role="switch"
                                aria-checked={sw.get()}
                                aria-label={sw.label}
                                onclick={() => sw.set(!sw.get())}
                                class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors {sw.get() ? 'bg-primary' : 'bg-muted'}"
                            >
                                <span class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {sw.get() ? 'translate-x-6' : 'translate-x-1'}"></span>
                            </button>
                        </div>
                    {/each}

                    <div>
                        <label for="editor-keywords" class="block text-sm font-medium mb-1.5">Trigger keywords</label>
                        <input
                            id="editor-keywords"
                            type="text"
                            bind:value={keywords}
                            placeholder="help, support, question"
                            class="w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                        />
                        <p class="text-xs text-muted-foreground mt-1">Comma-separated. Messages containing these words trigger the agent.</p>
                    </div>

                    <div>
                        <label for="editor-workflow" class="block text-sm font-medium mb-1.5">Workflow</label>
                        <select
                            id="editor-workflow"
                            bind:value={workflowId}
                            class="w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                        >
                            <option value="">Not connected</option>
                            {#each workflows as wf}
                                <option value={wf.id}>{wf.name}</option>
                            {/each}
                        </select>
                    </div>

                    <Button onclick={handleSaveTriggers} disabled={isSavingTriggers}>
                        {isSavingTriggers ? 'Saving...' : 'Save Trigger Settings'}
                    </Button>
                </div>
            {:else if activeTab === 'tokens'}
                <div class="space-y-5">
                    {#each tokenTypes as { type, label, hint }}
                        <div>
                            <div class="flex items-center justify-between mb-1.5">
                                <label for={`editor-${type}`} class="text-sm font-medium">
                                    {label} <span class="text-muted-foreground font-normal">(starts with {hint})</span>
                                </label>
                                {#if hasToken(type)}
                                    <Button variant="ghost" size="sm" onclick={() => (tokenToDelete = type)}>
                                        Delete
                                    </Button>
                                {/if}
                            </div>
                            {#if maskedTokens[type]}
                                <p class="font-mono text-xs text-muted-foreground mb-1.5">Current: {maskedTokens[type]}</p>
                            {/if}
                            <input
                                id={`editor-${type}`}
                                type="password"
                                value={tokenInputs[type] ?? ''}
                                oninput={(e) => (tokenInputs = { ...tokenInputs, [type]: e.currentTarget.value })}
                                placeholder={hasToken(type) ? 'Enter new token to replace' : `${hint}...`}
                                class="w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring font-mono"
                            />
                        </div>
                    {/each}
                    <Button onclick={handleSaveTokens} disabled={isSavingTokens}>
                        {isSavingTokens ? 'Saving...' : 'Save Tokens'}
                    </Button>
                </div>
            {:else}
                <div class="space-y-4">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-sm font-medium">Socket Mode</p>
                            <p class="text-xs text-muted-foreground mt-0.5">
                                Receive Slack events over a WebSocket — no public URL required.
                            </p>
                        </div>
                        <span
                            class="text-xs px-2 py-0.5 rounded-full font-medium {socketModeActive
                                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                : 'bg-muted text-muted-foreground'}"
                        >
                            {socketModeActive === null ? 'Unknown' : socketModeActive ? 'Active' : 'Inactive'}
                        </span>
                    </div>

                    {#if !agent.has_app_token}
                        <div class="p-3 rounded-md bg-amber-50 border border-amber-200 dark:bg-amber-900/20 dark:border-amber-800 text-sm text-amber-800 dark:text-amber-300">
                            Socket Mode requires an app-level token (xapp-...). Add one in the Tokens tab first.
                        </div>
                    {/if}

                    {#if socketModeMessage}
                        <p class="text-sm text-muted-foreground">{socketModeMessage}</p>
                    {/if}

                    <div class="flex gap-2">
                        <Button
                            onclick={() => handleSocketToggle(true)}
                            disabled={isSocketBusy || !agent.has_app_token || socketModeActive === true}
                        >
                            {isSocketBusy ? 'Working...' : 'Start'}
                        </Button>
                        <Button
                            variant="outline"
                            onclick={() => handleSocketToggle(false)}
                            disabled={isSocketBusy || socketModeActive !== true}
                        >
                            Stop
                        </Button>
                    </div>
                </div>
            {/if}
        </div>

        <Dialog.Footer>
            <Button variant="outline" onclick={() => (isTestOpen = true)}>Test Connection</Button>
            <Button variant="ghost" onclick={() => onOpenChange(false)}>Close</Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>

<SlackTestConnection {agent} isOpen={isTestOpen} onOpenChange={(open) => (isTestOpen = open)} />

<ConfirmationModal
    isOpen={tokenToDelete !== null}
    onClose={() => (tokenToDelete = null)}
    onConfirm={handleDeleteToken}
    title="Delete Token"
    message={`Delete the ${tokenToDelete?.replace('_', ' ')} for "${agent.name}"? The agent will stop working until a new one is saved.`}
    confirmText="Delete"
    isDanger={true}
/>
