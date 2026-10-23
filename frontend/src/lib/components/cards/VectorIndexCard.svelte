<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import type { VectorIndexResponseSchema } from '$lib/types/api_types/ragSchemas'

    interface Props {
        index: VectorIndexResponseSchema
        onClick?: (id: string) => void
    }

    let { index, onClick }: Props = $props()

    const statusColor = $derived(
        index.status === 'ready'
            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
            : index.status === 'failed'
              ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
              : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
    )
</script>

<button
    onclick={() => onClick?.(index.id)}
    class="text-left w-full border border-border rounded-xl overflow-hidden hover:border-primary/50 hover:shadow-sm transition-all bg-gradient-to-br from-background to-muted/30"
>
    <div class="p-6">
        <h2 class="text-lg font-semibold mb-1">{index.name}</h2>
        {#if index.description}
            <p class="text-sm text-muted-foreground mb-3">{index.description}</p>
        {/if}
        <div class="flex flex-col gap-1.5 text-sm">
            <div class="flex items-center gap-2 text-muted-foreground">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>
                Model: {index.embedding_model}
            </div>
            <div class="flex items-center gap-2 text-muted-foreground">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                {index.document_count} Documents
            </div>
            <div class="flex items-center gap-2 text-muted-foreground">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/></svg>
                {index.chunk_count} Chunks
            </div>
            <span class="text-xs px-2 py-0.5 rounded-full font-medium w-fit capitalize {statusColor}">
                {index.status}
            </span>
        </div>
    </div>
</button>
