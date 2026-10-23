<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { onMount } from 'svelte'
    import { goto } from '$app/navigation'
    import Icon from '@iconify/svelte'
    import { formatDistanceToNow } from 'date-fns'

    import { Button } from '$lib/components/ui/button'
    import * as Dialog from '$lib/components/ui/dialog'
    import * as Accordion from '$lib/components/ui/accordion'

    import Header from '$lib/components/Header.svelte'
    import SpurTypeChip from '$lib/components/SpurTypeChip.svelte'
    import TemplateCard from '$lib/components/cards/TemplateCard.svelte'
    import ConfirmationModal from '$lib/components/modals/ConfirmationModal.svelte'
    import SlackAgentList from '$lib/components/slack/SlackAgentList.svelte'
    import { apiKeyStatus } from '$lib/stores/apiKeyStatus.svelte'

    import {
        getWorkflows,
        createWorkflow,
        deleteWorkflow,
        duplicateWorkflow,
        getWorkflowRuns,
        getTemplates,
        instantiateTemplate,
        listPausedWorkflows,
        takePauseAction,
        cancelWorkflow,
        getAllRuns,
    } from '$lib/utils/api'
    import { SpurType, type WorkflowResponse, type WorkflowCreateRequest, type WorkflowDefinition } from '$lib/types/api_types/workflowSchemas'
    import type { RunListItem, RunResponse } from '$lib/types/api_types/runSchemas'
    import type { PausedWorkflowResponse, ResumeActionRequest } from '$lib/types/api_types/pausedWorkflowSchemas'
    import HumanInputModal from '$lib/components/modals/HumanInputModal.svelte'

    // ── state ──────────────────────────────────────────────────────────────

    let workflows = $state<WorkflowResponse[]>([])
    let workflowRuns = $state<Record<string, RunResponse[]>>({})
    let templates = $state<any[]>([])
    let isLoadingWorkflows = $state(true)
    let isLoadingTemplates = $state(true)
    let highlightedWorkflowId = $state<string | null>(null)
    let workflowPage = $state(1)
    let hasMoreWorkflows = $state(false)
    let isLoadingMore = $state(false)
    let hasApiKeys = $state(true)
    let isLoadingApiKeys = $state(true)
    let slackAgentCount = $state(0)

    // "New Flow" modal
    let isNewSpurOpen = $state(false)
    let selectedSpurType = $state<SpurType>(SpurType.WORKFLOW)
    let isCreating = $state(false)

    // delete confirmation
    let deleteTargetWorkflow = $state<WorkflowResponse | null>(null)

    // alert
    let alertMsg = $state('')
    let alertVisible = $state(false)
    let alertTimeout: ReturnType<typeof setTimeout>

    // paused workflows (human approval)
    let pausedWorkflows = $state<PausedWorkflowResponse[]>([])
    let isLoadingPaused = $state(false)
    let selectedWorkflow = $state<PausedWorkflowResponse | null>(null)
    let isHumanInputModalOpen = $state(false)
    let humanInputDefaultAction = $state<'APPROVE' | 'DECLINE' | 'OVERRIDE'>('APPROVE')

    // recent traces
    let recentRuns = $state<RunListItem[]>([])
    let isLoadingRuns = $state(false)
    let traceFilter = $state<'all' | 'failed'>('all')
    const filteredTraces = $derived(
        traceFilter === 'failed' ? recentRuns.filter(r => r.status === 'FAILED') : recentRuns
    )

    // drag-and-drop
    let isDragActive = $state(false)

    function showAlert(msg: string) {
        alertMsg = msg
        alertVisible = true
        clearTimeout(alertTimeout)
        alertTimeout = setTimeout(() => { alertVisible = false }, 4000)
    }

    // ── data loading ───────────────────────────────────────────────────────

    async function loadWorkflowRuns(wfId: string): Promise<RunResponse[]> {
        try { return (await getWorkflowRuns(wfId)).slice(0, 5) } catch { return [] }
    }

    async function loadWorkflows(page = 1) {
        if (page === 1) isLoadingWorkflows = true
        try {
            const wfs = await getWorkflows(page)
            const runs = Object.fromEntries(
                await Promise.all(wfs.map(async (w) => [w.id, await loadWorkflowRuns(w.id)]))
            )
            if (page === 1) {
                workflows = wfs
                workflowRuns = runs
            } else {
                workflows = [...workflows, ...wfs]
                workflowRuns = { ...workflowRuns, ...runs }
            }
            workflowPage = page
            hasMoreWorkflows = wfs.length === 10
        } catch (e) {
            console.error('Error loading workflows', e)
        } finally {
            isLoadingWorkflows = false
        }
    }

    async function loadTemplates() {
        isLoadingTemplates = true
        try { templates = await getTemplates() }
        catch { templates = [] }
        finally { isLoadingTemplates = false }
    }

    async function checkApiKeys() {
        try {
            await apiKeyStatus.ensureLoaded()
            hasApiKeys = apiKeyStatus.hasAnyKey()
        } catch { hasApiKeys = true }
        finally { isLoadingApiKeys = false }
    }

    async function loadPausedWorkflows() {
        isLoadingPaused = true
        try { pausedWorkflows = await listPausedWorkflows() }
        catch { pausedWorkflows = [] }
        finally { isLoadingPaused = false }
    }

    async function loadRecentRuns() {
        isLoadingRuns = true
        try { recentRuns = await getAllRuns(1, 20, true) }
        catch { recentRuns = [] }
        finally { isLoadingRuns = false }
    }

    onMount(() => {
        loadWorkflows()
        loadTemplates()
        checkApiKeys()
        loadPausedWorkflows()
        loadRecentRuns()
    })

    // ── actions ────────────────────────────────────────────────────────────

    async function handleCreateSpur() {
        isCreating = true
        try {
            const label = selectedSpurType === SpurType.CHATBOT ? 'Chatbot' : 'Workflow'
            const created = await createWorkflow({
                name: `New ${label} ${new Date().toLocaleString()}`,
                description: '',
                definition: { nodes: [], links: [], test_inputs: [], spur_type: selectedSpurType },
            })
            isNewSpurOpen = false
            goto(`/workflows/${created.id}`)
        } catch { showAlert('Failed to create flow') }
        finally { isCreating = false }
    }

    async function handleImport() {
        const input = Object.assign(document.createElement('input'), { type: 'file', accept: '.json' })
        input.onchange = async (e: Event) => {
            const file = (e.target as HTMLInputElement).files?.[0]
            if (!file) return
            try {
                const json = JSON.parse(await file.text())
                const created = await createWorkflow({
                    name: `Imported Flow ${new Date().toLocaleString()}`,
                    description: json.description ?? '',
                    definition: json.definition as WorkflowDefinition,
                })
                goto(`/workflows/${created.id}`)
            } catch { showAlert('Failed to import – invalid JSON') }
        }
        input.click()
    }

    async function handleDuplicate(wf: WorkflowResponse) {
        try {
            const dup = await duplicateWorkflow(wf.id)
            workflows = [dup, ...workflows]
            workflowRuns = { ...workflowRuns, [dup.id]: [] }
            highlightedWorkflowId = dup.id
            setTimeout(() => { highlightedWorkflowId = null }, 2000)
        } catch { showAlert('Failed to duplicate workflow') }
    }

    async function handleDelete(wf: WorkflowResponse) {
        try {
            await deleteWorkflow(wf.id)
            workflows = workflows.filter((w) => w.id !== wf.id)
            deleteTargetWorkflow = null
        } catch { showAlert('Failed to delete workflow') }
    }

    async function handleUseTemplate(template: any) {
        try {
            const created = await instantiateTemplate(template)
            goto(`/workflows/${created.id}`)
        } catch { showAlert('Failed to instantiate template') }
    }

    async function handleLoadMore() {
        isLoadingMore = true
        await loadWorkflows(workflowPage + 1)
        isLoadingMore = false
    }

    async function handleQuickAction(workflow: PausedWorkflowResponse, action: 'APPROVE' | 'DECLINE') {
        try {
            const runId = workflow.run.id
            if (!runId) return showAlert('Cannot perform action: missing run ID')
            const req: ResumeActionRequest = {
                inputs: {},
                user_id: 'current-user',
                action,
                comments: `Quick ${action.toLowerCase()} from dashboard`,
            }
            await takePauseAction(runId, req)
            showAlert(`Workflow ${action.toLowerCase()}d successfully`)
            pausedWorkflows = await listPausedWorkflows()
        } catch { showAlert(`Failed to ${action.toLowerCase()} workflow`) }
    }

    async function handleCancelWorkflow(workflow: PausedWorkflowResponse) {
        const runId = workflow.run.id
        if (!runId) return showAlert('Cannot cancel: missing run ID')
        if (!window.confirm('Are you sure you want to cancel this workflow? This action cannot be undone.')) return
        try {
            await cancelWorkflow(runId)
            showAlert('Workflow canceled successfully')
            pausedWorkflows = await listPausedWorkflows()
        } catch { showAlert('Failed to cancel workflow') }
    }

    async function handleHumanInputSubmit(
        action: 'APPROVE' | 'DECLINE' | 'OVERRIDE',
        inputData: Record<string, any>,
        comments: string
    ) {
        if (!selectedWorkflow) return
        const runId = selectedWorkflow.run.id
        if (!runId) return showAlert('Cannot resume workflow: missing run ID')
        try {
            const req: ResumeActionRequest = { inputs: inputData, user_id: 'current-user', action, comments }
            await takePauseAction(runId, req)
            showAlert(`Workflow resumed with action: ${action}`)
            isHumanInputModalOpen = false
            selectedWorkflow = null
            pausedWorkflows = await listPausedWorkflows()
        } catch { showAlert('Failed to resume workflow') }
    }

    // ── drag-and-drop import ───────────────────────────────────────────────

    async function handleDrop(e: DragEvent) {
        e.preventDefault()
        isDragActive = false
        const file = e.dataTransfer?.files[0]
        if (!file || !file.name.endsWith('.json')) return
        try {
            const json = JSON.parse(await file.text())
            const created = await createWorkflow({
                name: `Imported Flow ${new Date().toLocaleString()}`,
                description: json.description ?? '',
                definition: json.definition as WorkflowDefinition,
            })
            goto(`/workflows/${created.id}`)
        } catch { showAlert('Failed to import – invalid JSON') }
    }

    function getPausedWorkflowName(workflow: PausedWorkflowResponse): string {
        const wf = workflow.workflow as unknown as Record<string, unknown>
        return typeof wf?.name === 'string' ? wf.name : 'Unnamed Workflow'
    }

    /** Returns up to `max` key:value snippets to show context for a paused workflow. */
    function getPauseSnippet(workflow: PausedWorkflowResponse, max = 3): { key: string; value: string }[] {
        const source: Record<string, any> =
            workflow.current_pause.input_data && Object.keys(workflow.current_pause.input_data).length > 0
                ? workflow.current_pause.input_data
                : Object.values(workflow.run.initial_inputs ?? {})[0] ?? {}

        return Object.entries(source)
            .slice(0, max)
            .map(([key, val]) => ({
                key,
                value: typeof val === 'object' ? JSON.stringify(val) : String(val ?? ''),
            }))
    }

    function formatDate(d: string) {
        return new Date(d).toLocaleString(undefined, {
            year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
        })
    }

    function runStatusClass(status: string) {
        switch (status.toLowerCase()) {
            case 'completed': return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
            case 'failed':    return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
            case 'running':   return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'
            case 'paused':    return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300'
            default:          return 'bg-muted text-muted-foreground'
        }
    }
</script>

<svelte:head><title>Dashboard - Faraflow</title></svelte:head>

<Header activePage="dashboard" />

<!-- Alert toast -->
{#if alertVisible}
    <div class="fixed bottom-4 right-4 z-50 rounded-lg bg-foreground px-4 py-2 text-background text-sm shadow-lg">
        {alertMsg}
    </div>
{/if}

<!-- Delete confirmation -->
<ConfirmationModal
    isOpen={deleteTargetWorkflow !== null}
    onClose={() => { deleteTargetWorkflow = null }}
    onConfirm={() => deleteTargetWorkflow && handleDelete(deleteTargetWorkflow)}
    title="Delete Workflow"
    message={`Delete "${deleteTargetWorkflow?.name}"? This cannot be undone.`}
    confirmText="Delete"
    isDanger
/>

<!-- New Flow type picker modal -->
<Dialog.Root bind:open={isNewSpurOpen}>
    <Dialog.Content class="max-w-sm">
        <Dialog.Header>
            <Dialog.Title>Create New Flow</Dialog.Title>
            <Dialog.Description>Select the type of flow you want to create</Dialog.Description>
        </Dialog.Header>
        <div class="flex flex-col gap-2 py-2">
            {#each [
                { type: SpurType.WORKFLOW, label: 'Workflow', icon: 'lucide:workflow',       desc: 'Create a standard workflow with nodes and edges' },
                { type: SpurType.CHATBOT,  label: 'Chatbot',  icon: 'lucide:message-square', desc: 'Create a chatbot with session management and conversational I/O' },
            ] as opt}
                <button
                    class="flex items-start gap-3 rounded-lg border p-3 text-left transition-colors
                           {selectedSpurType === opt.type
                               ? 'border-primary bg-primary/5'
                               : 'border-border hover:bg-muted/50'}"
                    onclick={() => { selectedSpurType = opt.type }}
                >
                    <div class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 transition-colors
                                {selectedSpurType === opt.type ? 'border-primary' : 'border-muted-foreground/40'}">
                        {#if selectedSpurType === opt.type}
                            <div class="h-2.5 w-2.5 rounded-full bg-primary"></div>
                        {/if}
                    </div>
                    <div class="flex flex-col gap-0.5">
                        <div class="flex items-center gap-2 text-sm font-medium">
                            <Icon icon={opt.icon} width={16} />
                            {opt.label}
                        </div>
                        <p class="text-xs text-muted-foreground">{opt.desc}</p>
                    </div>
                </button>
            {/each}
        </div>
        <Dialog.Footer>
            <Button variant="ghost" onclick={() => { isNewSpurOpen = false }}>Cancel</Button>
            <Button onclick={handleCreateSpur} disabled={isCreating}>
                {isCreating ? 'Creating…' : 'Create'}
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>

<!-- Page body — acts as drop zone -->
<div
    class="relative flex flex-col gap-4 max-w-7xl w-full mx-auto pt-4 px-6 pb-12"
    ondragover={(e) => { e.preventDefault(); isDragActive = true }}
    ondragleave={() => { isDragActive = false }}
    ondrop={handleDrop}
    role="region"
    aria-label="Dashboard"
>
    <!-- Drop overlay -->
    {#if isDragActive}
        <div class="absolute inset-0 flex flex-col items-center justify-center bg-primary/10 backdrop-blur-sm border-2 border-dashed border-primary rounded-lg z-50 pointer-events-none">
            <Icon icon="lucide:upload" class="w-16 h-16 text-primary mb-4" />
            <p class="text-primary text-xl font-bold">Drop workflow JSON file here</p>
        </div>
    {/if}

    <!-- No API keys warning -->
    {#if !isLoadingApiKeys && !hasApiKeys}
        <div class="flex items-center gap-2 rounded-lg border border-yellow-300 bg-yellow-50 dark:border-yellow-700 dark:bg-yellow-900/20 px-4 py-3 text-sm text-yellow-800 dark:text-yellow-300">
            <Icon icon="lucide:alert-triangle" width={16} class="shrink-0" />
            No API keys configured. Set them in Settings to run workflows.
        </div>
    {/if}

    <!-- Header row -->
    <div class="flex items-center">
        <div>
            <h1 class="text-2xl font-bold">Dashboard</h1>
            <p class="text-sm text-muted-foreground">Manage your flows</p>
        </div>
        <div class="ml-auto flex items-center gap-2">
            <Button onclick={() => { isNewSpurOpen = true }}>
                <Icon icon="lucide:plus" width={16} class="mr-1.5" />
                New Flow
            </Button>
            <Button variant="outline" onclick={handleImport}>
                <Icon icon="lucide:upload" width={16} class="mr-1.5" />
                Import
            </Button>
        </div>
    </div>

    <!-- Collapsible sections -->
    <Accordion.Root type="multiple" value={['workflows', 'slack-agents', 'human-tasks', 'recent-traces', 'templates']} class="space-y-3">

        <!-- Recent Flows -->
        <Accordion.Item value="workflows" class="rounded-xl border border-border bg-card overflow-hidden">
            <Accordion.Trigger class="w-full px-5 py-4 flex items-center justify-between text-lg font-semibold hover:no-underline hover:bg-muted/30 transition-colors">
                Recent Flows
            </Accordion.Trigger>
            <Accordion.Content class="px-5 pb-5">
                {#if isLoadingWorkflows}
                    <div class="flex justify-center py-8">
                        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-foreground"></div>
                    </div>
                {:else if workflows.length === 0}
                    <div class="flex flex-col items-center py-10">
                        <h3 class="text-xl font-semibold mb-2">Welcome to Faraflow!</h3>
                        <p class="text-muted-foreground mb-8 text-center max-w-md">
                            You haven't created any flows yet. Get started below.
                        </p>
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 w-full max-w-3xl">
                            {#each [
                                { icon: 'lucide:plus', title: 'Create New', desc: 'Start fresh', action: () => { isNewSpurOpen = true } },
                                { icon: 'lucide:upload', title: 'Import Existing', desc: 'Import a JSON workflow', action: handleImport },
                                { icon: 'lucide:layout-grid', title: 'Use Template', desc: 'Browse templates below', action: () => {} },
                            ] as card}
                                <button
                                    class="flex flex-col items-center p-6 rounded-xl border border-border hover:bg-accent/5 transition-all hover:shadow-md cursor-pointer text-center"
                                    onclick={card.action}
                                >
                                    <div class="rounded-full bg-background p-4 mb-3 border border-border">
                                        <Icon icon={card.icon} class="w-7 h-7" />
                                    </div>
                                    <h4 class="font-medium mb-1">{card.title}</h4>
                                    <p class="text-sm text-muted-foreground">{card.desc}</p>
                                </button>
                            {/each}
                        </div>
                    </div>
                {:else}
                    <div class="overflow-x-auto rounded-lg border border-border">
                        <table class="w-full text-sm">
                            <thead class="bg-muted/50 text-muted-foreground">
                                <tr>
                                    <th class="px-4 py-2.5 text-left font-medium">Name</th>
                                    <th class="px-4 py-2.5 text-left font-medium whitespace-nowrap">Flow ID</th>
                                    <th class="px-4 py-2.5 text-left font-medium">Type</th>
                                    <th class="px-4 py-2.5 text-left font-medium">Recent Runs</th>
                                    <th class="px-4 py-2.5 text-left font-medium whitespace-nowrap">Last Modified</th>
                                    <th class="px-4 py-2.5 text-left font-medium">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {#each workflows as wf (wf.id)}
                                    <tr class="border-t border-border transition-colors hover:bg-muted/30
                                               {highlightedWorkflowId === wf.id ? 'bg-primary/5' : ''}">
                                        <td class="px-4 py-2.5">
                                            <button
                                                class="font-medium hover:text-primary transition-colors text-left"
                                                onclick={() => goto(`/workflows/${wf.id}`)}
                                            >{wf.name}</button>
                                        </td>
                                        <td class="px-4 py-2.5 font-mono text-xs text-muted-foreground whitespace-nowrap">
                                            {wf.id}
                                        </td>
                                        <td class="px-4 py-2.5">
                                            <SpurTypeChip spurType={wf.definition.spur_type} />
                                        </td>
                                        <td class="px-4 py-2.5">
                                            <div class="flex flex-wrap gap-1">
                                                {#each (workflowRuns[wf.id] ?? []) as run (run.id)}
                                                    <button
                                                        class="text-xs px-2 py-0.5 rounded-full border {runStatusClass(run.status)} hover:opacity-80 transition-opacity"
                                                        onclick={() => window.open(`/trace/${run.id}`, '_blank')}
                                                        title={run.status}
                                                    >{run.id.slice(-6)}</button>
                                                {/each}
                                                {#if (workflowRuns[wf.id]?.length ?? 0) >= 5}
                                                    <button
                                                        class="text-xs px-2 py-0.5 rounded-full border border-border hover:bg-muted transition-colors"
                                                        onclick={() => window.open(`/runs/${wf.id}`, '_blank')}
                                                    >See all</button>
                                                {/if}
                                            </div>
                                        </td>
                                        <td class="px-4 py-2.5 text-muted-foreground whitespace-nowrap text-xs">
                                            {formatDate(wf.updated_at)}
                                        </td>
                                        <td class="px-4 py-2.5">
                                            <div class="flex items-center gap-3">
                                                <button
                                                    class="text-muted-foreground hover:text-foreground transition-colors"
                                                    onclick={() => goto(`/workflows/${wf.id}`)}
                                                    title="Edit" aria-label="Edit"
                                                ><Icon icon="solar:pen-bold" width={15} /></button>
                                                <button
                                                    class="text-muted-foreground hover:text-foreground transition-colors"
                                                    onclick={() => handleDuplicate(wf)}
                                                    title="Duplicate" aria-label="Duplicate"
                                                ><Icon icon="solar:copy-bold" width={15} /></button>
                                                <button
                                                    class="text-muted-foreground hover:text-destructive transition-colors"
                                                    onclick={() => { deleteTargetWorkflow = wf }}
                                                    title="Delete" aria-label="Delete"
                                                ><Icon icon="solar:trash-bin-trash-bold" width={15} /></button>
                                            </div>
                                        </td>
                                    </tr>
                                {/each}
                            </tbody>
                        </table>
                    </div>

                    {#if hasMoreWorkflows}
                        <div class="flex justify-center mt-4">
                            <Button variant="outline" size="sm" onclick={handleLoadMore} disabled={isLoadingMore}>
                                {#if isLoadingMore}
                                    <Icon icon="svg-spinners:3-dots-fade" width={16} class="mr-1" />Loading…
                                {:else}
                                    <Icon icon="lucide:plus" width={14} class="mr-1" />Load More
                                {/if}
                            </Button>
                        </div>
                    {/if}
                {/if}
            </Accordion.Content>
        </Accordion.Item>

        <!-- Slack Agents (hidden for now; remove these comment markers to show it again)
        <Accordion.Item value="slack-agents" class="rounded-xl border border-border bg-card overflow-hidden">
            <Accordion.Trigger class="w-full px-5 py-4 flex items-center justify-between text-lg font-semibold hover:no-underline hover:bg-muted/30 transition-colors">
                <div class="flex items-center gap-2">
                    Slack Agents
                    {#if slackAgentCount > 0}
                        <span class="inline-flex items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-medium px-2 py-0.5 min-w-[1.5rem]">
                            {slackAgentCount}
                        </span>
                    {/if}
                </div>
            </Accordion.Trigger>
            <Accordion.Content class="px-5 pb-5">
                <SlackAgentList onCountChange={(count) => (slackAgentCount = count)} />
            </Accordion.Content>
        </Accordion.Item>
        -->

        <!-- Flows Awaiting Human Approval -->
        <Accordion.Item value="human-tasks" class="rounded-xl border border-border bg-card overflow-hidden">
            <Accordion.Trigger class="w-full px-5 py-4 flex items-center justify-between text-lg font-semibold hover:no-underline hover:bg-muted/30 transition-colors">
                <div class="flex items-center gap-2">
                    Flows Awaiting Human Approval
                    {#if pausedWorkflows.length > 0}
                        <span class="inline-flex items-center justify-center rounded-full bg-yellow-500/15 text-yellow-700 dark:text-yellow-400 text-xs font-medium px-2 py-0.5 min-w-[1.5rem]">
                            {pausedWorkflows.length}
                        </span>
                    {/if}
                </div>
            </Accordion.Trigger>
            <Accordion.Content class="px-5 pb-5">
                {#if isLoadingPaused}
                    <div class="flex justify-center py-8">
                        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-foreground"></div>
                    </div>
                {:else if pausedWorkflows.length === 0}
                    <p class="text-muted-foreground py-6 text-center text-sm">No tasks currently requiring human approval.</p>
                {:else}
                    <div class="space-y-3">
                        {#each pausedWorkflows as workflow (workflow.run.id)}
                            {@const snippet = getPauseSnippet(workflow)}
                            <div class="flex items-center justify-between p-4 rounded-lg border border-border bg-muted/20">
                                <div class="flex-1 min-w-0">
                                    <div class="flex items-center gap-2 mb-1">
                                        <a
                                            href="/trace/{workflow.run.id}"
                                            target="_blank"
                                            rel="noreferrer"
                                            class="font-medium text-sm truncate cursor-pointer hover:text-primary hover:underline transition-colors"
                                        >{getPausedWorkflowName(workflow)}</a>
                                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-yellow-500/15 text-yellow-700 dark:text-yellow-400 shrink-0">
                                            Paused
                                        </span>
                                    </div>
                                    {#if workflow.current_pause.pause_message}
                                        <p class="text-sm text-muted-foreground mb-1.5 truncate">
                                            {workflow.current_pause.pause_message}
                                        </p>
                                    {/if}
                                    {#if snippet.length > 0}
                                        <div class="flex flex-wrap gap-x-3 gap-y-1 mb-1.5">
                                            {#each snippet as { key, value }}
                                                <span class="text-xs text-muted-foreground">
                                                    <span class="font-medium text-foreground/70">{key}:</span>
                                                    <span class="ml-1 font-mono max-w-[180px] inline-block truncate align-bottom">{value}</span>
                                                </span>
                                            {/each}
                                        </div>
                                    {/if}
                                    <div class="flex items-center gap-3 text-xs text-muted-foreground/70">
                                        <span>Run: {workflow.run.id}</span>
                                        <span>•</span>
                                        <span>Paused {formatDistanceToNow(new Date(workflow.current_pause.pause_time), { addSuffix: true })}</span>
                                    </div>
                                </div>
                                <div class="flex gap-1.5 ml-4 shrink-0">
                                    <a
                                        href="/trace/{workflow.run.id}"
                                        target="_blank"
                                        rel="noreferrer"
                                        class="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                                        title="View Trace" aria-label="View Trace"
                                    ><Icon icon="lucide:external-link" width={16} /></a>
                                    <button
                                        class="p-1.5 rounded-md text-green-600 hover:bg-green-100 dark:hover:bg-green-900/30 transition-colors"
                                        onclick={() => { selectedWorkflow = workflow; humanInputDefaultAction = 'APPROVE'; isHumanInputModalOpen = true }}
                                        title="Approve" aria-label="Approve"
                                    ><Icon icon="lucide:check" width={16} /></button>
                                    <button
                                        class="p-1.5 rounded-md text-destructive hover:bg-destructive/10 transition-colors"
                                        onclick={() => { selectedWorkflow = workflow; humanInputDefaultAction = 'DECLINE'; isHumanInputModalOpen = true }}
                                        title="Decline" aria-label="Decline"
                                    ><Icon icon="lucide:x" width={16} /></button>
                                    <button
                                        class="p-1.5 rounded-md text-primary hover:bg-primary/10 transition-colors"
                                        onclick={() => { selectedWorkflow = workflow; humanInputDefaultAction = 'APPROVE'; isHumanInputModalOpen = true }}
                                        title="Details / Override" aria-label="Details"
                                    ><Icon icon="lucide:more-horizontal" width={16} /></button>
                                    <button
                                        class="p-1.5 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                                        onclick={() => handleCancelWorkflow(workflow)}
                                        title="Cancel Workflow" aria-label="Cancel Workflow"
                                    ><Icon icon="lucide:trash-2" width={16} /></button>
                                </div>
                            </div>
                        {/each}
                    </div>
                {/if}
            </Accordion.Content>
        </Accordion.Item>

        <!-- Recent Traces -->
        <Accordion.Item value="recent-traces" class="rounded-xl border border-border bg-card overflow-hidden">
            <Accordion.Trigger class="w-full px-5 py-4 flex items-center justify-between text-lg font-semibold hover:no-underline hover:bg-muted/30 transition-colors">
                <div class="flex items-center gap-3">
                    Recent Traces
                    <!-- All / Failed filter tabs — stop accordion toggle when clicking tabs -->
                    <!-- svelte-ignore a11y_click_events_have_key_events -->
                    <!-- svelte-ignore a11y_no_static_element_interactions -->
                    <div class="flex items-center gap-1 rounded-lg bg-muted p-0.5 text-xs font-normal" onclick={(e) => e.stopPropagation()}>
                        <button
                            type="button"
                            class="px-2.5 py-1 rounded-md transition-colors {traceFilter === 'all' ? 'bg-background shadow-sm font-medium' : 'text-muted-foreground hover:text-foreground'}"
                            onclick={() => traceFilter = 'all'}
                        >All</button>
                        <button
                            type="button"
                            class="px-2.5 py-1 rounded-md transition-colors {traceFilter === 'failed' ? 'bg-background shadow-sm font-medium text-destructive' : 'text-muted-foreground hover:text-foreground'}"
                            onclick={() => traceFilter = 'failed'}
                        >Failed</button>
                    </div>
                </div>
            </Accordion.Trigger>
            <Accordion.Content class="px-5 pb-5">
                {#if isLoadingRuns}
                    <div class="flex justify-center py-8">
                        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-foreground"></div>
                    </div>
                {:else if filteredTraces.length === 0}
                    <p class="text-muted-foreground py-6 text-center text-sm">{traceFilter === 'failed' ? 'No failed runs.' : 'No runs yet.'}</p>
                {:else}
                    <div class="overflow-x-auto rounded-lg border border-border">
                        <table class="w-full text-sm">
                            <thead class="bg-muted/50 text-muted-foreground">
                                <tr>
                                    <th class="px-4 py-2.5 text-left font-medium">Run ID</th>
                                    <th class="px-4 py-2.5 text-left font-medium">Workflow</th>
                                    <th class="px-4 py-2.5 text-left font-medium">Status</th>
                                    <th class="px-4 py-2.5 text-left font-medium">Inputs</th>
                                    <th class="px-4 py-2.5 text-left font-medium whitespace-nowrap">Started</th>
                                    <th class="px-4 py-2.5 text-left font-medium">Trace</th>
                                </tr>
                            </thead>
                            <tbody>
                                {#each filteredTraces as run (run.id)}
                                    {@const inputVals = Object.values(run.initial_inputs ?? {})[0] ?? {}}
                                    {@const inputPreview = Object.entries(inputVals).map(([k, v]) => `${k}: ${String(v).slice(0, 25)}`).join(' · ').slice(0, 70)}
                                    <tr class="border-t border-border hover:bg-muted/30 transition-colors">
                                        <td class="px-4 py-2.5 font-mono text-xs text-muted-foreground">
                                            {run.id}
                                        </td>
                                        <td class="px-4 py-2.5">
                                            {#if run.workflow_id}
                                                <a href={`/workflows/${run.workflow_id}`} class="text-primary hover:underline">
                                                    {workflows.find(w => w.id === run.workflow_id)?.name ?? run.workflow_id}
                                                </a>
                                            {:else}
                                                <span class="text-muted-foreground/50">—</span>
                                            {/if}
                                        </td>
                                        <td class="px-4 py-2.5">
                                            <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {runStatusClass(run.status)}">
                                                {run.status}
                                            </span>
                                        </td>
                                        <td class="px-4 py-2.5 max-w-[220px]">
                                            {#if inputPreview}
                                                <span class="text-xs text-muted-foreground truncate block" title={Object.entries(inputVals).map(([k, v]) => `${k}: ${String(v)}`).join(', ')}>{inputPreview}</span>
                                            {:else}
                                                <span class="text-xs text-muted-foreground/50">—</span>
                                            {/if}
                                        </td>
                                        <td class="px-4 py-2.5 text-muted-foreground whitespace-nowrap">
                                            {run.start_time ? formatDate(run.start_time) : '—'}
                                        </td>
                                        <td class="px-4 py-2.5">
                                            <a
                                                href="/trace/{run.id}"
                                                class="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors inline-flex"
                                                title="View Trace"
                                            >
                                                <Icon icon="lucide:external-link" width={16} />
                                            </a>
                                        </td>
                                    </tr>
                                {/each}
                            </tbody>
                        </table>
                    </div>
                {/if}
            </Accordion.Content>
        </Accordion.Item>

        <!-- Flow Templates -->
        <Accordion.Item value="templates" class="rounded-xl border border-border bg-card overflow-hidden">
            <Accordion.Trigger class="w-full px-5 py-4 flex items-center justify-between text-lg font-semibold hover:no-underline hover:bg-muted/30 transition-colors">
                Flow Templates
            </Accordion.Trigger>
            <Accordion.Content class="px-5 pb-5">
                {#if isLoadingTemplates}
                    <div class="flex justify-center py-8">
                        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-foreground"></div>
                    </div>
                {:else if templates.length === 0}
                    <p class="text-muted-foreground py-6 text-center text-sm">No templates available.</p>
                {:else}
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {#each templates as template (template.name)}
                            <TemplateCard
                                title={template.name}
                                description={template.description ?? ''}
                                features={template.features ?? []}
                                onUse={() => handleUseTemplate(template)}
                            />
                        {/each}
                    </div>
                {/if}
            </Accordion.Content>
        </Accordion.Item>

    </Accordion.Root>
</div>

<!-- Human Input Modal -->
{#if selectedWorkflow}
    <HumanInputModal
        isOpen={isHumanInputModalOpen}
        onOpenChange={(open) => { isHumanInputModalOpen = open; if (!open) selectedWorkflow = null }}
        workflow={selectedWorkflow}
        defaultAction={humanInputDefaultAction}
        onSubmit={handleHumanInputSubmit}
    />
{/if}
