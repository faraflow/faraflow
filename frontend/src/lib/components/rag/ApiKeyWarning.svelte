<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    interface Props {
        requiredEnvVars: string[]
        apiKeys: Record<string, string>
        serviceName: string
    }

    let { requiredEnvVars, apiKeys, serviceName }: Props = $props()

    const missingVars = $derived(requiredEnvVars.filter((v) => !apiKeys[v]))
</script>

{#if missingVars.length > 0}
    <div class="mt-2 p-3 rounded-md bg-amber-50 border border-amber-200 dark:bg-amber-900/20 dark:border-amber-800 text-sm text-amber-800 dark:text-amber-300">
        <p class="font-medium">Missing API key{missingVars.length > 1 ? 's' : ''} for {serviceName}</p>
        <p class="mt-1">
            Set
            {#each missingVars as v, i}
                <code class="px-1 py-0.5 rounded bg-amber-100 dark:bg-amber-900/40 font-mono text-xs">{v}</code>{i < missingVars.length - 1 ? ', ' : ''}
            {/each}
            in <span class="font-medium">Settings → API Keys</span> before indexing, or indexing will fail.
        </p>
    </div>
{/if}
