<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { useStore } from '@xyflow/svelte'

    interface Props {
        horizontal?: number
        vertical?: number
    }

    let { horizontal, vertical }: Props = $props()

    const store = useStore()

    let canvas: HTMLCanvasElement

    $effect(() => {
        // Re-draw whenever dimensions, viewport, or line positions change
        const w = store.width
        const h = store.height
        const vp = store.viewport
        const hLine = horizontal
        const vLine = vertical

        const ctx = canvas?.getContext('2d')
        if (!ctx || !canvas) return

        const dpi = window.devicePixelRatio
        canvas.width = w * dpi
        canvas.height = h * dpi
        ctx.scale(dpi, dpi)
        ctx.clearRect(0, 0, w, h)
        ctx.strokeStyle = '#0041d0'

        if (typeof vLine === 'number') {
            ctx.beginPath()
            ctx.moveTo(vLine * vp.zoom + vp.x, 0)
            ctx.lineTo(vLine * vp.zoom + vp.x, h)
            ctx.stroke()
        }

        if (typeof hLine === 'number') {
            ctx.beginPath()
            ctx.moveTo(0, hLine * vp.zoom + vp.y)
            ctx.lineTo(w, hLine * vp.zoom + vp.y)
            ctx.stroke()
        }
    })
</script>

<canvas
    bind:this={canvas}
    class="svelte-flow__canvas"
    style="width:100%;height:100%;position:absolute;z-index:10;pointer-events:none;"
/>
