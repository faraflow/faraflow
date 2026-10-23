<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { useSvelteFlow } from '@xyflow/svelte'
    import { flowStore } from '$lib/stores/flow.svelte'

    const { fitView } = useSvelteFlow()

    let hasFit = false

    $effect(() => {
        if (hasFit) return
        const nodes = flowStore.nodes
        if (nodes.length === 0) return

        // Run after the current microtask so SvelteFlow has rendered node dimensions
        hasFit = true
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                const inputNode = nodes.find((n) => n.type === 'InputNode')
                if (inputNode) {
                    fitView({ nodes: [{ id: inputNode.id }], duration: 400, maxZoom: 0.75, padding: 0.3 })
                } else {
                    fitView({ duration: 400, maxZoom: 0.75, padding: 0.15 })
                }
            })
        })
    })
</script>
