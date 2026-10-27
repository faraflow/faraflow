<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
        import Icon from '@iconify/svelte'
    import * as Dialog from '$lib/components/ui/dialog'
    import { Button } from '$lib/components/ui/button'
    import { Input } from '$lib/components/ui/input'
    import { mode } from 'mode-watcher'
    import { setMode } from 'mode-watcher'
    import { listApiKeyInfo, setApiKey, deleteApiKey, getProviders } from '$lib/utils/api'
    import { apiKeyStatus } from '$lib/stores/apiKeyStatus.svelte'

    interface Props {
        isOpen: boolean
        onOpenChange: (open: boolean) => void
        initialTab?: 'appearance' | 'api-keys'
    }

    let { isOpen, onOpenChange, initialTab = 'api-keys' }: Props = $props()

    type Tab = 'appearance' | 'api-keys'
    let activeTab = $state<Tab>('api-keys')

    // Sync tab when modal opens with a different initialTab
    $effect(() => {
        if (isOpen) activeTab = initialTab
    })

    // ESC key
    $effect(() => {
        if (!isOpen) return
        function onKeyDown(e: KeyboardEvent) {
            if (e.key === 'Escape') onOpenChange(false)
        }
        window.addEventListener('keydown', onKeyDown)
        return () => window.removeEventListener('keydown', onKeyDown)
    })

    // --- API Keys section ---

    interface ProviderParameter {
        name: string
        description: string
        required: boolean
        type: string
    }

    interface ProviderConfig {
        id: string
        name: string
        description: string
        category: string
        parameters: ProviderParameter[]
        icon: string
    }

    let providers = $state<ProviderConfig[]>([])
    let keys = $state<{ name: string; value: string }[]>([])
    let originalKeys = $state<{ name: string; value: string }[]>([])
    let openSections = $state<Record<string, boolean>>({ 'AI Models': true })

    async function fetchProviders() {
        try {
            const data = await getProviders()
            providers = Array.isArray(data) ? data : []
        } catch (err) {
            console.error('Error fetching providers:', err)
            providers = []
        }
    }

    async function fetchApiKeys() {
        try {
            const info = await listApiKeyInfo()
            const keyValues = info.map((k) => ({ name: k.name, value: k.value ?? '' }))
            keys = keyValues
            originalKeys = JSON.parse(JSON.stringify(keyValues))
        } catch (err) {
            console.error('Error fetching API keys:', err)
        }
    }

    // Load providers and keys the first time the modal is opened, not on every page load
    let hasLoaded = false
    $effect(() => {
        if (isOpen && !hasLoaded) {
            hasLoaded = true
            fetchProviders()
            fetchApiKeys()
        }
    })

    function updateKey(name: string, value: string) {
        keys = keys.map((k) => (k.name === name ? { ...k, value } : k))
    }

    function clearKeyInput(name: string) {
        keys = keys.map((k) => (k.name === name ? { ...k, value: '' } : k))
    }

    async function handleDeleteKey(name: string) {
        try {
            await deleteApiKey(name)
            await fetchApiKeys()
            apiKeyStatus.refresh().catch(() => {})
        } catch (err) {
            console.error('Error deleting API key:', err)
        }
    }

    async function saveApiKeys() {
        try {
            await Promise.all(
                keys.map(async ({ name, value }) => {
                    const orig = originalKeys.find((k) => k.name === name)
                    const trimmed = value.trim()
                    if (orig && trimmed !== orig.value) {
                        if (trimmed !== '') {
                            await setApiKey(name, trimmed)
                        } else {
                            await handleDeleteKey(name)
                        }
                    }
                })
            )
            await fetchApiKeys()
            apiKeyStatus.refresh().catch(() => {})
        } catch (err) {
            console.error('Error saving API keys:', err)
        }
    }

    const hasChanges = $derived(
        keys.some((k) => {
            const orig = originalKeys.find((o) => o.name === k.name)
            return orig && k.value.trim() !== orig.value
        })
    )

    const iconMap: Record<string, string> = {
        openai: 'logos:openai-icon',
        azure: 'logos:microsoft-azure',
        anthropic: 'solar:stars-bold',
        google: 'logos:google-icon',
        deepseek: 'solar:code-circle-bold',
        ifm: 'solar:cpu-bolt-bold',
        cohere: 'solar:magic-stick-3-bold',
        voyage: 'solar:rocket-bold',
        mistral: 'solar:stars-bold',
        pinecone: 'solar:database-bold',
        weaviate: 'solar:database-bold',
        qdrant: 'solar:database-bold',
        chroma: 'solar:database-minimalistic-bold',
        supabase: 'logos:supabase-icon',
        database: 'solar:database-bold',
    }

    function getProviderIcon(icon: string): string {
        return iconMap[icon] ?? iconMap.database
    }

    function toggleSection(title: string) {
        openSections = { ...openSections, [title]: !openSections[title] }
    }

    const llmProviders = $derived(providers.filter((p) => p.category === 'llm'))
    const vectorStoreProviders = $derived(providers.filter((p) => p.category === 'vectorstore'))
    const otherProviders = $derived(
        providers.filter((p) => !['vectorstore', 'llm'].includes(p.category))
    )

    function getKeyValue(name: string): string {
        return keys.find((k) => k.name === name)?.value ?? ''
    }
</script>

<Dialog.Root
    open={isOpen}
    onOpenChange={(open) => { if (!open) onOpenChange(false) }}
>
    <Dialog.Content class="max-w-3xl max-h-[90vh] flex flex-col p-0">
        <Dialog.Header class="px-6 py-4 border-b shrink-0">
            <Dialog.Title>Settings</Dialog.Title>
        </Dialog.Header>

        <!-- Tab bar -->
        <div class="flex border-b px-6 shrink-0">
            <!-- TODO: re-enable the Appearance tab (dark mode toggle) once dark mode looks right
            <button
                type="button"
                class="flex items-center gap-2 px-3 py-2.5 text-sm border-b-2 -mb-px transition-colors
                    {activeTab === 'appearance'
                        ? 'border-primary text-primary font-medium'
                        : 'border-transparent text-muted-foreground hover:text-foreground'}"
                onclick={() => (activeTab = 'appearance')}
            >
                <Icon icon="solar:palette-bold" width={16} />
                Appearance
            </button>
            -->
            <button
                type="button"
                class="flex items-center gap-2 px-3 py-2.5 text-sm border-b-2 -mb-px transition-colors
                    {activeTab === 'api-keys'
                        ? 'border-primary text-primary font-medium'
                        : 'border-transparent text-muted-foreground hover:text-foreground'}"
                onclick={() => (activeTab = 'api-keys')}
            >
                <Icon icon="solar:key-minimalistic-bold" width={16} />
                API Keys
            </button>
        </div>

        <!-- Body -->
        <div class="flex-1 overflow-y-auto px-6 py-4">
            {#if activeTab === 'appearance'}
                <!-- TODO: re-enable with the Appearance tab above
                <div class="space-y-4">
                    <div class="flex items-center justify-between p-4 rounded-xl bg-muted/40">
                        <div>
                            <p class="font-medium">Dark Mode</p>
                            <p class="text-sm text-muted-foreground">Toggle between light and dark theme</p>
                        </div>
                        <button
                            type="button"
                            aria-label="Toggle dark mode"
                            class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                                {$mode === 'dark' ? 'bg-primary' : 'bg-muted'}"
                            onclick={() => setMode($mode === 'dark' ? 'light' : 'dark')}
                            role="switch"
                            aria-checked={$mode === 'dark'}
                        >
                            <span
                                class="inline-block h-4 w-4 rounded-full bg-white shadow transition-transform
                                    {$mode === 'dark' ? 'translate-x-6' : 'translate-x-1'}"
                            ></span>
                        </button>
                    </div>
                </div>
                -->
            {:else}
                <!-- API Keys tab -->
                <div class="space-y-4">
                    {#snippet providerSection(title: string, description: string, icon: string, providerList: ProviderConfig[])}
                        {#if providerList.length > 0}
                            <div class="border rounded-xl overflow-hidden">
                                <button
                                    type="button"
                                    class="w-full flex items-center gap-3 px-4 py-3 bg-muted/30 hover:bg-muted/50 transition-colors text-left"
                                    onclick={() => toggleSection(title)}
                                >
                                    <Icon {icon} width={20} class="text-primary shrink-0" />
                                    <div class="flex-1">
                                        <p class="text-sm font-medium">{title}</p>
                                        <p class="text-xs text-muted-foreground">{description}</p>
                                    </div>
                                    <Icon
                                        icon={openSections[title] ? 'solar:alt-arrow-up-linear' : 'solar:alt-arrow-down-linear'}
                                        width={16}
                                        class="text-muted-foreground"
                                    />
                                </button>
                                {#if openSections[title]}
                                    <div class="divide-y">
                                        {#each providerList as provider}
                                            <div class="p-4 space-y-3">
                                                <div class="flex items-center gap-2">
                                                    <Icon icon={getProviderIcon(provider.icon)} width={20} />
                                                    <div>
                                                        <p class="text-sm font-medium">{provider.name}</p>
                                                        <p class="text-xs text-muted-foreground">{provider.description}</p>
                                                    </div>
                                                </div>
                                                {#each provider.parameters as param}
                                                    <div>
                                                        <p class="block text-xs text-muted-foreground mb-1">
                                                            {param.description}
                                                            {#if param.required}
                                                                <span class="text-destructive ml-0.5">*</span>
                                                            {/if}
                                                        </p>
                                                        <div class="flex gap-2">
                                                            <Input
                                                                type={param.type === 'password' ? 'password' : 'text'}
                                                                class="text-sm h-8"
                                                                placeholder="Enter {param.description.toLowerCase()}"
                                                                value={getKeyValue(param.name)}
                                                                oninput={(e) =>
                                                                    updateKey(param.name, (e.target as HTMLInputElement).value)}
                                                                onfocus={() => clearKeyInput(param.name)}
                                                            />
                                                            {#if getKeyValue(param.name)}
                                                                <Button
                                                                    variant="ghost"
                                                                    size="icon"
                                                                    class="h-8 w-8 shrink-0"
                                                                    onclick={() => handleDeleteKey(param.name)}
                                                                >
                                                                    <Icon icon="solar:close-circle-linear" width={14} />
                                                                </Button>
                                                            {/if}
                                                        </div>
                                                    </div>
                                                {/each}
                                            </div>
                                        {/each}
                                    </div>
                                {/if}
                            </div>
                        {/if}
                    {/snippet}

                    {@render providerSection('AI Models', 'Configure your AI model providers', 'solar:brain-bold', llmProviders)}
                    {@render providerSection('Vector Databases', 'Configure your vector database providers', 'solar:database-bold', vectorStoreProviders)}
                    {@render providerSection('Other Integrations', 'Configure additional service providers', 'solar:widget-bold', otherProviders)}

                    {#if providers.length === 0}
                        <p class="text-sm text-muted-foreground text-center py-8">Loading providers...</p>
                    {/if}
                </div>
            {/if}
        </div>

        <!-- Footer -->
        {#if activeTab === 'api-keys' && hasChanges}
            <div class="px-6 py-4 border-t flex justify-end gap-2 shrink-0">
                <Button
                    variant="outline"
                    onclick={() => {
                        keys = JSON.parse(JSON.stringify(originalKeys))
                    }}
                >
                    <Icon icon="solar:close-circle-bold" width={16} class="mr-1" />
                    Cancel
                </Button>
                <Button onclick={saveApiKeys}>
                    <Icon icon="solar:disk-bold" width={16} class="mr-1" />
                    Save Changes
                </Button>
            </div>
        {:else}
            <div class="px-6 py-4 border-t flex justify-end shrink-0">
                <Button variant="outline" onclick={() => onOpenChange(false)}>Close</Button>
            </div>
        {/if}
    </Dialog.Content>
</Dialog.Root>
