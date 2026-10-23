// Copyright 2026 Alokin LLC
// SPDX-License-Identifier: FCL-1.0-ALv2
import { flowStore } from '$lib/stores/flow.svelte'
import { startRun, getRunStatus } from '$lib/utils/api'

interface ChatMessage {
    role: string
    message: string
    runId?: string
}

interface UseChatExecutionOptions {
    workflowID?: string
    sessionId?: string | null
}

// ---------------------------------------------------------------------------
// Module-level state
// ---------------------------------------------------------------------------

export const chatState = $state({
    isLoading: false,
    error: null as string | null,
})

let statusIntervals: ReturnType<typeof setInterval>[] = []

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function clearIntervals() {
    statusIntervals.forEach((id) => clearInterval(id))
    statusIntervals = []
}

function updateNodeStatuses(tasks: any[]) {
    if (tasks.length === 0) return
    const nodes = flowStore.nodes

    tasks.forEach((task: any) => {
        const nodeId = task.node_id
        let node = nodes.find((n) => n.id === nodeId || n.data?.title === nodeId)

        if (!node) {
            const correspondingNodeId = Object.keys(flowStore.nodeConfigs).find(
                (key) => flowStore.nodeConfigs[key]?.title === nodeId
            )
            if (correspondingNodeId) {
                node = nodes.find((n) => n.id === correspondingNodeId)
            }
        }

        if (task.subworkflow_output) {
            Object.entries(task.subworkflow_output).forEach(([subNodeId, outputs]) => {
                const subNode = nodes.find((n) => n.id === subNodeId || n.data?.title === subNodeId)
                if (subNode) {
                    flowStore.updateNodeDataOnly(subNode.id, { run: outputs, taskStatus: 'COMPLETED' })
                }
            })
        }

        if (node) {
            flowStore.updateNodeDataOnly(node.id, {
                run: task.outputs ?? {},
                error: task.error ?? null,
                taskStatus: task.status,
            })
        }
    })
}

// ---------------------------------------------------------------------------
// executeChat — send a message through a workflow and return the response
// ---------------------------------------------------------------------------

export async function executeChat(
    message: string,
    options: UseChatExecutionOptions
): Promise<ChatMessage | null> {
    const { workflowID, sessionId } = options

    if (!workflowID) {
        chatState.error = 'No workflow connected'
        return null
    }

    try {
        chatState.isLoading = true
        chatState.error = null
        clearIntervals()
        flowStore.resetRun()

        const result = await startRun(
            workflowID,
            {
                input_node: {
                    user_message: message,
                    session_id: sessionId ?? `chat_session_${Date.now()}`,
                    message_history: [],
                },
            },
            null,
            'interactive'
        )

        const runID = result.id

        return new Promise<ChatMessage | null>((resolve) => {
            const interval = setInterval(async () => {
                try {
                    const statusResponse = await getRunStatus(runID)
                    const tasks = statusResponse.tasks ?? []

                    updateNodeStatuses(tasks)

                    if (statusResponse.status === 'COMPLETED' || statusResponse.status === 'FAILED') {
                        clearInterval(interval)
                        statusIntervals = statusIntervals.filter((i) => i !== interval)

                        const outputNode = statusResponse.workflow_version?.definition?.nodes?.find(
                            (n: any) => n.node_type === 'OutputNode'
                        )

                        if (!outputNode) {
                            chatState.isLoading = false
                            chatState.error = 'No output node found in workflow'
                            resolve({ role: 'assistant', message: 'Error: No output node found in workflow' })
                            return
                        }

                        const outputTask = tasks.find(
                            (t: any) => t.status === 'COMPLETED' && t.node_id === outputNode.id && t.outputs
                        )

                        if (outputTask?.outputs) {
                            const content =
                                outputTask.outputs.assistant_message ?? JSON.stringify(outputTask.outputs)
                            chatState.isLoading = false
                            resolve({
                                role: 'assistant',
                                message: typeof content === 'string' ? content : JSON.stringify(content),
                                runId: runID,
                            })
                        } else if (statusResponse.status === 'FAILED') {
                            const failedTask = tasks.find((t: any) => t.status === 'FAILED')
                            const errorMessage = failedTask?.error ?? 'Workflow execution failed'
                            chatState.isLoading = false
                            chatState.error = errorMessage
                            resolve({ role: 'assistant', message: `Error: ${errorMessage}`, runId: runID })
                        } else {
                            chatState.isLoading = false
                            chatState.error = 'Workflow completed but no response was generated'
                            resolve({ role: 'assistant', message: "Sorry, I couldn't generate a response.", runId: runID })
                        }
                    }
                } catch (err) {
                    console.error('Error checking workflow status:', err)
                    clearInterval(interval)
                    statusIntervals = statusIntervals.filter((i) => i !== interval)
                    chatState.isLoading = false
                    chatState.error = 'Error checking workflow status'
                    resolve({ role: 'assistant', message: 'Sorry, an error occurred while processing your message.' })
                }
            }, 1000)

            statusIntervals.push(interval)
        })
    } catch (err: any) {
        console.error('Error executing chat workflow:', err)
        chatState.isLoading = false
        chatState.error = err?.message ?? 'Failed to execute workflow'
        return { role: 'assistant', message: 'Sorry, an error occurred while processing your message.' }
    }
}

export function cleanupChat() {
    clearIntervals()
}
