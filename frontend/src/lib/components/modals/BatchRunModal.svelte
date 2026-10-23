<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { onMount } from 'svelte'
    import { toast } from 'svelte-sonner'
    import * as Dialog from '$lib/components/ui/dialog'
    import { Button } from '$lib/components/ui/button'
    import { getWorkflows, startBatchRun } from '$lib/utils/api'
    import type { WorkflowResponse } from '$lib/types/api_types/workflowSchemas'

    interface Props {
        isOpen: boolean
        onOpenChange: (open: boolean) => void
        datasetId: string
        onStarted: () => void
    }

    let { isOpen, onOpenChange, datasetId, onStarted }: Props = $props()

    let workflows = $state<WorkflowResponse[]>([])
    let workflowId = $state('')
    let miniBatchSize = $state(10)
    let isLoading = $state(true)
    let isStarting = $state(false)

    onMount(async () => {
        try {
            // Paginate through all workflows so the select is complete
            let page = 1
            let all: WorkflowResponse[] = []
            while (true) {
                const batch = await getWorkflows(page, 50)
                all = [...all, ...batch]
                if (batch.length < 50) break
                page++
            }
            workflows = all
        } catch {
            toast.error('Failed to load workflows')
        } finally {
            isLoading = false
        }
    })

    async function handleStart() {
        if (!workflowId) { toast.error('Please select a workflow'); return }
        try {
            isStarting = true
            await startBatchRun(workflowId, datasetId, miniBatchSize)
            toast.success('Batch run started')
            onStarted()
            onOpenChange(false)
        } catch (err: any) {
            // Backend 400s with a helpful detail when dataset columns don't
            // match the workflow's input schema — surface it verbatim.
            // response.data.detail holds the raw body text, usually {"detail": "..."}
            let detail: string | undefined = err?.response?.data?.detail
            if (detail) {
                try {
                    detail = JSON.parse(detail)?.detail ?? detail
                } catch {
                    /* not JSON — use as-is */
                }
            }
            toast.error(detail || 'Failed to start batch run')
            console.error(err)
        } finally {
            isStarting = false
        }
    }
</script>

<Dialog.Root open={isOpen} onOpenChange={(open) => { if (!open) onOpenChange(false) }}>
    <Dialog.Content class="max-w-md">
        <Dialog.Header>
            <Dialog.Title>Start Batch Run</Dialog.Title>
            <Dialog.Description>
                Run a workflow once per dataset row. The dataset's columns must include every field
                of the workflow's input schema.
            </Dialog.Description>
        </Dialog.Header>

        <div class="space-y-4 py-2">
            <div>
                <label for="batch-workflow" class="block text-sm font-medium mb-1.5">Workflow</label>
                <select
                    id="batch-workflow"
                    bind:value={workflowId}
                    disabled={isLoading}
                    class="w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                >
                    <option value="">{isLoading ? 'Loading...' : 'Select a workflow...'}</option>
                    {#each workflows as wf}
                        <option value={wf.id}>{wf.name}</option>
                    {/each}
                </select>
            </div>
            <div>
                <label for="batch-size" class="block text-sm font-medium mb-1.5">Mini-batch size</label>
                <input
                    id="batch-size"
                    type="number"
                    bind:value={miniBatchSize}
                    min={1}
                    max={100}
                    class="w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                />
                <p class="text-xs text-muted-foreground mt-1">How many rows run concurrently.</p>
            </div>
        </div>

        <Dialog.Footer>
            <Button variant="ghost" onclick={() => onOpenChange(false)}>Cancel</Button>
            <Button onclick={handleStart} disabled={isStarting || !workflowId}>
                {isStarting ? 'Starting...' : 'Start Batch Run'}
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
