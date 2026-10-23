<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { onMount } from 'svelte'
    import Header from '$lib/components/Header.svelte'
    import StockTools from '$lib/components/StockTools.svelte'
    import SpecTools from '$lib/components/SpecTools.svelte'
    import { nodeTypesStore } from '$lib/stores/nodeTypes.svelte'

    let selectedTab = $state<'stock' | 'openapi'>('stock')

    onMount(async () => {
        if (nodeTypesStore.status === 'idle') {
            await nodeTypesStore.fetch()
        }
    })
</script>

<svelte:head>
    <title>Tools - Faraflow</title>
</svelte:head>

<div class="min-h-screen flex flex-col">
    <Header activePage="tools" />

    <div class="flex flex-col gap-4 max-w-7xl w-full mx-auto px-6 py-6 flex-1">
        <div>
            <h1 class="text-2xl font-bold">Tools</h1>
            <p class="text-sm text-muted-foreground mt-1">Create and manage tools for your workflows</p>
        </div>

        <!-- Tabs -->
        <div class="flex gap-1 border-b border-border">
            {#each [{ key: 'stock', label: 'Stock Tools' }, { key: 'openapi', label: 'OpenAPI Tools' }] as tab}
                <button
                    onclick={() => (selectedTab = tab.key as any)}
                    class="px-4 py-2 text-sm font-medium border-b-2 transition-colors
                        {selectedTab === tab.key
                            ? 'border-primary text-primary'
                            : 'border-transparent text-muted-foreground hover:text-foreground'}"
                >
                    {tab.label}
                </button>
            {/each}
        </div>

        <!-- Content -->
        <div class="py-2">
            {#if selectedTab === 'stock'}
                <StockTools />
            {:else}
                <SpecTools />
            {/if}
        </div>
    </div>
</div>
