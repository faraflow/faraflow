<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { page } from '$app/stores'
    import { goto } from '$app/navigation'
    import { onMount } from 'svelte'
    import { getSession } from '$lib/utils/api'
    import Header from '$lib/components/Header.svelte'
    import LoadingSpinner from '$lib/components/LoadingSpinner.svelte'
    import Chat from '$lib/components/chat/Chat.svelte'
    import type { SessionResponse } from '$lib/types/api_types/sessionSchemas'

    const userId = $derived($page.params.userId)
    const sessionId = $derived($page.params.sessionId)

    let session = $state<SessionResponse | null>(null)
    let isLoading = $state(true)
    let error = $state<string | null>(null)

    onMount(async () => {
        if (sessionId) {
            await fetchSession()
        }
    })

    async function fetchSession() {
        try {
            isLoading = true
            error = null
            session = await getSession(sessionId)
        } catch (err) {
            console.error('Error fetching session:', err)
            error = 'Failed to fetch session. Please try again.'
        } finally {
            isLoading = false
        }
    }
</script>

<svelte:head>
    <title>Session Chat - Faraflow</title>
</svelte:head>

<div style="height: 100vh; display: flex; flex-direction: column;">
    <Header activePage="sessions" />

    <div class="flex flex-col gap-2 max-w-7xl w-full mx-auto pt-6 px-6 flex-1 overflow-hidden">
        <div class="flex items-center justify-between mb-4 flex-shrink-0">
            <div>
                <h1 class="text-xl font-bold">Session Chat</h1>
                <p class="text-sm text-muted-foreground">Session ID: {sessionId}</p>
            </div>
            <button
                onclick={() => goto(`/sessions/${userId}`)}
                class="flex items-center gap-2 px-3 py-2 rounded-md border border-border text-sm hover:bg-muted transition-colors"
            >
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 19-7-7 7-7"/><path d="M19 12H5"/></svg>
                Back to Sessions
            </button>
        </div>

        {#if isLoading}
            <LoadingSpinner />
        {:else if error}
            <div class="flex items-center justify-center h-full text-destructive">{error}</div>
        {:else}
            <div class="flex-1 border border-border rounded-xl overflow-hidden">
                <Chat
                    workflowID={session?.workflow_id}
                    sessionId={sessionId}
                />
            </div>
        {/if}
    </div>
</div>
