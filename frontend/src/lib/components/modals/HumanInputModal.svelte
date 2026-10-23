<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { formatDistanceToNow } from 'date-fns'
    import Icon from '@iconify/svelte'
    import * as Dialog from '$lib/components/ui/dialog'
    import { Button } from '$lib/components/ui/button'
    import { Input } from '$lib/components/ui/input'
    import type { PausedWorkflowResponse } from '$lib/types/api_types/pausedWorkflowSchemas'

    interface Props {
        isOpen: boolean
        onOpenChange: (open: boolean) => void
        workflow: PausedWorkflowResponse
        defaultAction?: 'APPROVE' | 'DECLINE' | 'OVERRIDE'
        onSubmit: (
            action: 'APPROVE' | 'DECLINE' | 'OVERRIDE',
            inputData: Record<string, any>,
            comments: string
        ) => void
    }

    let { isOpen, onOpenChange, workflow, defaultAction = 'APPROVE', onSubmit }: Props = $props()

    // svelte-ignore state_referenced_locally
    let action = $state<'APPROVE' | 'DECLINE' | 'OVERRIDE'>(defaultAction)
    let inputData = $state<Record<string, any>>({})
    let comments = $state('')

    // Sync action when the modal is opened with a specific default
    $effect(() => {
        if (isOpen) action = defaultAction
    })

    // Pre-populate input data from pause info
    $effect(() => {
        if (workflow?.current_pause?.input_data) {
            inputData = { ...workflow.current_pause.input_data }
        }
    })

    // Keyboard shortcuts
    $effect(() => {
        if (!isOpen) return
        function onKeyDown(e: KeyboardEvent) {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                handleSubmit()
            } else if (e.key === 'Escape') {
                onOpenChange(false)
            }
        }
        window.addEventListener('keydown', onKeyDown)
        return () => window.removeEventListener('keydown', onKeyDown)
    })

    function getInputSchema(): Record<string, string> {
        const wf = workflow.workflow as any
        const def = 'definition' in wf ? wf.definition : wf
        const node = def?.nodes?.find((n: any) => n.id === workflow.current_pause?.node_id)
        return node?.config?.input_schema ?? {}
    }

    function handleSubmit() {
        onSubmit(action, inputData, comments)
        onOpenChange(false)
    }

    const workflowName = $derived(
        'name' in (workflow.workflow as any)
            ? (workflow.workflow as any).name
            : 'Unnamed'
    )

    const pauseTime = $derived(
        workflow.current_pause?.pause_time
            ? formatDistanceToNow(new Date(workflow.current_pause.pause_time))
            : ''
    )
</script>

<Dialog.Root
    open={isOpen}
    onOpenChange={(open) => { if (!open) onOpenChange(false) }}
>
    <Dialog.Content class="max-w-2xl max-h-[90vh] flex flex-col p-0">
        <Dialog.Header class="px-6 py-4 border-b shrink-0">
            <Dialog.Title>Human Input Required</Dialog.Title>
            <div class="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                <span class="px-2 py-0.5 bg-yellow-500/15 text-yellow-700 dark:text-yellow-400 rounded-full text-xs">
                    Paused
                </span>
                <span>•</span>
                <span>Workflow: {workflowName}</span>
                <span>•</span>
                <span>Run: {workflow.run?.id}</span>
            </div>
        </Dialog.Header>

        <div class="flex-1 overflow-y-auto px-6 py-4 space-y-5">
            <!-- Pause message -->
            <div class="bg-muted/50 p-4 rounded-lg flex gap-3">
                <Icon icon="lucide:alert-circle" width={20} class="text-yellow-500 mt-0.5 shrink-0" />
                <div>
                    <p class="font-medium text-sm mb-1">Message</p>
                    <p class="text-sm text-muted-foreground">{workflow.current_pause?.pause_message}</p>
                    {#if pauseTime}
                        <p class="text-xs text-muted-foreground mt-1">Paused {pauseTime} ago</p>
                    {/if}
                </div>
            </div>

            <!-- Action buttons -->
            <div>
                <p class="text-sm font-medium mb-2">Action</p>
                <div class="flex gap-2">
                    <Button
                        variant={action === 'APPROVE' ? 'default' : 'outline'}
                        class={action === 'APPROVE' ? 'bg-green-600 hover:bg-green-700' : ''}
                        onclick={() => (action = 'APPROVE')}
                    >
                        Approve
                    </Button>
                    <Button
                        variant={action === 'DECLINE' ? 'destructive' : 'outline'}
                        onclick={() => (action = 'DECLINE')}
                    >
                        Decline
                    </Button>
                    <Button
                        variant={action === 'OVERRIDE' ? 'default' : 'outline'}
                        class={action === 'OVERRIDE' ? 'bg-yellow-500 hover:bg-yellow-600' : ''}
                        onclick={() => (action = 'OVERRIDE')}
                    >
                        Override
                    </Button>
                </div>
            </div>

            <!-- Input fields (not shown when declining) -->
            {#if action !== 'DECLINE'}
                {@const schema = getInputSchema()}
                {#if Object.keys(schema).length > 0}
                    <div>
                        <p class="text-sm font-medium mb-2">Required Inputs</p>
                        <div class="space-y-3">
                            {#each Object.entries(schema) as [key, type]}
                                <div>
                                    <p class="block text-xs text-muted-foreground mb-1">{key}</p>
                                    {#if (type as string).toLowerCase() === 'boolean'}
                                        <select
                                            class="text-sm border border-border rounded-md px-2 py-1 bg-background w-full"
                                            value={String(inputData[key] ?? 'true')}
                                            onchange={(e) =>
                                                (inputData = {
                                                    ...inputData,
                                                    [key]: (e.target as HTMLSelectElement).value === 'true',
                                                })}
                                        >
                                            <option value="true">True</option>
                                            <option value="false">False</option>
                                        </select>
                                    {:else}
                                        <Input
                                            type={(type as string).toLowerCase() === 'number' ? 'number' : 'text'}
                                            class="text-sm"
                                            placeholder="Enter {key}"
                                            value={String(inputData[key] ?? '')}
                                            oninput={(e) =>
                                                (inputData = {
                                                    ...inputData,
                                                    [key]:
                                                        (type as string).toLowerCase() === 'number'
                                                            ? Number((e.target as HTMLInputElement).value)
                                                            : (e.target as HTMLInputElement).value,
                                                })}
                                        />
                                    {/if}
                                </div>
                            {/each}
                        </div>
                    </div>
                {/if}
            {/if}

            <!-- Comments -->
            <div>
                <p class="text-sm font-medium mb-2">Comments</p>
                <textarea
                    class="w-full text-sm border border-border rounded-lg px-3 py-2 bg-background resize-y min-h-[80px] focus:outline-none focus:border-primary"
                    placeholder="Add any comments about your decision..."
                    bind:value={comments}
                ></textarea>
            </div>
        </div>

        <div class="px-6 py-4 border-t flex justify-end gap-2 shrink-0">
            <Button variant="outline" onclick={() => onOpenChange(false)}>
                Cancel
                <span class="ml-1 text-xs opacity-60">ESC</span>
            </Button>
            <Button onclick={handleSubmit}>
                Submit Decision
                <span class="ml-1 text-xs opacity-60">⌘+↵</span>
            </Button>
        </div>
    </Dialog.Content>
</Dialog.Root>
