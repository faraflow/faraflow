<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { useSvelteFlow } from '@xyflow/svelte'
    import { panelStore } from '$lib/stores/panel.svelte'

    const { fitView } = useSvelteFlow()

    panelStore.registerPanToNode((nodeId: string) => {
        fitView({ nodes: [{ id: nodeId }], duration: 500, maxZoom: 0.75 })
    })
</script>
