<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import Icon from '@iconify/svelte'
    import { Button } from '$lib/components/ui/button'
    import { Input } from '$lib/components/ui/input'
    import FileUploadBox from '$lib/components/FileUploadBox.svelte'
    import TextEditor from '$lib/components/textEditor/TextEditor.svelte'
    import { flowStore } from '$lib/stores/flow.svelte'
    import { saveWorkflow } from '$lib/actions/saveWorkflow.svelte'
    import { uploadTestFiles, getWorkflowRuns } from '$lib/utils/api'
    import type { TestInput } from '$lib/types/api_types/workflowSchemas'
    import type { RunResponse } from '$lib/types/api_types/runSchemas'

    interface Props {
        onRun: (inputs: Record<string, any>, files?: Record<string, string[]>) => Promise<void>
        readOnly?: boolean
    }

    let { onRun, readOnly = false }: Props = $props()

    // ── Derived from store ─────────────────────────────────────────────────────
    const nodes = $derived(flowStore.nodes)
    const nodeConfigs = $derived(flowStore.nodeConfigs)
    const workflowID = $derived(flowStore.workflowID)
    const testInputs = $derived(flowStore.testInputs)
    const selectedTestInputId = $derived(flowStore.selectedTestInputId)

    const inputNode = $derived(nodes.find((n) => n.type === 'InputNode'))
    const workflowInputVariables = $derived(
        inputNode ? nodeConfigs[inputNode.id]?.output_schema ?? {} : {}
    )
    const workflowInputVariableNames = $derived(Object.keys(workflowInputVariables))

    // ── Recent runs ────────────────────────────────────────────────────────────
    let recentRuns = $state<RunResponse[]>([])

    $effect(() => {
        if (workflowID) {
            getWorkflowRuns(workflowID, 1, 50).then(runs => { recentRuns = runs }).catch(() => {})
        }
    })

    function findLatestRunForTestInput(testInput: TestInput): RunResponse | undefined {
        const { id, ...inputVals } = testInput
        const targetJson = JSON.stringify(inputVals)
        return recentRuns.find(run => {
            const runInputs = Object.values(run.initial_inputs ?? {})[0]
            return runInputs !== undefined && JSON.stringify(runInputs) === targetJson
        })
    }

    // ── Search & filter ────────────────────────────────────────────────────────
    let searchQuery = $state('')
    let runFilter = $state<'all' | 'run' | 'not-run'>('all')

    const filteredTestInputs = $derived.by(() => {
        const q = searchQuery.trim().toLowerCase()
        return testInputs.filter((row) => {
            if (q) {
                const matches = workflowInputVariableNames.some((f) =>
                    String(row[f] ?? '').toLowerCase().includes(q)
                )
                if (!matches) return false
            }
            if (runFilter !== 'all') {
                const hasRun = findLatestRunForTestInput(row) !== undefined
                if (runFilter === 'run' && !hasRun) return false
                if (runFilter === 'not-run' && hasRun) return false
            }
            return true
        })
    })

    // ── Local state ────────────────────────────────────────────────────────────
    let editorContents = $state<Record<string, string>>({})
    let uploadedFiles = $state<Record<string, File[]>>({})
    let filePaths = $state<Record<string, string[]>>({})
    let fileInputModes = $state<Record<string, 'file' | 'url'>>({})
    let editingCell = $state<{ rowId: number; field: string } | null>(null)

    // ── Helpers ────────────────────────────────────────────────────────────────
    function getNextId(): number {
        return testInputs.reduce((max, row) => Math.max(max, row.id), 0) + 1
    }

    function handleDeleteRow(id: number) {
        flowStore.deleteTestInput(id)
        if (selectedTestInputId === id.toString()) flowStore.setSelectedTestInputId(null)
        saveWorkflow()
    }

    function handleCellEdit(rowId: number, field: string, value: string) {
        const row = testInputs.find((r) => r.id === rowId)
        if (row) flowStore.updateTestInput({ ...row, [field]: value })
        saveWorkflow()
    }

    async function handleFilesChange(nodeId: string, files: File[]) {
        if (!workflowID) return
        uploadedFiles = { ...uploadedFiles, [nodeId]: files }
        if (files.length === 0) {
            const ff = workflowInputVariableNames.filter(f => f.toLowerCase().includes('file'))
            if (ff.length > 0) editorContents = { ...editorContents, [ff[0]]: '' }
            return
        }
        try {
            const paths = await uploadTestFiles(workflowID, nodeId, files)
            filePaths = { ...filePaths, ...paths }
            const ff = workflowInputVariableNames.filter(f => f.toLowerCase().includes('file'))
            if (ff.length > 0) editorContents = { ...editorContents, [ff[0]]: paths[nodeId]?.[0] ?? '' }
        } catch (err) {
            console.error('Error uploading files:', err)
        }
    }

    function handleUrlInput(field: string, value: string) {
        if (value === '' || /^(https?:\/\/|gs:\/\/)/.test(value)) {
            editorContents = { ...editorContents, [field]: value }
        }
    }

    function handleSaveTestCase() {
        if (!Object.values(editorContents).some(v => v?.trim())) return
        const newId = getNextId()
        const newTestInput: TestInput = { id: newId, ...editorContents }
        flowStore.addTestInput(newTestInput)
        flowStore.setSelectedTestInputId(newId.toString())
        editorContents = {}
        saveWorkflow()
    }

    async function handleRun() {
        if (!inputNode) return
        let testCaseToRun: TestInput | undefined
        const hasUnsaved = Object.values(editorContents).some(v => v?.trim())

        if (hasUnsaved) {
            const newId = getNextId()
            const newTestInput: TestInput = { id: newId, ...editorContents }
            flowStore.addTestInput(newTestInput)
            flowStore.setSelectedTestInputId(newId.toString())
            editorContents = {}
            testCaseToRun = newTestInput
        } else {
            testCaseToRun = testInputs.find(r => r.id.toString() === selectedTestInputId)
        }

        if (!testCaseToRun) return

        const { id, ...inputValues } = testCaseToRun
        await onRun({ [inputNode.id]: inputValues }, filePaths)
    }

    function getFileExtension(content: string): string {
        return (content.split('.').pop() ?? '').toLowerCase()
    }

    function normalizeFilePath(content: string): string {
        if (content.startsWith('test_files/') || content.startsWith('run_files/')) {
            return `${window.location.origin}/api/files/${content}`
        }
        return content
    }

    const canRun = $derived(
        !readOnly &&
        !!inputNode &&
        (!!selectedTestInputId || Object.values(editorContents).some(v => v?.trim()) || workflowInputVariableNames.length === 0)
    )
</script>

<div class="flex flex-col h-full min-h-0">
    <!-- Scrollable body -->
    <div class="flex-1 overflow-y-auto px-4 py-3 space-y-4 min-h-0">

        <!-- Existing test cases table -->
        {#if testInputs.length > 0}
            <!-- Search + filter bar -->
            <div class="flex items-center gap-2 flex-wrap">
                <div class="relative flex-1 min-w-36">
                    <Icon icon="solar:magnifer-linear" width={14} class="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
                    <Input class="pl-8 h-8 text-sm" placeholder="Search test cases…" bind:value={searchQuery} />
                </div>
                <div class="flex items-center gap-1 shrink-0">
                    {#each ([['all', 'All'], ['not-run', 'Not run'], ['run', 'Run']] as const) as [val, label]}
                        <button
                            type="button"
                            class="px-3 py-1 rounded-full text-xs font-medium border transition-colors
                                {runFilter === val
                                    ? 'bg-primary text-primary-foreground border-primary'
                                    : 'bg-background text-muted-foreground border-border hover:bg-muted'}"
                            onclick={() => { runFilter = val }}
                        >
                            {label}
                            {#if val === 'all'}
                                <span class="ml-1 opacity-60">{testInputs.length}</span>
                            {:else if val === 'run'}
                                <span class="ml-1 opacity-60">{testInputs.filter(r => findLatestRunForTestInput(r)).length}</span>
                            {:else}
                                <span class="ml-1 opacity-60">{testInputs.filter(r => !findLatestRunForTestInput(r)).length}</span>
                            {/if}
                        </button>
                    {/each}
                </div>
            </div>

            <div class="border rounded-lg overflow-x-auto">
                <table class="w-full text-sm">
                    <thead class="bg-muted/50 border-b">
                        <tr>
                            <th class="px-3 py-2 text-left w-16">ID</th>
                            {#each workflowInputVariableNames as field}
                                <th class="px-3 py-2 text-left">{field}</th>
                            {/each}
                            <th class="px-3 py-2 text-left w-28">Status</th>
                            <th class="px-3 py-2 text-left w-20">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#if filteredTestInputs.length === 0}
                            <tr>
                                <td colspan={workflowInputVariableNames.length + 3} class="px-3 py-6 text-center text-sm text-muted-foreground">
                                    No test cases match your search or filter.
                                </td>
                            </tr>
                        {/if}
                        {#each filteredTestInputs as row (row.id)}
                            {@const latestRun = findLatestRunForTestInput(row)}
                            <tr
                                class="border-b last:border-0 cursor-pointer transition-colors
                                    {row.id.toString() === selectedTestInputId
                                        ? 'bg-primary/10'
                                        : 'hover:bg-muted/50'}"
                                onclick={() => {
                                    if (editingCell?.rowId !== row.id) {
                                        flowStore.setSelectedTestInputId(row.id.toString())
                                    }
                                }}
                            >
                                <td class="px-3 py-2 text-muted-foreground">{row.id}</td>
                                {#each workflowInputVariableNames as field}
                                    <td class="px-3 py-2 max-w-xs">
                                        {#if editingCell?.rowId === row.id && editingCell?.field === field}
                                            <!-- svelte-ignore a11y_click_events_have_key_events -->
                                            <!-- svelte-ignore a11y_no_static_element_interactions -->
                                            <div onclick={(e) => e.stopPropagation()}>
                                                <Input
                                                    autofocus
                                                    class="h-7 text-sm"
                                                    value={String(row[field] ?? '')}
                                                    onblur={(e) => {
                                                        handleCellEdit(row.id, field, (e.target as HTMLInputElement).value)
                                                        editingCell = null
                                                    }}
                                                    onkeydown={(e) => {
                                                        if (e.key === 'Enter' || e.key === 'Escape') {
                                                            handleCellEdit(row.id, field, (e.target as HTMLInputElement).value)
                                                            editingCell = null
                                                        }
                                                    }}
                                                />
                                            </div>
                                        {:else}
                                            {@const content = String(row[field] ?? '')}
                                            {@const ext = getFileExtension(content)}
                                            {#if field.toLowerCase().includes('file') && content}
                                                {@const fp = normalizeFilePath(content)}
                                                {@const fileName = content.split('/').pop() ?? content}
                                                {#if ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext)}
                                                    <img src={fp} alt={fileName} class="max-h-16 rounded object-contain" />
                                                {:else if ['mp4', 'webm', 'ogg', 'mov'].includes(ext)}
                                                    <!-- svelte-ignore a11y_media_has_caption -->
                                                    <video src={fp} class="max-h-16 rounded" controls></video>
                                                {:else}
                                                    <div class="flex items-center gap-1">
                                                        <Icon icon="solar:file-linear" width={14} />
                                                        <span class="truncate text-xs">{fileName}</span>
                                                    </div>
                                                {/if}
                                            {:else}
                                                <div class="flex items-center gap-1">
                                                    <span class="truncate">{content}</span>
                                                    {#if !readOnly}
                                                        <button
                                                            type="button"
                                                            class="shrink-0 p-0.5 rounded hover:bg-muted"
                                                            onclick={(e) => {
                                                                e.stopPropagation()
                                                                editingCell = { rowId: row.id, field }
                                                            }}
                                                        >
                                                            <Icon icon="solar:pen-linear" width={12} />
                                                        </button>
                                                    {/if}
                                                </div>
                                            {/if}
                                        {/if}
                                    </td>
                                {/each}
                                <td class="px-3 py-2">
                                    {#if latestRun}
                                        <span class="inline-flex items-center gap-1 text-xs font-medium text-green-700 dark:text-green-400 bg-green-500/10 px-2 py-0.5 rounded-full">
                                            <Icon icon="solar:check-circle-linear" width={12} />
                                            Run
                                        </span>
                                    {:else}
                                        <span class="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
                                            <Icon icon="solar:clock-circle-linear" width={12} />
                                            Not run
                                        </span>
                                    {/if}
                                </td>
                                <td class="px-3 py-2">
                                    <div class="flex items-center gap-0.5">
                                        {#if latestRun}
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                class="h-7 w-7"
                                                title="View latest trace ({latestRun.id})"
                                                onclick={(e) => {
                                                    e.stopPropagation()
                                                    window.open(`/trace/${latestRun.id}`, '_blank')
                                                }}
                                            >
                                                <Icon icon="solar:eye-linear" width={14} />
                                            </Button>
                                        {/if}
                                        {#if !readOnly}
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                class="h-7 w-7"
                                                onclick={(e) => {
                                                    e.stopPropagation()
                                                    handleDeleteRow(row.id)
                                                }}
                                            >
                                                <Icon icon="solar:trash-bin-trash-linear" width={14} />
                                            </Button>
                                        {/if}
                                    </div>
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        {/if}

        <!-- New test case editor -->
        {#if !readOnly}
            <div class="border rounded-lg">
                <div class="px-4 py-3 border-b bg-muted/30">
                    <h3 class="text-sm font-semibold">New Test Case</h3>
                </div>
                <div class="p-4">
                    {#if workflowInputVariableNames.length === 0}
                        <p class="text-sm text-muted-foreground">
                            This workflow has no input variables. You can run it without test inputs.
                        </p>
                    {:else}
                        <div class="grid grid-cols-[repeat(auto-fit,minmax(180px,1fr))] gap-4">
                            {#each workflowInputVariableNames as field}
                                <div class="flex flex-col gap-2">
                                    <div class="text-sm font-medium">{field}</div>
                                    {#if field.toLowerCase().includes('file')}
                                        <div class="space-y-2 bg-muted/30 p-3 rounded-lg">
                                            <div class="flex items-center gap-2 mb-2">
                                                <label class="flex items-center gap-2 cursor-pointer text-sm">
                                                    <input
                                                        type="checkbox"
                                                        checked={fileInputModes[field] === 'url'}
                                                        onchange={() => {
                                                            fileInputModes = {
                                                                ...fileInputModes,
                                                                [field]: fileInputModes[field] === 'url' ? 'file' : 'url',
                                                            }
                                                            editorContents = { ...editorContents, [field]: '' }
                                                        }}
                                                    />
                                                    URL Input
                                                </label>
                                            </div>
                                            {#if fileInputModes[field] === 'url'}
                                                <Input
                                                    type="url"
                                                    placeholder="Enter URL (https:// or gs://)"
                                                    value={editorContents[field] ?? ''}
                                                    oninput={(e) => handleUrlInput(field, (e.target as HTMLInputElement).value)}
                                                />
                                            {:else}
                                                <FileUploadBox
                                                    multiple={false}
                                                    onFilesChange={(files) => inputNode && handleFilesChange(inputNode.id, files)}
                                                    acceptedFileTypes={{
                                                        'application/pdf': ['.pdf'],
                                                        'text/plain': ['.txt'],
                                                        'text/markdown': ['.md'],
                                                        'image/*': ['.png', '.jpg', '.jpeg', '.gif', '.webp'],
                                                        'audio/*': ['.mp3', '.wav', '.ogg', '.m4a'],
                                                        'video/*': ['.mp4', '.webm', '.avi', '.mov'],
                                                    }}
                                                    supportedFormatsMessage="Drop files here (PDF, images, audio, video)"
                                                />
                                            {/if}
                                        </div>
                                    {:else}
                                        <div class="bg-muted/30 p-3 rounded-lg">
                                            <TextEditor
                                                nodeID="panel-newRow-{field}"
                                                fieldName={field}
                                                fieldTitle={field}
                                                inputSchema={[]}
                                                content={editorContents[field] ?? ''}
                                                setContent={(v) => { editorContents = { ...editorContents, [field]: v } }}
                                            />
                                        </div>
                                    {/if}
                                </div>
                            {/each}
                        </div>
                    {/if}

                    <div class="mt-4">
                        <Button
                            variant="outline"
                            size="sm"
                            disabled={Object.values(editorContents).every(v => !v?.trim())}
                            onclick={handleSaveTestCase}
                        >
                            <Icon icon="material-symbols:save-outline" width={14} class="mr-1" />
                            Save Test Case
                        </Button>
                    </div>
                </div>
            </div>
        {/if}
    </div>

    <!-- Footer run bar -->
    {#if !readOnly}
        <div class="shrink-0 border-t px-4 py-2 flex justify-end">
            <Button
                disabled={!canRun}
                size="sm"
                onclick={handleRun}
            >
                <Icon icon="material-symbols:play-arrow" width={16} class="mr-1" />
                Run
                <span class="ml-1 text-xs opacity-60">⌘+↵</span>
            </Button>
        </div>
    {/if}
</div>
