<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import Icon from '@iconify/svelte'
    import { untrack } from 'svelte'
    import { flowStore } from '$lib/stores/flow.svelte'
    import { panelStore } from '$lib/stores/panel.svelte'
    import { duplicateNode } from '$lib/utils/flowUtils'
    import NodeSidebar from '$lib/components/nodes/nodeSidebar/NodeSidebar.svelte'
    import PanelConnectionsTab from './PanelConnectionsTab.svelte'
    import TestCasesPanel from './TestCasesPanel.svelte'
    import RunsPanel from './RunsPanel.svelte'
    import SessionsPanel from './SessionsPanel.svelte'
    import AskNodeOutputDisplay from '$lib/components/nodes/AskNodeOutputDisplay.svelte'
    import { executionState, executeWorkflow, rerunWorkflow, continueFromNode } from '$lib/actions/workflowExecution.svelte'
    import { getStatusColor, getStatusOpacity, getStatusConfig } from '$lib/utils/statusConfig'
    import LoadingSpinner from '$lib/components/LoadingSpinner.svelte'
    import { toast } from 'svelte-sonner'
    import { SpurType } from '$lib/types/api_types/workflowSchemas'

    interface Props {
        nodeID: string | null
        readOnly?: boolean
        onStop?: () => void
    }

    let { nodeID, readOnly = false, onStop }: Props = $props()

    type SnapState = 'collapsed' | 'medium' | 'full'

    let snapState = $state<SnapState>('collapsed')
    let displayedNodeID = $state<string | null>(null)
    let historyStack = $state<string[]>([])
    let historyIndex = $state(0)
    let activeTab = $state<'outputs' | 'config' | 'connections' | 'subnodes'>('outputs')
    let workflowTab = $state<'test-cases' | 'runs' | 'sessions'>('runs')
    let runsTotalCount = $state(0)

    const isChatbot = $derived(flowStore.spurType === SpurType.CHATBOT)

    // Drag state
    let isDragging = $state(false)
    let dragHeight = $state<number | null>(null)
    let dragStartY = 0
    let dragStartHeight = 0

    // Click debounce state
    let clickTimer: ReturnType<typeof setTimeout> | null = null
    let snapStateAtClick: SnapState = 'collapsed'

    const HANDLE_HEIGHT = 44 // px

    // Sync selection: when the graph selection changes, reset history.
    $effect(() => {
        const id = nodeID
        untrack(() => {
            if (id !== displayedNodeID) {
                if (id) {
                    historyStack = [id]
                    historyIndex = 0
                    displayedNodeID = id
                    if (snapState === 'collapsed') snapState = 'medium'
                } else {
                    displayedNodeID = null
                    dragHeight = null
                    snapState = 'collapsed'
                }
            }
        })
    })

    const displayedNode = $derived(
        displayedNodeID ? (flowStore.nodes.find((n) => n.id === displayedNodeID) ?? null) : null
    )
    const displayedNodeConfig = $derived(
        displayedNodeID ? (flowStore.nodeConfigs[displayedNodeID] ?? {}) : {}
    )
    const nodeTitle = $derived(displayedNodeConfig?.title || displayedNode?.id || '')

    const upstreamNodes = $derived(
        displayedNodeID
            ? flowStore.edges
                  .filter((e) => e.target === displayedNodeID)
                  .map((e) => {
                      const n = flowStore.nodes.find((n) => n.id === e.source)
                      return n ? { id: n.id, title: flowStore.nodeConfigs[n.id]?.title || n.id } : null
                  })
                  .filter((x): x is { id: string; title: string } => x !== null)
            : []
    )

    const downstreamNodes = $derived(
        displayedNodeID
            ? flowStore.edges
                  .filter((e) => e.source === displayedNodeID)
                  .map((e) => {
                      const n = flowStore.nodes.find((n) => n.id === e.target)
                      return n ? { id: n.id, title: flowStore.nodeConfigs[n.id]?.title || n.id } : null
                  })
                  .filter((x): x is { id: string; title: string } => x !== null)
            : []
    )

    const isPeeking = $derived(displayedNodeID !== null && displayedNodeID !== nodeID)
    const canGoBack = $derived(historyIndex > 0)
    const canGoForward = $derived(historyIndex < historyStack.length - 1)

    function getSnapHeight(state: SnapState): number {
        if (typeof window === 'undefined') return 300
        const vh = window.innerHeight
        if (state === 'collapsed') return HANDLE_HEIGHT
        if (state === 'medium') return Math.round(vh * 0.5)
        return Math.round(vh * 0.9)
    }

    // Panel is always at least HANDLE_HEIGHT — never disappears.
    const panelHeight = $derived.by(() => {
        if (dragHeight !== null) return Math.max(dragHeight, HANDLE_HEIGHT)
        return Math.max(getSnapHeight(snapState), HANDLE_HEIGHT)
    })

    $effect(() => {
        panelStore.bottomPanelHeight = panelHeight
    })

    const showTabs = $derived(
        snapState !== 'collapsed' ||
        (dragHeight !== null && dragHeight > HANDLE_HEIGHT + 20)
    )

    function handlePointerDown(e: PointerEvent) {
        isDragging = true
        dragStartY = e.clientY
        dragStartHeight = dragHeight ?? getSnapHeight(snapState)
        ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
        document.body.style.cursor = 'ns-resize'
        e.preventDefault()
    }

    function handlePointerMove(e: PointerEvent) {
        if (!isDragging) return
        const delta = dragStartY - e.clientY
        const vh = window.innerHeight
        dragHeight = Math.max(HANDLE_HEIGHT, Math.min(dragStartHeight + delta, vh * 0.95))
    }

    function handlePointerUp(e: PointerEvent) {
        if (!isDragging) return
        const totalDelta = Math.abs(dragStartY - e.clientY)
        isDragging = false
        document.body.style.cursor = ''

        if (totalDelta < 5) {
            snapStateAtClick = snapState
            if (clickTimer) clearTimeout(clickTimer)
            clickTimer = setTimeout(() => {
                clickTimer = null
                snapState = 'medium'
                dragHeight = null
            }, 220)
        }
        // Free drag: keep dragHeight as-is; no snap-to-nearest
    }

    function cycleSnapState() {
        snapState = snapState === 'full' ? 'medium' : 'full'
        dragHeight = null
    }

    function minimizePanel() {
        snapState = 'collapsed'
        dragHeight = null
    }

    const isMinimized = $derived(snapState === 'collapsed' && dragHeight === null)

    function handleDoubleClick() {
        if (clickTimer) { clearTimeout(clickTimer); clickTimer = null }
        snapState = snapStateAtClick === 'full' ? 'collapsed' : 'full'
        dragHeight = null
    }

    function navigate(id: string, peek: boolean) {
        if (peek) {
            historyStack = [...historyStack.slice(0, historyIndex + 1), id]
            historyIndex = historyStack.length - 1
            displayedNodeID = id
            if (snapState === 'collapsed') snapState = 'medium'
        } else {
            flowStore.setSelectedNode(id)
            panelStore.panToNode(id)
        }
    }

    function goBack() {
        if (canGoBack) {
            historyIndex--
            displayedNodeID = historyStack[historyIndex]
        }
    }

    function goForward() {
        if (canGoForward) {
            historyIndex++
            displayedNodeID = historyStack[historyIndex]
        }
    }

    let isNodeRunning = $state(false)

    async function handleRunNode() {
        if (!displayedNodeID || !flowStore.workflowID) return
        isNodeRunning = true
        try {
            const { partialRun } = await import('$lib/actions/partialRun.svelte')
            await partialRun(flowStore.workflowID, displayedNodeID, nodeTitle)
        } finally {
            isNodeRunning = false
        }
    }

    function handleDuplicate() {
        if (!displayedNodeID || readOnly) return
        duplicateNode(displayedNodeID)
    }

    function handleDelete() {
        if (!displayedNodeID || readOnly) return
        flowStore.deleteNode(displayedNodeID)
    }

    const displayedNodeType = $derived(displayedNode?.type ?? '')
    const isAskNode = $derived(displayedNodeType === 'AskNode')

    const tabLabel: Record<'outputs' | 'config' | 'connections' | 'subnodes', string> = {
        outputs: 'Outputs',
        config: 'Config',
        connections: 'Connections',
        subnodes: 'Sub-nodes',
    }

    const isRunning = $derived(executionState.isRunning)
    const completionPercentage = $derived(executionState.completionPercentage)

    // loadedRunStatus: use the authoritatively-tracked status from executionState.
    // This covers runs loaded from the paginated panel (not in workflowRuns top-10)
    // as well as runs started directly from the workflow.
    const loadedRunStatus = $derived(executionState.loadedRunStatus)
    const isCanvasRunActive = $derived(
        isRunning || loadedRunStatus === 'RUNNING' || loadedRunStatus === 'PENDING'
    )

    function makeAlertHandler() {
        return {
            onAlert(message: string, color: string) {
                if (color === 'success') toast.success(message)
                else if (color === 'danger') toast.error(message)
                else if (color === 'warning') toast.warning(message)
                else toast(message)
            }
        }
    }

    async function handlePanelRun(inputs: Record<string, any>, files?: Record<string, string[]>) {
        await executeWorkflow(inputs, makeAlertHandler())
    }

    async function handleRerun() {
        await rerunWorkflow(makeAlertHandler())
    }

    async function handleContinue(nodeId: string | null = null) {
        await continueFromNode(nodeId, makeAlertHandler())
    }
</script>

<div
    class="relative w-full flex-shrink-0 border-t border-border bg-background overflow-hidden flex flex-col"
    style="height: {panelHeight}px; transition: {isDragging ? 'none' : 'height 200ms ease-in-out'}; z-index: 50; box-shadow: 0 -4px 12px rgba(0,0,0,0.08);"
>
    <!-- Handle strip — always visible -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        class="relative flex items-center px-3 gap-1.5 shrink-0 {showTabs ? 'border-b border-border' : ''} cursor-ns-resize touch-none select-none transition-colors
            {!displayedNodeID && isCanvasRunActive
                ? 'bg-blue-50 hover:bg-blue-100 dark:bg-blue-950/40 dark:hover:bg-blue-900/50'
                : 'bg-muted/30 hover:bg-muted/50'}"
        style="height: {HANDLE_HEIGHT}px;"
        onpointerdown={handlePointerDown}
        onpointermove={handlePointerMove}
        onpointerup={handlePointerUp}
        ondblclick={(e) => { e.preventDefault(); handleDoubleClick() }}
    >
        {#if displayedNodeID}
            <!-- ── Node mode ─────────────────────────────────────────── -->

            {#if canGoBack || canGoForward}
                <button
                    type="button"
                    class="p-1 rounded hover:bg-muted disabled:opacity-30 shrink-0"
                    disabled={!canGoBack}
                    title="Back"
                    onclick={(e) => { e.stopPropagation(); goBack() }}
                    onpointerdown={(e) => e.stopPropagation()}
                >
                    <Icon icon="solar:alt-arrow-left-linear" width={14} />
                </button>
                <button
                    type="button"
                    class="p-1 rounded hover:bg-muted disabled:opacity-30 shrink-0"
                    disabled={!canGoForward}
                    title="Forward"
                    onclick={(e) => { e.stopPropagation(); goForward() }}
                    onpointerdown={(e) => e.stopPropagation()}
                >
                    <Icon icon="solar:alt-arrow-right-linear" width={14} />
                </button>
            {/if}

            {#each upstreamNodes.slice(0, 3) as n}
                <button
                    type="button"
                    class="px-2 py-0.5 text-xs rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-800/60 max-w-[100px] truncate shrink-0"
                    title="Click to select · Cmd+Click to peek"
                    onclick={(e) => { e.stopPropagation(); navigate(n.id, e.metaKey || e.ctrlKey) }}
                    onpointerdown={(e) => e.stopPropagation()}
                >
                    ← {n.title}
                </button>
            {/each}

            <span class="flex-1 text-center text-sm font-semibold truncate min-w-0 px-2">
                {nodeTitle}
                {#if isPeeking}
                    <span class="text-xs font-normal text-muted-foreground ml-1">(peek)</span>
                {/if}
            </span>

            {#each downstreamNodes.slice(0, 3) as n}
                <button
                    type="button"
                    class="px-2 py-0.5 text-xs rounded-full bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-800/60 max-w-[100px] truncate shrink-0"
                    title="Click to select · Cmd+Click to peek"
                    onclick={(e) => { e.stopPropagation(); navigate(n.id, e.metaKey || e.ctrlKey) }}
                    onpointerdown={(e) => e.stopPropagation()}
                >
                    {n.title} →
                </button>
            {/each}

            <span class="w-px h-5 bg-border shrink-0 mx-0.5"></span>

            {#if !readOnly && flowStore.workflowID}
                {#if displayedNode?.data?.taskStatus === 'FAILED'}
                    <!-- Re-run this node (with predecessors) -->
                    <button
                        type="button"
                        class="p-1.5 rounded hover:bg-muted shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Re-run this node"
                        disabled={isNodeRunning}
                        onclick={(e) => { e.stopPropagation(); handleRunNode() }}
                        onpointerdown={(e) => e.stopPropagation()}
                    >
                        {#if isNodeRunning}
                            <LoadingSpinner size="sm" />
                        {:else}
                            <Icon icon="solar:restart-bold" class="text-orange-500" width={15} />
                        {/if}
                    </button>
                    <!-- Continue from this node (re-run this node + all descendants) -->
                    <button
                        type="button"
                        class="flex items-center gap-1 px-2 py-1 rounded text-xs font-medium bg-orange-100 hover:bg-orange-200 text-orange-700 dark:bg-orange-900/30 dark:hover:bg-orange-800/50 dark:text-orange-400 shrink-0 disabled:opacity-50"
                        title="Re-run this node and continue to all downstream nodes"
                        disabled={isNodeRunning}
                        onclick={(e) => { e.stopPropagation(); handleContinue(displayedNodeID) }}
                        onpointerdown={(e) => e.stopPropagation()}
                    >
                        <Icon icon="solar:play-bold" width={12} />
                        Continue
                    </button>
                {:else}
                    <button
                        type="button"
                        class="p-1.5 rounded hover:bg-muted shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Run node"
                        disabled={isNodeRunning}
                        onclick={(e) => { e.stopPropagation(); handleRunNode() }}
                        onpointerdown={(e) => e.stopPropagation()}
                    >
                        {#if isNodeRunning}
                            <LoadingSpinner size="sm" />
                        {:else}
                            <Icon icon="solar:play-linear" class="text-muted-foreground" width={15} />
                        {/if}
                    </button>
                {/if}
            {/if}
            {#if !readOnly}
                <button
                    type="button"
                    class="p-1.5 rounded hover:bg-muted shrink-0"
                    title="Duplicate"
                    onclick={(e) => { e.stopPropagation(); handleDuplicate() }}
                    onpointerdown={(e) => e.stopPropagation()}
                >
                    <Icon icon="solar:copy-linear" class="text-muted-foreground" width={15} />
                </button>
                <button
                    type="button"
                    class="p-1.5 rounded hover:bg-muted shrink-0"
                    title="Delete"
                    onclick={(e) => { e.stopPropagation(); handleDelete() }}
                    onpointerdown={(e) => e.stopPropagation()}
                >
                    <Icon icon="solar:trash-bin-trash-linear" class="text-muted-foreground" width={15} />
                </button>
            {/if}

            <button
                type="button"
                class="p-1.5 rounded hover:bg-muted shrink-0"
                title={snapState === 'full' ? 'Shrink panel' : 'Expand panel'}
                onclick={(e) => { e.stopPropagation(); cycleSnapState() }}
                onpointerdown={(e) => e.stopPropagation()}
            >
                <Icon
                    icon={snapState === 'full'
                        ? 'solar:alt-arrow-down-linear'
                        : 'solar:alt-arrow-up-linear'}
                    class="text-muted-foreground"
                    width={15}
                />
            </button>
            <button
                type="button"
                class="p-1.5 rounded hover:bg-muted shrink-0 disabled:opacity-30 disabled:cursor-not-allowed"
                title="Minimize panel"
                disabled={isMinimized}
                onclick={(e) => { e.stopPropagation(); minimizePanel() }}
                onpointerdown={(e) => e.stopPropagation()}
            >
                <Icon icon="lucide:minus" class="text-muted-foreground" width={15} />
            </button>
        {:else}
            <!-- ── Workflow mode (no node selected) ──────────────────── -->
            <span class="text-sm font-semibold truncate px-2 shrink-0 {isCanvasRunActive ? 'text-blue-700 dark:text-blue-300' : ''}">
                {flowStore.projectName || 'Workflow'}
            </span>

            {#if isCanvasRunActive}
                <!-- Percentage label + segmented node bar fill available space -->
                <div
                    class="flex-1 min-w-0 flex items-center gap-2 mx-2"
                    onpointerdown={(e) => e.stopPropagation()}
                >
                    <span class="text-sm font-bold tabular-nums shrink-0 text-blue-600 dark:text-blue-400">
                        {Math.floor(completionPercentage)}%
                    </span>
                    {#if flowStore.nodes.length > 0}
                        <div class="flex items-stretch gap-px flex-1 h-3 rounded-sm overflow-hidden min-w-0" title="Node-by-node progress">
                            {#each flowStore.nodes as node}
                                {@const s = node.data?.taskStatus ?? null}
                                <div
                                    class="flex-1 h-full transition-all duration-300 {s === 'RUNNING' ? 'animate-pulse' : ''}"
                                    style="background-color: {getStatusColor(s)}; opacity: {getStatusOpacity(s)};"
                                ></div>
                            {/each}
                        </div>
                    {/if}
                </div>
            {:else}
                <span class="flex-1"></span>
            {/if}

            <!-- Run ID — shown whenever a run is loaded, regardless of active state -->
            {#if executionState.currentRunId}
                {@const runCfg = getStatusConfig(loadedRunStatus)}
                <div class="flex items-center gap-1 shrink-0 mx-1" onpointerdown={(e) => e.stopPropagation()}>
                    {#if isCanvasRunActive}
                        <Icon icon="solar:refresh-bold" width={12} class="animate-spin shrink-0 text-blue-500" />
                    {:else}
                        <Icon icon={runCfg.icon} width={12} class="shrink-0" style="color: {runCfg.color};" />
                    {/if}
                    <span class="text-xs font-mono" style="color: {isCanvasRunActive ? 'rgb(59,130,246)' : runCfg.color};">{executionState.currentRunId}</span>
                </div>
            {/if}

            <span class="w-px h-5 bg-border/60 shrink-0 mx-0.5"></span>

            {#if !readOnly}
                {#if isCanvasRunActive}
                    <button
                        type="button"
                        class="p-1.5 rounded hover:bg-blue-200/60 dark:hover:bg-blue-900/60 shrink-0"
                        title="Stop workflow"
                        onclick={(e) => { e.stopPropagation(); onStop?.() }}
                        onpointerdown={(e) => e.stopPropagation()}
                    >
                        <Icon icon="solar:stop-bold" class="text-blue-600 dark:text-blue-400" width={15} />
                    </button>
                {:else if loadedRunStatus === 'FAILED' || loadedRunStatus === 'CANCELED'}
                    <button
                        type="button"
                        class="flex items-center gap-1 px-2 py-1 rounded text-xs font-medium bg-orange-100 hover:bg-orange-200 text-orange-700 dark:bg-orange-900/30 dark:hover:bg-orange-800/50 dark:text-orange-400 shrink-0"
                        title="Re-execute unfinished nodes and continue"
                        onclick={(e) => { e.stopPropagation(); handleContinue(null) }}
                        onpointerdown={(e) => e.stopPropagation()}
                    >
                        <Icon icon="solar:play-bold" width={12} />
                        Continue
                    </button>
                {:else if loadedRunStatus === 'COMPLETED'}
                    <button
                        type="button"
                        class="flex items-center gap-1 px-2 py-1 rounded text-xs font-medium bg-green-100 hover:bg-green-200 text-green-700 dark:bg-green-900/30 dark:hover:bg-green-800/50 dark:text-green-400 shrink-0"
                        title="Re-run with same inputs"
                        onclick={(e) => { e.stopPropagation(); handleRerun() }}
                        onpointerdown={(e) => e.stopPropagation()}
                    >
                        <Icon icon="solar:restart-bold" width={12} />
                        Rerun
                    </button>
                {:else}
                    <button
                        type="button"
                        class="p-1.5 rounded hover:bg-muted shrink-0"
                        title="Run workflow (⌘ Enter)"
                        onclick={(e) => { e.stopPropagation(); flowStore.setRunModalOpen(true) }}
                        onpointerdown={(e) => e.stopPropagation()}
                    >
                        <Icon icon="solar:play-linear" class="text-muted-foreground" width={15} />
                    </button>
                {/if}
            {/if}

            <button
                type="button"
                class="p-1.5 rounded hover:bg-muted shrink-0"
                title={snapState === 'full' ? 'Shrink panel' : 'Expand panel'}
                onclick={(e) => { e.stopPropagation(); cycleSnapState() }}
                onpointerdown={(e) => e.stopPropagation()}
            >
                <Icon
                    icon={snapState === 'full' ? 'solar:alt-arrow-down-linear' : 'solar:alt-arrow-up-linear'}
                    class="text-muted-foreground"
                    width={15}
                />
            </button>
            <button
                type="button"
                class="p-1.5 rounded hover:bg-muted shrink-0 disabled:opacity-30 disabled:cursor-not-allowed"
                title="Minimize panel"
                disabled={isMinimized}
                onclick={(e) => { e.stopPropagation(); minimizePanel() }}
                onpointerdown={(e) => e.stopPropagation()}
            >
                <Icon icon="lucide:minus" class="text-muted-foreground" width={15} />
            </button>

        {/if}
    </div>

    {#if showTabs}
        {#if displayedNodeID}
            <!-- ── Node mode tab bar ─────────────────────────────────────── -->
            <div class="flex shrink-0 border-b border-border px-1">
                {#each (['outputs', 'config', 'connections'] as const) as tab}
                    <button
                        type="button"
                        class="px-4 py-2 text-sm border-b-2 transition-colors {activeTab === tab
                            ? 'border-primary text-foreground font-medium'
                            : 'border-transparent text-muted-foreground hover:text-foreground'}"
                        onclick={() => (activeTab = tab)}
                    >
                        {tabLabel[tab]}
                    </button>
                {/each}
                {#if isAskNode}
                    <button
                        type="button"
                        class="px-4 py-2 text-sm border-b-2 transition-colors {activeTab === 'subnodes'
                            ? 'border-primary text-foreground font-medium'
                            : 'border-transparent text-muted-foreground hover:text-foreground'}"
                        onclick={() => (activeTab = 'subnodes')}
                    >
                        {tabLabel.subnodes}
                    </button>
                {/if}
            </div>

            <div class="flex-1 overflow-auto min-h-0">
                {#if activeTab === 'outputs' || activeTab === 'config'}
                    <NodeSidebar
                        nodeID={displayedNodeID}
                        {readOnly}
                        embedded={true}
                        activeTab={activeTab}
                    />
                {:else if activeTab === 'connections'}
                    <PanelConnectionsTab
                        nodeID={displayedNodeID}
                        {readOnly}
                        onNavigate={navigate}
                    />
                {:else if activeTab === 'subnodes' && isAskNode}
                    <div class="px-4 py-3 h-full overflow-auto">
                        <AskNodeOutputDisplay
                            nodeConfig={displayedNodeConfig}
                            nodeData={displayedNode?.data ?? {}}
                            grow={true}
                        />
                    </div>
                {/if}
            </div>
        {:else}
            <!-- ── Workflow mode tab bar ──────────────────────────────────── -->
            <div class="flex shrink-0 border-b border-border px-1">
                <button
                    type="button"
                    class="px-4 py-2 text-sm border-b-2 transition-colors {workflowTab === 'test-cases'
                        ? 'border-primary text-foreground font-medium'
                        : 'border-transparent text-muted-foreground hover:text-foreground'}"
                    onclick={() => (workflowTab = 'test-cases')}
                >
                    Test Cases
                    {#if flowStore.testInputs.length > 0}
                        <span class="ml-1.5 text-xs font-normal opacity-60">{flowStore.testInputs.length}</span>
                    {/if}
                </button>
                <button
                    type="button"
                    class="px-4 py-2 text-sm border-b-2 transition-colors {workflowTab === 'runs'
                        ? 'border-primary text-foreground font-medium'
                        : 'border-transparent text-muted-foreground hover:text-foreground'}"
                    onclick={() => (workflowTab = 'runs')}
                >
                    Runs
                    {#if runsTotalCount > 0}
                        <span class="ml-1.5 text-xs font-normal opacity-60">{runsTotalCount}</span>
                    {/if}
                </button>
                {#if isChatbot}
                    <button
                        type="button"
                        class="px-4 py-2 text-sm border-b-2 transition-colors {workflowTab === 'sessions'
                            ? 'border-primary text-foreground font-medium'
                            : 'border-transparent text-muted-foreground hover:text-foreground'}"
                        onclick={() => (workflowTab = 'sessions')}
                    >
                        Sessions
                    </button>
                {/if}
            </div>

            <div class="flex-1 min-h-0">
                {#if workflowTab === 'test-cases'}
                    <TestCasesPanel onRun={handlePanelRun} {readOnly} />
                {:else if workflowTab === 'sessions' && isChatbot}
                    <SessionsPanel />
                {:else}
                    <RunsPanel {readOnly} bind:totalCount={runsTotalCount} />
                {/if}
            </div>
        {/if}
    {/if}
</div>

<style>
    @keyframes indeterminate {
        0%   { transform: translateX(-100%); }
        100% { transform: translateX(400%); }
    }
</style>

