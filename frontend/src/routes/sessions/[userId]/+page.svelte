<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { page } from '$app/stores'
    import { goto } from '$app/navigation'
    import { onMount } from 'svelte'
    import { formatDistanceToNow } from 'date-fns'
    import { listSessions, getWorkflow } from '$lib/utils/api'
    import Header from '$lib/components/Header.svelte'
    import LoadingSpinner from '$lib/components/LoadingSpinner.svelte'
    import type { SessionResponse } from '$lib/types/api_types/sessionSchemas'
    import type { WorkflowResponse } from '$lib/types/api_types/workflowSchemas'

    const userId = $derived($page.params.userId)

    let sessions = $state<SessionResponse[]>([])
    let workflows = $state<Record<string, WorkflowResponse>>({})
    let isLoading = $state(true)
    let isLoadingMore = $state(false)
    let hasMore = $state(false)
    let currentPage = $state(1)
    let error = $state<string | null>(null)

    onMount(() => {
        fetchSessions()
    })

    async function fetchSessions() {
        if (!userId) return
        try {
            isLoading = true
            error = null
            const data = await listSessions(0, 10, userId)
            sessions = data.sessions
            hasMore = data.total > data.sessions.length

            const wfMap: Record<string, WorkflowResponse> = {}
            await Promise.all(
                data.sessions.map(async (s: SessionResponse) => {
                    if (s.workflow_id) {
                        const wf = await getWorkflow(s.workflow_id)
                        wfMap[s.workflow_id] = wf
                    }
                })
            )
            workflows = wfMap
        } catch (err) {
            console.error('Error fetching sessions:', err)
            error = 'Failed to fetch sessions. Please try again.'
        } finally {
            isLoading = false
        }
    }

    async function handleLoadMore() {
        if (!userId) return
        try {
            isLoadingMore = true
            const nextPage = currentPage + 1
            const data = await listSessions((nextPage - 1) * 10, 10, userId)

            const wfMap = { ...workflows }
            await Promise.all(
                data.sessions.map(async (s: SessionResponse) => {
                    if (s.workflow_id && !wfMap[s.workflow_id]) {
                        const wf = await getWorkflow(s.workflow_id)
                        wfMap[s.workflow_id] = wf
                    }
                })
            )

            sessions = [...sessions, ...data.sessions]
            workflows = wfMap
            currentPage = nextPage
            hasMore = data.total > sessions.length
        } catch (err) {
            console.error('Error loading more:', err)
            error = 'Failed to load more sessions.'
        } finally {
            isLoadingMore = false
        }
    }

    function formatDate(dateStr: string) {
        return formatDistanceToNow(new Date(dateStr), { addSuffix: true })
    }
</script>

<svelte:head>
    <title>Sessions - Faraflow</title>
</svelte:head>

<div class="min-h-screen flex flex-col">
    <Header activePage="sessions" />

    <div class="flex flex-col gap-2 max-w-7xl w-full mx-auto pt-6 px-6 flex-1">
        <div class="flex items-center justify-between mb-6">
            <div>
                <h1 class="text-2xl font-bold">User Sessions</h1>
                <p class="text-sm text-muted-foreground">Viewing sessions for: {userId}</p>
            </div>
            <button
                onclick={() => goto('/dashboard')}
                class="flex items-center gap-2 px-3 py-2 rounded-md border border-border text-sm hover:bg-muted transition-colors"
            >
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 19-7-7 7-7"/><path d="M19 12H5"/></svg>
                Back to Dashboard
            </button>
        </div>

        {#if error}
            <div class="p-4 rounded-lg bg-destructive/10 text-destructive text-sm mb-4">{error}</div>
        {/if}

        {#if isLoading}
            <LoadingSpinner />
        {:else if sessions.length === 0}
            <div class="flex items-center justify-center py-16 text-muted-foreground">
                No sessions found for this user.
            </div>
        {:else}
            <div class="border border-border rounded-xl overflow-hidden">
                <table class="w-full text-sm">
                    <thead class="bg-muted/50 border-b border-border">
                        <tr>
                            <th class="text-left px-4 py-3 font-medium">Session ID</th>
                            <th class="text-left px-4 py-3 font-medium">Workflow</th>
                            <th class="text-left px-4 py-3 font-medium">Messages</th>
                            <th class="text-left px-4 py-3 font-medium">Created</th>
                            <th class="text-left px-4 py-3 font-medium">Last Updated</th>
                            <th class="text-left px-4 py-3 font-medium">Actions</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-border">
                        {#each sessions as session (session.id)}
                            <tr class="hover:bg-muted/30">
                                <td class="px-4 py-3 font-mono text-xs text-muted-foreground">{session.id.slice(0, 16)}...</td>
                                <td class="px-4 py-3">
                                    {#if session.workflow_id && workflows[session.workflow_id]}
                                        <button
                                            onclick={() => goto(`/workflows/${session.workflow_id}`)}
                                            class="text-xs px-2 py-1 rounded bg-muted hover:bg-muted/80 border border-border transition-colors"
                                        >
                                            {workflows[session.workflow_id].name}
                                        </button>
                                    {:else}
                                        <span class="text-muted-foreground">N/A</span>
                                    {/if}
                                </td>
                                <td class="px-4 py-3">
                                    <span class="text-xs px-2 py-1 rounded bg-muted border border-border">
                                        {session.messages.length} messages
                                    </span>
                                </td>
                                <td class="px-4 py-3 text-muted-foreground">{formatDate(session.created_at)}</td>
                                <td class="px-4 py-3 text-muted-foreground">{formatDate(session.updated_at)}</td>
                                <td class="px-4 py-3">
                                    <button
                                        onclick={() => goto(`/sessions/${userId}/${session.id}`)}
                                        class="p-1 rounded hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                                        title="View session"
                                    >
                                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>
                                    </button>
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>

            {#if hasMore}
                <div class="flex justify-center mt-4">
                    <button
                        onclick={handleLoadMore}
                        disabled={isLoadingMore}
                        class="flex items-center gap-2 px-4 py-2 rounded-md border border-border text-sm hover:bg-muted disabled:opacity-50 transition-colors"
                    >
                        {#if isLoadingMore}
                            <div class="animate-spin h-3 w-3 border-2 border-foreground border-t-transparent rounded-full"></div>
                            Loading...
                        {:else}
                            Load More
                        {/if}
                    </button>
                </div>
            {/if}
        {/if}
    </div>
</div>
