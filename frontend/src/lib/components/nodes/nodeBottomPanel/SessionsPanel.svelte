<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import Icon from '@iconify/svelte'
    import { format } from 'date-fns'
    import { Button } from '$lib/components/ui/button'
    import { listSessions } from '$lib/utils/api'
    import { flowStore } from '$lib/stores/flow.svelte'
    import type { SessionResponse } from '$lib/types/api_types/sessionSchemas'

    const PAGE_SIZE = 50

    let sessions = $state<SessionResponse[]>([])
    let page = $state(1)
    let hasMore = $state(false)
    let loading = $state(false)
    let loadingMore = $state(false)

    async function fetchPage(p: number, append = false) {
        const workflowId = flowStore.workflowID
        if (!workflowId) return
        if (append) loadingMore = true
        else loading = true
        try {
            const skip = (p - 1) * PAGE_SIZE
            const result = await listSessions(skip, PAGE_SIZE, undefined, workflowId)
            sessions = append ? [...sessions, ...result.sessions] : result.sessions
            page = p
            hasMore = result.sessions.length === PAGE_SIZE
        } catch (err) {
            console.error('Error loading sessions:', err)
        } finally {
            loading = false
            loadingMore = false
        }
    }

    async function loadMore() {
        await fetchPage(page + 1, true)
    }

    $effect(() => {
        if (flowStore.workflowID) fetchPage(1)
    })

    function formatCreatedAt(isoStr?: string): string {
        if (!isoStr) return '—'
        try { return format(Date.parse(isoStr + 'Z'), 'MMM d, HH:mm:ss') }
        catch { return isoStr }
    }
</script>

<div class="flex flex-col h-full min-h-0">
    <div class="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-0">
        <div class="flex items-center justify-end">
            <Button
                variant="ghost"
                size="icon"
                class="h-8 w-8 shrink-0"
                title="Reload sessions"
                onclick={() => fetchPage(1)}
            >
                <Icon icon="solar:refresh-linear" width={15} class="text-muted-foreground {loading ? 'animate-spin' : ''}" />
            </Button>
        </div>

        {#if loading && sessions.length === 0}
            <div class="flex items-center justify-center py-12 gap-2 text-muted-foreground">
                <Icon icon="solar:refresh-bold" width={20} class="animate-spin opacity-50" />
                <span class="text-sm">Loading sessions…</span>
            </div>
        {:else if sessions.length === 0}
            <div class="flex flex-col items-center justify-center py-12 gap-2 text-muted-foreground">
                <Icon icon="solar:users-group-rounded-linear" width={32} class="opacity-30" />
                <p class="text-sm">No sessions yet. Chat with this workflow to create one.</p>
            </div>
        {:else}
            <div class="border rounded-lg overflow-x-auto">
                <table class="w-full text-sm">
                    <thead class="bg-muted/50 border-b">
                        <tr>
                            <th class="px-3 py-2 text-left font-medium text-muted-foreground w-24">Session ID</th>
                            <th class="px-3 py-2 text-left font-medium text-muted-foreground w-24">User ID</th>
                            <th class="px-3 py-2 text-left font-medium text-muted-foreground w-36">Created</th>
                            <th class="px-3 py-2 text-left font-medium text-muted-foreground w-24">Messages</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each sessions as session (session.id)}
                            <tr class="border-b last:border-0">
                                <td class="px-3 py-2 font-mono text-muted-foreground">{session.id}</td>
                                <td class="px-3 py-2 font-mono text-muted-foreground">{session.user_id}</td>
                                <td class="px-3 py-2 text-muted-foreground whitespace-nowrap">
                                    {formatCreatedAt(session.created_at)}
                                </td>
                                <td class="px-3 py-2 text-muted-foreground">{session.messages.length}</td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>

            {#if hasMore}
                <div class="flex justify-center py-2">
                    <Button
                        variant="outline"
                        size="sm"
                        class="text-xs"
                        disabled={loadingMore}
                        onclick={loadMore}
                    >
                        {#if loadingMore}
                            <Icon icon="solar:refresh-bold" width={12} class="mr-1.5 animate-spin" />
                            Loading…
                        {:else}
                            Load more
                        {/if}
                    </Button>
                </div>
            {/if}
        {/if}
    </div>
</div>
