<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import '../app.css'
    import { ModeWatcher } from 'mode-watcher'
    import FaraflowLogo from '$lib/components/FaraflowLogo.svelte'
    import { Toaster } from 'svelte-sonner'
    import { onMount } from 'svelte'
    import { preferencesStore } from '$lib/stores/preferences.svelte'
    import { sidebarPanels } from '$lib/stores/sidebarPanels.svelte'
    import { apiKey } from '$lib/stores/apiKey.svelte'

    let { children } = $props()
    let inputKey = $state('')
    let checking = $state(false)
    let error = $state('')

    onMount(() => {
        preferencesStore.load()
        sidebarPanels.load()
    })

    async function submitKey() {
        error = ''
        checking = true
        try {
            const res = await fetch(`${window.location.protocol}//${window.location.host}/api/wf/`, {
                headers: { 'Authorization': `Bearer ${inputKey}` },
            })
            if (res.status === 401) {
                error = 'Invalid API key. Please try again.'
            } else {
                apiKey.current = inputKey
            }
        } catch {
            error = 'Could not reach the server. Please try again.'
        } finally {
            checking = false
        }
    }
</script>

<ModeWatcher defaultMode="light" />
<Toaster richColors position="top-right" />

{#if !apiKey.current}
    <div class="key-gate">
        <h1><FaraflowLogo markSize={44} wordmarkWidth={150} /></h1>
        <p>Enter your API key to continue.</p>
        <form onsubmit={submitKey}>
            <input
                type="password"
                bind:value={inputKey}
                placeholder="API key"
                autocomplete="current-password"
                disabled={checking}
            />
            {#if error}
                <p class="error">{error}</p>
            {/if}
            <button type="submit" disabled={checking}>
                {checking ? 'Verifying…' : 'Continue'}
            </button>
        </form>
    </div>
{:else}
    {@render children()}
{/if}

<style lang="scss">
    .key-gate {
        @apply flex flex-col items-center justify-center min-h-screen gap-4;

        h1 {
            @apply text-2xl font-semibold;
        }

        p {
            @apply text-sm text-gray-500;
        }

        form {
            @apply flex flex-col gap-3 w-64;
        }

        input {
            @apply border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500;

            &:disabled {
                @apply opacity-50 cursor-not-allowed;
            }
        }

        .error {
            @apply text-sm text-red-500;
        }

        button {
            @apply bg-blue-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-blue-700;

            &:disabled {
                @apply opacity-50 cursor-not-allowed;
            }
        }
    }
</style>
