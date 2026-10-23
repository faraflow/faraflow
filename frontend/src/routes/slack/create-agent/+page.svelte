<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { onMount } from 'svelte'
    import { goto } from '$app/navigation'
    import { toast } from 'svelte-sonner'
    import Header from '$lib/components/Header.svelte'
    import { createSlackAgent, associateWorkflow, getWorkflows } from '$lib/utils/api'
    import type { WorkflowResponse } from '$lib/types/api_types/workflowSchemas'
    import { SpurType } from '$lib/types/api_types/workflowSchemas'

    let workflows = $state<WorkflowResponse[]>([])
    let isLoading = $state(true)
    let isSubmitting = $state(false)
    let isAssociating = $state(false)

    // Form fields
    let name = $state('')
    let selectedWorkflowId = $state('')
    let botToken = $state('')
    let userToken = $state('')
    let appToken = $state('')
    let triggerOnMention = $state(true)
    let triggerOnDM = $state(true)
    let triggerOnChannel = $state(false)
    let keywords = $state('')

    onMount(async () => {
        try {
            const data = await getWorkflows()
            workflows = [...data].sort(
                (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
            )
        } catch {
            toast.error('Failed to load workflows')
        } finally {
            isLoading = false
        }
    })

    async function handleSubmit() {
        if (!name.trim()) { toast.error('Please enter a name for the agent'); return }
        if (!botToken.trim()) { toast.error('Bot Token is required'); return }
        if (!selectedWorkflowId) { toast.error('Please select a workflow'); return }

        try {
            isSubmitting = true

            const keywordsArray = keywords.split(',').map(k => k.trim()).filter(k => k.length > 0)

            const agent = await createSlackAgent(name.trim(), {
                workflow_id: selectedWorkflowId,
                trigger_enabled: true,
                trigger_on_mention: triggerOnMention,
                trigger_on_direct_message: triggerOnDM,
                trigger_on_channel_message: triggerOnChannel,
                trigger_keywords: keywordsArray,
                bot_token: botToken.trim(),
                user_token: userToken.trim() || undefined,
                app_token: appToken.trim() || undefined,
            })

            if (!agent) {
                toast.error('Failed to create agent')
                return
            }

            // Ensure workflow association
            if (agent.id && (!agent.workflow_id || agent.workflow_id !== selectedWorkflowId)) {
                try {
                    isAssociating = true
                    await associateWorkflow(agent.id, selectedWorkflowId)
                    await new Promise(resolve => setTimeout(resolve, 500))
                } catch (err) {
                    console.error('Error associating workflow:', err)
                } finally {
                    isAssociating = false
                }
            }

            toast.success('Slack agent created successfully!')
            goto('/dashboard')
        } catch (err: any) {
            const detail = err?.response?.data?.detail
            toast.error(detail ? `Error: ${JSON.stringify(detail)}` : 'Failed to create agent')
        } finally {
            isSubmitting = false
        }
    }

    const chatbotWorkflows = $derived(
        workflows.filter(w => w.definition?.spur_type === SpurType.CHATBOT || !w.definition?.spur_type)
    )
</script>

<svelte:head>
    <title>Create Slack Agent - Faraflow</title>
</svelte:head>

<div class="min-h-screen bg-background flex flex-col">
    <div class="p-6">
        <div class="max-w-3xl mx-auto">
            <button
                onclick={() => goto('/dashboard')}
                class="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-6 transition-colors"
            >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 19-7-7 7-7"/><path d="M19 12H5"/></svg>
                Back to Dashboard
            </button>

            {#if isLoading}
                <div class="flex justify-center py-16">
                    <div class="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full"></div>
                </div>
            {:else if isAssociating}
                <div class="flex flex-col items-center gap-4 py-16">
                    <div class="animate-spin h-10 w-10 border-2 border-primary border-t-transparent rounded-full"></div>
                    <p class="text-muted-foreground">Finalizing agent setup...</p>
                </div>
            {:else}
                <div class="border border-border rounded-xl p-8 space-y-8">
                    <div>
                        <h1 class="text-2xl font-bold mb-1">Create Slack Agent</h1>
                        <p class="text-sm text-muted-foreground">Configure your agent to respond in Slack channels and DMs</p>
                    </div>

                    <!-- Basic Info -->
                    <div class="space-y-4">
                        <h2 class="text-base font-semibold border-b border-border pb-2">Basic Information</h2>
                        <div>
                            <label class="block text-sm font-medium mb-1.5">Agent Name *</label>
                            <input type="text" bind:value={name} placeholder="My Slack Bot" class="w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring" />
                        </div>
                        <div>
                            <label class="block text-sm font-medium mb-1.5">Workflow *</label>
                            <select bind:value={selectedWorkflowId} class="w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring">
                                <option value="">Select a workflow...</option>
                                {#each chatbotWorkflows as wf}
                                    <option value={wf.id}>{wf.name}</option>
                                {/each}
                            </select>
                        </div>
                    </div>

                    <!-- Trigger Configuration -->
                    <div class="space-y-4">
                        <h2 class="text-base font-semibold border-b border-border pb-2">Trigger Configuration</h2>
                        <div class="space-y-3">
                            {#each [
                                { label: 'Trigger on @mention', bind: 'triggerOnMention' },
                                { label: 'Trigger on Direct Messages', bind: 'triggerOnDM' },
                                { label: 'Trigger on all channel messages', bind: 'triggerOnChannel' },
                            ] as trigger}
                                <label class="flex items-center gap-3 cursor-pointer">
                                    {#if trigger.bind === 'triggerOnMention'}
                                        <button
                                            role="switch"
                                            aria-checked={triggerOnMention}
                                            onclick={() => (triggerOnMention = !triggerOnMention)}
                                            class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors {triggerOnMention ? 'bg-primary' : 'bg-muted'}"
                                        >
                                            <span class="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform {triggerOnMention ? 'translate-x-4' : 'translate-x-1'}"></span>
                                        </button>
                                    {:else if trigger.bind === 'triggerOnDM'}
                                        <button
                                            role="switch"
                                            aria-checked={triggerOnDM}
                                            onclick={() => (triggerOnDM = !triggerOnDM)}
                                            class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors {triggerOnDM ? 'bg-primary' : 'bg-muted'}"
                                        >
                                            <span class="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform {triggerOnDM ? 'translate-x-4' : 'translate-x-1'}"></span>
                                        </button>
                                    {:else}
                                        <button
                                            role="switch"
                                            aria-checked={triggerOnChannel}
                                            onclick={() => (triggerOnChannel = !triggerOnChannel)}
                                            class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors {triggerOnChannel ? 'bg-primary' : 'bg-muted'}"
                                        >
                                            <span class="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform {triggerOnChannel ? 'translate-x-4' : 'translate-x-1'}"></span>
                                        </button>
                                    {/if}
                                    <span class="text-sm">{trigger.label}</span>
                                </label>
                            {/each}

                            <div>
                                <label class="block text-sm font-medium mb-1.5">Keywords (comma-separated, optional)</label>
                                <input type="text" bind:value={keywords} placeholder="help, support, question" class="w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring" />
                            </div>
                        </div>
                    </div>

                    <!-- Tokens -->
                    <div class="space-y-4">
                        <h2 class="text-base font-semibold border-b border-border pb-2">Slack Tokens</h2>
                        <div class="space-y-4">
                            <div>
                                <label class="block text-sm font-medium mb-1.5">Bot Token * <span class="text-muted-foreground font-normal">(starts with xoxb-)</span></label>
                                <input type="password" bind:value={botToken} placeholder="xoxb-..." class="w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring font-mono" />
                            </div>
                            <div>
                                <label class="block text-sm font-medium mb-1.5">App Token <span class="text-muted-foreground font-normal">(optional, for Socket Mode, starts with xapp-)</span></label>
                                <input type="password" bind:value={appToken} placeholder="xapp-..." class="w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring font-mono" />
                            </div>
                            <div>
                                <label class="block text-sm font-medium mb-1.5">User Token <span class="text-muted-foreground font-normal">(optional, starts with xoxp-)</span></label>
                                <input type="password" bind:value={userToken} placeholder="xoxp-..." class="w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring font-mono" />
                            </div>
                        </div>
                    </div>

                    <!-- Actions -->
                    <div class="flex gap-3 pt-2">
                        <button onclick={() => goto('/dashboard')} class="px-4 py-2 rounded-md border border-border text-sm hover:bg-muted transition-colors">
                            Cancel
                        </button>
                        <button
                            onclick={handleSubmit}
                            disabled={isSubmitting}
                            class="px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm hover:bg-primary/90 disabled:opacity-50 transition-colors"
                        >
                            {isSubmitting ? 'Creating...' : 'Create Agent'}
                        </button>
                    </div>
                </div>
            {/if}
        </div>
    </div>
</div>
