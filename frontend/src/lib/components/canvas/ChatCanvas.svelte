<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { sidebarPanels } from '$lib/stores/sidebarPanels.svelte'
    import EditorCanvas from './EditorCanvas.svelte'
    import Chat from '$lib/components/chat/Chat.svelte'
    import type { WorkflowCreateRequest, WorkflowResponse } from '$lib/types/api_types/workflowSchemas'

    interface Props {
        workflowData?: WorkflowCreateRequest | WorkflowResponse
        workflowID?: string
        onDownloadImageInit?: (handler: () => void) => void
        onStop?: () => void
    }

    let { workflowData, workflowID, onDownloadImageInit, onStop }: Props = $props()
</script>

<EditorCanvas {workflowData} {workflowID} {onDownloadImageInit} {onStop}>
    {#snippet sidebarExtra()}
        <div class="flex flex-col flex-1 min-h-0">
            <Chat workflowID={workflowID} onClose={() => sidebarPanels.toggle('chat')} />
        </div>
    {/snippet}
</EditorCanvas>
