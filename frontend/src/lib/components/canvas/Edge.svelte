<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { BaseEdge, EdgeLabel, getBezierPath, useSvelteFlow, useStore, type EdgeProps } from '@xyflow/svelte'
    import { Button } from '$lib/components/ui/button'
    import Icon from '@iconify/svelte'
    import { flowStore } from '$lib/stores/flow.svelte'
    import { mode } from 'mode-watcher'
    import { getContext } from 'svelte'

    interface EdgeDisplayContext {
        hoveredEdge: string | null
        hoveredNode: string | null
        selectedEdgeId: string | null
        isDark: boolean
        handlePopoverOpen: ((data: any) => void) | null
        onLabelEnter: () => void
        onLabelLeave: () => void
    }

    interface Props extends EdgeProps {
        readOnly?: boolean
    }

    let {
        id,
        sourceX,
        sourceY,
        targetX,
        targetY,
        sourcePosition,
        targetPosition,
        style = '',
        markerEnd,
        source,
        target,
        readOnly = false,
    }: Props = $props()

    const { getNode, screenToFlowPosition } = useSvelteFlow()
    const store = $derived(useStore())
    const zoom = $derived(store.viewport.zoom)
    const edgeCtx = getContext<EdgeDisplayContext | undefined>('edgeDisplayContext')

    const isDark = $derived(edgeCtx ? edgeCtx.isDark : $mode === 'dark')

    const [edgePath, labelX, labelY] = $derived(
        getBezierPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition })
    )

    const isHovered = $derived(edgeCtx?.hoveredEdge === id || edgeCtx?.selectedEdgeId === id)
    const isEndpointHovered = $derived(edgeCtx?.hoveredNode === source || edgeCtx?.hoveredNode === target)
    const highlighted = $derived(!!(isHovered || isEndpointHovered))

    const stroke = $derived(
        highlighted ? (isDark ? '#fff' : '#555') : (isDark ? '#666' : '#999')
    )
    const strokeWidth = $derived(highlighted ? 3 : 1.5)
    const edgeStyle = $derived(`stroke-width: ${strokeWidth}; stroke: ${stroke}; ${style}`)

    // ── Cursor tracking ──────────────────────────────────────────────────────
    // We render a wide transparent path on top of the edge so that the full
    // stroke area (not just the hairline) is a pointer-event target.  As the
    // cursor moves along it we record both the screen position (for the
    // proximity check) and the flow position (for label placement).

    let cursorFlowPos = $state<{ x: number; y: number } | null>(null)
    let cursorClientPos = $state<{ x: number; y: number } | null>(null)
    let isLabelHovered = $state(false)
    let pathLeaveTimer: ReturnType<typeof setTimeout> | null = null

    function onPathPointerMove(e: PointerEvent) {
        cursorClientPos = { x: e.clientX, y: e.clientY }
        cursorFlowPos = screenToFlowPosition({ x: e.clientX, y: e.clientY })
    }

    function onPathPointerLeave() {
        // Small delay so a cursor sliding onto the label div doesn't flicker.
        // Also keep the position frozen while the edge is selected so the
        // toolbar stays at the click position after the cursor leaves.
        pathLeaveTimer = setTimeout(() => {
            if (!isLabelHovered && edgeCtx?.selectedEdgeId !== id) {
                cursorFlowPos = null
                cursorClientPos = null
            }
            pathLeaveTimer = null
        }, 50)
    }

    function onLabelPointerEnter() {
        if (pathLeaveTimer) { clearTimeout(pathLeaveTimer); pathLeaveTimer = null }
        isLabelHovered = true
        edgeCtx?.onLabelEnter?.()
    }

    function onLabelPointerLeave() {
        isLabelHovered = false
        if (edgeCtx?.selectedEdgeId !== id) {
            cursorFlowPos = null
            cursorClientPos = null
        }
        edgeCtx?.onLabelLeave?.()
    }

    // When the edge is deselected, clear the frozen cursor position.
    $effect(() => {
        if (edgeCtx?.selectedEdgeId !== id) {
            cursorFlowPos = null
            cursorClientPos = null
        }
    })

    // Returns true when the cursor is within --edge-handle-proximity em of
    // either endpoint handle (measured in screen pixels).
    const isTooCloseToHandle = $derived.by(() => {
        if (!cursorClientPos) return false
        const vp = store.viewport
        const srcScreen = { x: sourceX * vp.zoom + vp.x, y: sourceY * vp.zoom + vp.y }
        const tgtScreen = { x: targetX * vp.zoom + vp.x, y: targetY * vp.zoom + vp.y }

        const rootEm = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16
        const threshEm = parseFloat(
            getComputedStyle(document.documentElement)
                .getPropertyValue('--edge-handle-proximity')
                .trim() || '4'
        )
        const threshPx = threshEm * rootEm

        return (
            Math.hypot(cursorClientPos.x - srcScreen.x, cursorClientPos.y - srcScreen.y) < threshPx ||
            Math.hypot(cursorClientPos.x - tgtScreen.x, cursorClientPos.y - tgtScreen.y) < threshPx
        )
    })

    // Show the toolbar at the cursor position — whether the edge is hovered or
    // selected.  cursorFlowPos is frozen at the click position while selected,
    // so the toolbar stays put after the mouse leaves.
    const showLabel = $derived(
        !readOnly &&
        (edgeCtx?.hoveredEdge === id || edgeCtx?.selectedEdgeId === id) &&
        !!cursorFlowPos &&
        !isTooCloseToHandle
    )

    const effectiveLabelX = $derived(cursorFlowPos?.x ?? labelX)
    const effectiveLabelY = $derived(cursorFlowPos?.y ?? labelY)

    function handleDeleteEdge(e: MouseEvent) {
        e.stopPropagation()
        flowStore.deleteEdge(id)
    }

    function handleAddNode(e: MouseEvent) {
        e.stopPropagation()
        const popoverOpen = edgeCtx?.handlePopoverOpen
        if (!popoverOpen) return
        const sourceNode = getNode(source)
        const targetNode = getNode(target)
        if (!sourceNode || !targetNode) return
        popoverOpen({
            sourceNode: { id: sourceNode.id, position: sourceNode.position, data: sourceNode.data },
            targetNode: { id: targetNode.id, position: targetNode.position, data: targetNode.data },
            edgeId: id,
            screenPosition: { x: e.clientX, y: e.clientY },
        })
    }
</script>

<BaseEdge path={edgePath} {markerEnd} style={edgeStyle} />

<!-- Wide transparent hit area so the full stroke thickness captures pointer events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<path
    d={edgePath}
    stroke="rgba(0,0,0,0)"
    stroke-width={20 / zoom}
    fill="none"
    style="pointer-events: stroke;"
    onpointermove={onPathPointerMove}
    onpointerleave={onPathPointerLeave}
/>

{#if showLabel}
    <EdgeLabel x={effectiveLabelX} y={effectiveLabelY}>
        <div
            class="nodrag nopan flex gap-1 items-center bg-background rounded-full shadow-md p-1"
            style="transform: scale({1 / zoom}); transform-origin: center;"
            role="presentation"
            onpointerenter={onLabelPointerEnter}
            onpointerleave={onLabelPointerLeave}
        >
            <Button
                variant="ghost"
                size="icon"
                class="h-6 w-6 rounded-full hover:bg-muted"
                onclick={(e) => handleAddNode(e)}
            >
                <Icon icon="solar:add-circle-bold-duotone" class="text-primary" width={18} />
            </Button>
            <Button
                variant="ghost"
                size="icon"
                class="h-6 w-6 rounded-full hover:bg-muted"
                onclick={handleDeleteEdge}
            >
                <Icon icon="solar:trash-bin-trash-bold-duotone" class="text-destructive" width={18} />
            </Button>
        </div>
    </EdgeLabel>
{/if}
