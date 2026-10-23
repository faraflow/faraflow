<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import Icon from '@iconify/svelte'
    import FaraflowLogo from '$lib/components/FaraflowLogo.svelte'
    import { formatDistanceStrict } from 'date-fns'
    import { goto } from '$app/navigation'
    import { page } from '$app/state'
    import { onMount } from 'svelte'

    import { Button } from '$lib/components/ui/button'
    import * as DropdownMenu from '$lib/components/ui/dropdown-menu'
    import { Input } from '$lib/components/ui/input'

    import SpurTypeChip from '$lib/components/SpurTypeChip.svelte'
    import ConfirmationModal from '$lib/components/modals/ConfirmationModal.svelte'
    import DeployModal from '$lib/components/modals/DeployModal.svelte'
    import HelpModal from '$lib/components/modals/HelpModal.svelte'
    import RunModal from '$lib/components/modals/RunModal.svelte'
    import SettingsModal from '$lib/components/modals/SettingsModal.svelte'

    import { flowStore } from '$lib/stores/flow.svelte'
    import { nodeTypesStore } from '$lib/stores/nodeTypes.svelte'
    import { preferencesStore } from '$lib/stores/preferences.svelte'
    import { sidebarPanels } from '$lib/stores/sidebarPanels.svelte'
    import { saveWorkflow } from '$lib/actions/saveWorkflow.svelte'
    import { getRunStatus, getWorkflow, getWorkflowVersions, updateWorkflow } from '$lib/utils/api'
    import { apiKey } from '$lib/stores/apiKey.svelte'
    import type { WorkflowVersionResponse } from '$lib/types/api_types/workflowSchemas'

    interface Props {
        activePage: 'dashboard' | 'workflow' | 'evals' | 'trace' | 'runs' | 'rag' | 'tools' | 'sessions' | 'datasets'
        associatedWorkflowId?: string
        runId?: string
        handleDownloadImage?: () => void
        onExecute?: (inputs: Record<string, any>) => Promise<void>
        showChatToggle?: boolean
    }

    let {
        activePage,
        associatedWorkflowId,
        runId,
        handleDownloadImage,
        onExecute,
        showChatToggle = false,
    }: Props = $props()

    // Modal state
    let isDeployModalOpen = $state(false)
    let isVersionHistoryOpen = $state(false)
    let isHelpModalOpen = $state(false)
    let isSettingsModalOpen = $state(false)
    let isConfirmationOpen = $state(false)

    // Version history
    let workflowVersions = $state<WorkflowVersionResponse[]>([])
    let isLoadingVersions = $state(false)

    // Alert
    let alertMessage = $state('')
    let alertVisible = $state(false)
    let alertTimeout: ReturnType<typeof setTimeout>

    function showAlert(message: string) {
        alertMessage = message
        alertVisible = true
        clearTimeout(alertTimeout)
        alertTimeout = setTimeout(() => { alertVisible = false }, 3000)
    }

    // Reactive from store
    const projectName = $derived(flowStore.projectName)
    const workflowId = $derived(flowStore.workflowID)
    const spurType = $derived(flowStore.spurType)
    const isRunModalOpen = $derived(flowStore.isRunModalOpen)

    // Page title
    $effect(() => {
        if (activePage === 'workflow' || activePage === 'trace' || activePage === 'runs') {
            document.title = `${projectName} - Faraflow`
        } else if (activePage === 'dashboard') {
            document.title = 'Dashboard - Faraflow'
        } else if (activePage === 'rag') {
            document.title = 'RAG - Faraflow'
        }
    })

    // Fetch versions when panel opens
    $effect(() => {
        if (!isVersionHistoryOpen || !workflowId) return
        isLoadingVersions = true
        getWorkflowVersions(workflowId)
            .then((v) => { workflowVersions = v })
            .catch(() => showAlert('Error fetching versions'))
            .finally(() => { isLoadingVersions = false })
    })

    // Keyboard shortcut: Cmd/Ctrl+Enter to run
    function handleKeydown(e: KeyboardEvent) {
        if (activePage !== 'workflow') return
        if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
            e.preventDefault()
            flowStore.setRunModalOpen(true)
        }
    }

    async function handleDownloadWorkflow() {
        if (!workflowId) return
        try {
            const workflow = await getWorkflow(workflowId)
            const blob = new Blob([JSON.stringify({ name: workflow.name, definition: workflow.definition, description: workflow.description }, null, 2)], { type: 'application/json' })
            const url = URL.createObjectURL(blob)
            const a = Object.assign(document.createElement('a'), { href: url, download: `${projectName.replace(/\s+/g, '_')}.json` })
            document.body.appendChild(a)
            a.click()
            document.body.removeChild(a)
            URL.revokeObjectURL(url)
        } catch {
            showAlert('Error downloading workflow')
        }
    }

    async function handleDownloadTrace() {
        if (!runId) return
        try {
            showAlert('Preparing trace data...')
            const run = await getRunStatus(runId)
            const blob = new Blob([JSON.stringify(run, null, 2)], { type: 'application/json' })
            const url = URL.createObjectURL(blob)
            const a = Object.assign(document.createElement('a'), { href: url, download: `trace_${run.id}.json` })
            document.body.appendChild(a)
            a.click()
            document.body.removeChild(a)
            URL.revokeObjectURL(url)
            showAlert('Trace downloaded successfully')
        } catch {
            showAlert('Error downloading trace')
        }
    }

    // File upload (overwrite workflow)
    let pendingWorkflowData: any = $state(null)

    function handleFileUpload() {
        const input = document.createElement('input')
        input.type = 'file'
        input.accept = '.json'
        input.onchange = async (e) => {
            const file = (e.target as HTMLInputElement).files?.[0]
            if (!file) return
            try {
                const text = await file.text()
                pendingWorkflowData = JSON.parse(text)
                isConfirmationOpen = true
            } catch {
                showAlert('Invalid JSON file')
            }
        }
        input.click()
    }

    async function handleConfirmOverwrite() {
        if (!pendingWorkflowData || !workflowId || !nodeTypesStore.data) return
        try {
            // Persist to DB first using the raw uploaded definition — no store
            // reconstruction, no race with the auto-save effect.
            await updateWorkflow(workflowId, {
                name: flowStore.projectName,
                description: '',
                definition: pendingWorkflowData.definition,
            })
            // Only update visual state after the save is confirmed.
            flowStore.initializeFlow({
                workflowID: workflowId,
                definition: pendingWorkflowData.definition,
                name: flowStore.projectName,
                nodeTypes: nodeTypesStore.data,
            })
            showAlert('Workflow imported successfully')
        } catch (err) {
            console.error('Import workflow failed:', err)
            showAlert('Failed to import workflow — see console for details')
        } finally {
            pendingWorkflowData = null
            isConfirmationOpen = false
        }
    }

</script>

<svelte:window onkeydown={handleKeydown} />

<!-- Alert toast -->
{#if alertVisible}
    <div class="fixed bottom-4 right-4 z-50 rounded-lg bg-foreground px-4 py-2 text-background text-sm shadow-lg">
        {alertMessage}
    </div>
{/if}

<ConfirmationModal
    isOpen={isConfirmationOpen}
    onClose={() => { isConfirmationOpen = false }}
    onConfirm={handleConfirmOverwrite}
    title="Overwrite Workflow"
    message={`Are you sure you want to overwrite the current workflow with "${pendingWorkflowData?.name}"? This action cannot be undone.`}
    confirmText="Overwrite"
    isDanger
/>

<nav class="h-12 border-b bg-background shadow-sm flex items-center px-4 gap-2">
    <!-- Brand -->
    <div class="flex items-center gap-2 min-w-fit">
        {#if activePage === 'dashboard'}
            <span aria-label="Faraflow"><FaraflowLogo shiftDown={4.4} /></span>
        {:else}
            <a href="/dashboard" class="hover:opacity-70 transition-opacity" aria-label="Faraflow home"><FaraflowLogo shiftDown={4.4} /></a>
        {/if}
    </div>

    <!-- Workflow title input -->
    {#if activePage === 'workflow' || activePage === 'trace' || activePage === 'runs'}
        <div class="flex items-center gap-2 px-2">
            {#if spurType}
                <SpurTypeChip {spurType} showText={false} />
            {/if}
            <Input
                class="h-8 w-48 text-sm"
                type="text"
                placeholder="Project Name"
                value={projectName}
                oninput={(e) => {
                    flowStore.setProjectName((e.target as HTMLInputElement).value)
                    saveWorkflow()
                }}
                onkeydown={(e) => {
                    if (e.key === 'Enter') (e.target as HTMLInputElement).blur()
                }}
                disabled={activePage !== 'workflow'}
            />
        </div>
    {/if}

    <!-- Nav links -->
    <div class="flex items-center gap-1 rounded-full bg-muted px-3 h-8 ml-2">
        <a
            href="/dashboard"
            class="text-sm px-2 py-0.5 rounded-full transition-colors {activePage === 'dashboard' ? 'font-medium' : 'text-muted-foreground hover:text-foreground'}"
        >Dashboard</a>
        {#if activePage === 'workflow'}
            <span class="text-sm px-2 py-0.5 font-medium">Editor</span>
        {/if}
        {#if activePage === 'trace'}
            <span class="text-sm px-2 py-0.5 font-medium">Trace</span>
        {/if}
        <a
            href="/rag"
            class="text-sm px-2 py-0.5 rounded-full transition-colors {activePage === 'rag' ? 'font-medium' : 'text-muted-foreground hover:text-foreground'}"
        >RAG</a>
        <a
            href="/tools"
            class="text-sm px-2 py-0.5 rounded-full transition-colors {activePage === 'tools' ? 'font-medium' : 'text-muted-foreground hover:text-foreground'}"
        >Tools</a>
        <a
            href="/evals"
            class="text-sm px-2 py-0.5 rounded-full transition-colors {activePage === 'evals' ? 'font-medium' : 'text-muted-foreground hover:text-foreground'}"
        >Evals</a>
        <a
            href="/datasets"
            class="text-sm px-2 py-0.5 rounded-full transition-colors {activePage === 'datasets' ? 'font-medium' : 'text-muted-foreground hover:text-foreground'}"
        >Datasets</a>
    </div>

    <div class="ml-auto flex items-center gap-1">
        <!-- Workflow editor actions -->
        {#if activePage === 'workflow'}
            <div class="flex items-center gap-0 rounded-full bg-muted px-1 h-10">
                <!-- Chat panel toggle — only shown for chatbot workflows -->
                {#if showChatToggle}
                    <Button
                        variant="header_toggle"
                        active={sidebarPanels.isOpen('chat')}
                        onclick={() => sidebarPanels.toggle('chat')}
                        title="Chat"
                    >
                        <Icon icon="solar:chat-square-linear" width={18} />
                    </Button>
                {/if}

                <!-- Runs panel toggle -->
                <Button
                    variant="header_toggle"
                    active={sidebarPanels.isOpen('runs')}
                    onclick={() => sidebarPanels.toggle('runs')}
                    title="Runs"
                >
                    <Icon icon="solar:playlist-linear" width={18} />
                </Button>

                <!-- Nodes overview toggle -->
                <Button
                    variant="header_toggle"
                    active={sidebarPanels.isOpen('nodes')}
                    onclick={() => sidebarPanels.toggle('nodes')}
                    title="Node Overview"
                >
                    <Icon icon="solar:list-check-linear" width={18} />
                </Button>
            </div>
                    <!-- Settings + Help (always visible) -->
            <div class="flex items-center gap-0 rounded-full bg-muted px-1 h-10 ml-1">

                <!-- Version history dropdown -->
                <DropdownMenu.Root bind:open={isVersionHistoryOpen}>
                    <DropdownMenu.Trigger>
                        <Button variant="ghost" size="icon" class="rounded-full h-8 w-8" title="Version History">
                            <Icon icon="solar:history-linear" width={18} />
                        </Button>
                    </DropdownMenu.Trigger>
                    <DropdownMenu.Content>
                        {#if isLoadingVersions}
                            <DropdownMenu.Item class="gap-2 opacity-60">
                                <Icon icon="svg-spinners:3-dots-fade" width={16} />
                                Fetching versions...
                            </DropdownMenu.Item>
                        {:else if workflowVersions.length === 0}
                            <DropdownMenu.Item class="opacity-60">No versions available</DropdownMenu.Item>
                        {:else}
                            {#each workflowVersions as version, i}
                                <DropdownMenu.Item class="flex justify-between gap-4">
                                    <span>Version {version.version} | {formatDistanceStrict(Date.parse(version.created_at + 'Z'), new Date(), { addSuffix: true })}</span>
                                    {#if i > 0}
                                        <Button
                                            size="sm" variant="ghost" class="h-6 text-xs"
                                            onclick={() => goto(`/version-diff/${workflowId}?left=${version.version}&right=${workflowVersions[0].version}`)}
                                        >
                                            <Icon icon="solar:document-add-linear" width={12} class="mr-1" />
                                            Compare
                                        </Button>
                                    {/if}
                                </DropdownMenu.Item>
                            {/each}
                            {#if workflowVersions.length >= 2}
                                <DropdownMenu.Separator />
                                <DropdownMenu.Item onclick={() => goto(`/version-diff/${workflowId}`)}>
                                    <Icon icon="solar:document-add-linear" width={14} class="mr-2" />
                                    Custom Compare
                                </DropdownMenu.Item>
                            {/if}
                        {/if}
                    </DropdownMenu.Content>
                </DropdownMenu.Root>

                <!-- Download dropdown -->
                <DropdownMenu.Root>
                    <DropdownMenu.Trigger>
                        <Button variant="ghost" size="icon" class="rounded-full h-8 w-8" title="Download">
                            <Icon icon="solar:download-linear" width={18} />
                        </Button>
                    </DropdownMenu.Trigger>
                    <DropdownMenu.Content>
                        <DropdownMenu.Item onclick={handleDownloadWorkflow}>
                            <Icon icon="solar:document-text-linear" width={14} class="mr-2" />
                            Download JSON
                        </DropdownMenu.Item>
                        <DropdownMenu.Item onclick={handleDownloadImage}>
                            <Icon icon="solar:gallery-linear" width={14} class="mr-2" />
                            Download Image
                        </DropdownMenu.Item>
                    </DropdownMenu.Content>
                </DropdownMenu.Root>

                <!-- Upload -->
                <Button variant="ghost" size="icon" class="rounded-full h-8 w-8" onclick={handleFileUpload} title="Upload Workflow">
                    <Icon icon="solar:upload-linear" width={18} />
                </Button>

                <!-- Deploy -->
                <Button variant="ghost" size="icon" class="rounded-full h-8 w-8" onclick={() => { isDeployModalOpen = true }} title="Deploy">
                    <Icon icon="solar:cloud-upload-linear" width={18} />
                </Button>
            </div>
        {/if}

        <!-- Trace toolbar -->
        {#if activePage === 'trace'}
            <div class="flex items-center gap-0 rounded-full bg-muted px-1 h-10">
                <!-- Runs panel toggle -->
                <Button
                    variant="header_toggle"
                    active={sidebarPanels.isOpen('runs')}
                    onclick={() => sidebarPanels.toggle('runs')}
                    title="Runs"
                >
                    <Icon icon="solar:playlist-linear" width={18} />
                </Button>

                <!-- Node overview toggle -->
                <Button
                    variant="header_toggle"
                    active={sidebarPanels.isOpen('nodes')}
                    onclick={() => sidebarPanels.toggle('nodes')}
                    title="Node Overview"
                >
                    <Icon icon="solar:list-check-linear" width={18} />
                </Button>

                {#if associatedWorkflowId}
                    <DropdownMenu.Root>
                        <DropdownMenu.Trigger>
                            <Button variant="ghost" size="icon" class="rounded-full h-8 w-8" title="Download">
                                <Icon icon="solar:download-linear" width={18} />
                            </Button>
                        </DropdownMenu.Trigger>
                        <DropdownMenu.Content>
                            <DropdownMenu.Item onclick={handleDownloadTrace}>
                                <Icon icon="solar:document-text-linear" width={14} class="mr-2" />
                                Download JSON
                            </DropdownMenu.Item>
                            <DropdownMenu.Item onclick={handleDownloadImage}>
                                <Icon icon="solar:gallery-linear" width={14} class="mr-2" />
                                Download Image
                            </DropdownMenu.Item>
                        </DropdownMenu.Content>
                    </DropdownMenu.Root>
                    <a href={`/workflows/${associatedWorkflowId}`}>
                        <Button variant="ghost" size="sm">Go To Workflow</Button>
                    </a>
                {/if}
            </div>
        {/if}

        {#if activePage === 'runs' && associatedWorkflowId}
            <a href={`/workflows/${associatedWorkflowId}`}>
                <Button variant="ghost" size="sm">Go To Workflow</Button>
            </a>
        {/if}

        <!-- Settings + Help (always visible) -->
        <div class="flex items-center gap-0 rounded-full bg-muted px-1 h-10 ml-1">
            <Button variant="ghost" size="icon" class="rounded-full h-8 w-8" onclick={() => { isSettingsModalOpen = true }} aria-label="Settings">
                <Icon icon="solar:settings-linear" width={18} />
            </Button>
            <Button variant="ghost" size="icon" class="rounded-full h-8 w-8" onclick={() => { isHelpModalOpen = true }} aria-label="Help">
                <Icon icon="solar:question-circle-linear" width={18} />
            </Button>
            <Button
                variant="ghost"
                size="icon"
                class="rounded-full h-8 w-8"
                onclick={() => { apiKey.current = '' }}
                aria-label="Log out"
                title="Log out"
            >
                <Icon icon="solar:logout-2-linear" width={18} />
            </Button>
        </div>
    </div>
</nav>

<!-- Modals -->
<RunModal
    isOpen={isRunModalOpen}
    onOpenChange={(v) => flowStore.setRunModalOpen(v)}
    onRun={async (inputs) => {
        await onExecute?.(inputs)
        flowStore.setRunModalOpen(false)
    }}
/>

<DeployModal
    isOpen={isDeployModalOpen}
    onOpenChange={(v) => { isDeployModalOpen = v }}
    {workflowId}
    testInput={flowStore.testInputs.find((r) => r.id.toString() === flowStore.selectedTestInputId) ?? flowStore.testInputs[0]}
/>

<HelpModal isOpen={isHelpModalOpen} onOpenChange={(v) => { isHelpModalOpen = v }} />
<SettingsModal isOpen={isSettingsModalOpen} onOpenChange={(v) => { isSettingsModalOpen = v }} />
