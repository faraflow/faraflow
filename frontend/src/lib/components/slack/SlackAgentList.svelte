<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { onMount } from 'svelte'
    import { goto } from '$app/navigation'
    import { toast } from 'svelte-sonner'
    import Icon from '@iconify/svelte'
    import { Button } from '$lib/components/ui/button'
    import ConfirmationModal from '$lib/components/modals/ConfirmationModal.svelte'
    import SpurTypeChip from '$lib/components/SpurTypeChip.svelte'
    import SlackAgentEditor from './SlackAgentEditor.svelte'
    import SlackSetupGuide from './SlackSetupGuide.svelte'
    import SlackTestConnection from './SlackTestConnection.svelte'
    import {
        deleteSlackAgent,
        getSlackAgents,
        getSocketModeStatus,
        startSocketMode,
        stopSocketMode,
        toggleSlackTrigger,
        type SlackAgent,
    } from '$lib/utils/api'

    interface Props {
        onCountChange?: (count: number) => void
    }

    let { onCountChange }: Props = $props()

    let agents = $state<SlackAgent[]>([])
    let isLoading = $state(true)
    let isGuideOpen = $state(false)
    let editingAgent = $state<SlackAgent | null>(null)
    let testingAgent = $state<SlackAgent | null>(null)
    let deletingAgent = $state<SlackAgent | null>(null)
    let socketBusyId = $state<number | null>(null)

    onMount(() => {
        loadAgents()

        // Refresh socket-mode status every 30s and when the tab regains focus
        const interval = setInterval(refreshSocketStatuses, 30_000)
        const onVisibility = () => {
            if (document.visibilityState === 'visible') refreshSocketStatuses()
        }
        document.addEventListener('visibilitychange', onVisibility)
        return () => {
            clearInterval(interval)
            document.removeEventListener('visibilitychange', onVisibility)
        }
    })

    $effect(() => {
        onCountChange?.(agents.length)
    })

    async function loadAgents() {
        try {
            isLoading = true
            agents = await getSlackAgents()
            refreshSocketStatuses()
        } finally {
            isLoading = false
        }
    }

    async function refreshSocketStatuses() {
        for (const agent of agents.filter((a) => a.has_app_token)) {
            const status = await getSocketModeStatus(agent.id)
            if (status) {
                agents = agents.map((a) =>
                    a.id === agent.id ? { ...a, socket_mode_enabled: status.socket_mode_active } : a
                )
            }
        }
    }

    function updateAgent(updated: SlackAgent) {
        agents = agents.map((a) => (a.id === updated.id ? updated : a))
    }

    async function handleTriggerToggle(agent: SlackAgent, value: boolean) {
        await toggleSlackTrigger(agent.id, 'trigger_enabled', value, agents, (updater) => {
            agents = updater(agents)
        }, (message, color) => {
            if (color === 'success') toast.success(message)
            else toast.error(message)
        })
    }

    async function handleSocketToggle(agent: SlackAgent) {
        if (!agent.has_bot_token) {
            toast.warning('Add a bot token before enabling Socket Mode')
            return
        }
        if (!agent.socket_mode_enabled && !agent.has_app_token) {
            toast.warning('Socket Mode requires an app-level token (xapp-...). Add one in the agent editor.')
            return
        }
        try {
            socketBusyId = agent.id
            const res = agent.socket_mode_enabled
                ? await stopSocketMode(agent.id)
                : await startSocketMode(agent.id)
            agents = agents.map((a) =>
                a.id === agent.id ? { ...a, socket_mode_enabled: res.socket_mode_active } : a
            )
            if (res.message && res.socket_mode_active === Boolean(agent.socket_mode_enabled)) {
                // state didn't change — surface the reason
                toast.error(res.message)
            }
        } finally {
            socketBusyId = null
        }
    }

    async function handleDelete() {
        if (!deletingAgent) return
        const ok = await deleteSlackAgent(deletingAgent.id)
        if (ok) {
            toast.success('Slack agent deleted')
            agents = agents.filter((a) => a.id !== deletingAgent!.id)
        } else {
            toast.error('Failed to delete Slack agent')
        }
        deletingAgent = null
    }
</script>

{#if isLoading}
    <div class="flex justify-center py-8">
        <div class="animate-spin h-6 w-6 border-2 border-primary border-t-transparent rounded-full"></div>
    </div>
{:else if agents.length === 0}
    <div class="text-center py-10">
        <Icon icon="logos:slack-icon" width={40} class="mx-auto mb-3" />
        <h3 class="font-semibold mb-1">No Slack Agents Connected</h3>
        <p class="text-sm text-muted-foreground mb-4">
            Connect a Slack workspace to trigger workflows from mentions, DMs, and keywords.
        </p>
        <div class="flex justify-center gap-2">
            <Button variant="outline" onclick={() => (isGuideOpen = true)}>Setup Guide</Button>
            <Button onclick={() => goto('/slack/create-agent')}>Create New Agent</Button>
        </div>
    </div>
{:else}
    <div class="flex justify-end mb-3">
        <Button size="sm" onclick={() => goto('/slack/create-agent')}>Create New Agent</Button>
    </div>
    <div class="border border-border rounded-xl overflow-hidden">
        <table class="w-full text-sm">
            <thead class="bg-muted/50 text-left">
                <tr>
                    <th class="px-4 py-3 font-medium">Name</th>
                    <th class="px-4 py-3 font-medium">Workspace</th>
                    <th class="px-4 py-3 font-medium">Workflow</th>
                    <th class="px-4 py-3 font-medium">Triggers</th>
                    <th class="px-4 py-3 font-medium">Socket Mode</th>
                    <th class="px-4 py-3 font-medium text-right">Actions</th>
                </tr>
            </thead>
            <tbody>
                {#each agents as agent (agent.id)}
                    <tr class="border-t border-border hover:bg-muted/30 transition-colors">
                        <td class="px-4 py-3">
                            <div class="flex items-center gap-2">
                                <span class="font-medium">{agent.name}</span>
                                <SpurTypeChip spurType={agent.spur_type} showText={false} />
                            </div>
                        </td>
                        <td class="px-4 py-3 text-muted-foreground">{agent.slack_team_name || '—'}</td>
                        <td class="px-4 py-3">
                            {#if agent.workflow_id}
                                <a href={`/workflows/${agent.workflow_id}`} class="text-primary hover:underline">
                                    {agent.workflow_id}
                                </a>
                            {:else}
                                <span class="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                                    Not Connected
                                </span>
                            {/if}
                        </td>
                        <td class="px-4 py-3">
                            <button
                                role="switch"
                                aria-checked={agent.trigger_enabled}
                                aria-label={`Toggle triggers for ${agent.name}`}
                                onclick={() => handleTriggerToggle(agent, !agent.trigger_enabled)}
                                class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors {agent.trigger_enabled ? 'bg-primary' : 'bg-muted'}"
                            >
                                <span class="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform {agent.trigger_enabled ? 'translate-x-[1.15rem]' : 'translate-x-1'}"></span>
                            </button>
                        </td>
                        <td class="px-4 py-3">
                            <div class="flex items-center gap-2">
                                <span
                                    class="text-xs px-2 py-0.5 rounded-full font-medium {agent.socket_mode_enabled
                                        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                        : agent.has_app_token
                                          ? 'bg-muted text-muted-foreground'
                                          : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'}"
                                >
                                    {agent.socket_mode_enabled ? 'Active' : agent.has_app_token ? 'Inactive' : 'No App Token'}
                                </span>
                                <button
                                    onclick={() => handleSocketToggle(agent)}
                                    disabled={socketBusyId === agent.id}
                                    aria-label={agent.socket_mode_enabled ? 'Stop Socket Mode' : 'Start Socket Mode'}
                                    class="p-1 rounded hover:bg-muted transition-colors disabled:opacity-50"
                                >
                                    <Icon
                                        icon={socketBusyId === agent.id
                                            ? 'solar:refresh-bold'
                                            : agent.socket_mode_enabled
                                              ? 'solar:stop-circle-linear'
                                              : 'solar:play-circle-linear'}
                                        width={16}
                                        class={socketBusyId === agent.id ? 'animate-spin' : ''}
                                    />
                                </button>
                            </div>
                        </td>
                        <td class="px-4 py-3 text-right whitespace-nowrap">
                            <Button variant="ghost" size="sm" onclick={() => (testingAgent = agent)}>Test</Button>
                            <Button variant="ghost" size="sm" onclick={() => (editingAgent = agent)}>Edit</Button>
                            <Button variant="ghost" size="sm" onclick={() => (deletingAgent = agent)}>Delete</Button>
                        </td>
                    </tr>
                {/each}
            </tbody>
        </table>
    </div>
{/if}

<SlackSetupGuide isOpen={isGuideOpen} onOpenChange={(open) => (isGuideOpen = open)} />

{#if editingAgent}
    <SlackAgentEditor
        agent={editingAgent}
        isOpen={editingAgent !== null}
        onOpenChange={(open) => { if (!open) editingAgent = null }}
        onUpdated={updateAgent}
    />
{/if}

{#if testingAgent}
    <SlackTestConnection
        agent={testingAgent}
        isOpen={testingAgent !== null}
        onOpenChange={(open) => { if (!open) testingAgent = null }}
    />
{/if}

<ConfirmationModal
    isOpen={deletingAgent !== null}
    onClose={() => (deletingAgent = null)}
    onConfirm={handleDelete}
    title="Delete Slack Agent"
    message={`Are you sure you want to delete "${deletingAgent?.name}"? This action cannot be undone.`}
    confirmText="Delete"
    isDanger={true}
/>
