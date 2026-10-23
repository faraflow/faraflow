// Copyright 2026 Alokin LLC
// SPDX-License-Identifier: FCL-1.0-ALv2
import {
    addEdge,
    type Connection,
} from '@xyflow/svelte'
import isEqual from 'lodash.isequal'
import { v4 as uuidv4 } from 'uuid'

import type {
    CreateNodeResult,
    FlowWorkflowEdge,
    FlowWorkflowNode,
    FlowWorkflowNodeConfig,
    FlowWorkflowNodeTypesByCategory,
    Position,
} from '$lib/types/api_types/nodeTypeSchemas'
import { SpurType, type TestInput, type WorkflowDefinition } from '$lib/types/api_types/workflowSchemas'
import { isTargetAncestorOfSource } from '$lib/utils/cyclicEdgeUtils'
import { computeJsonSchemaIntersection } from '$lib/utils/schemaUtils'
import { createNode } from '$lib/utils/nodeFactory'

// ─── helpers ───────────────────────────────────────────────────────────────

function generateJsonSchema(schema: Record<string, any>): string {
    const jsonSchema = {
        type: 'object',
        properties: Object.fromEntries(Object.entries(schema).map(([key, type]) => [key, { type }])),
        required: Object.keys(schema),
    }
    return JSON.stringify(jsonSchema, null, 2)
}

function rebuildRouterNodeSchema(
    edges: FlowWorkflowEdge[],
    nodes: FlowWorkflowNode[],
    nodeConfigs: Record<string, FlowWorkflowNodeConfig>,
    routerNode: FlowWorkflowNode
) {
    const incomingEdges = edges.filter((e) => e.target === routerNode.id)
    const newSchemaProperties = incomingEdges.reduce(
        (props, edge) => {
            const srcNode = nodes.find((n) => n.id === edge.source)
            const srcConfig = srcNode ? nodeConfigs[srcNode.id] : undefined
            if (srcConfig?.output_json_schema) {
                const title = srcConfig.title || srcNode?.id
                props[title] = JSON.parse(srcConfig.output_json_schema)
            }
            return props
        },
        {} as Record<string, any>
    )
    const newOutputSchema = JSON.stringify({
        type: 'object',
        properties: newSchemaProperties,
        required: Object.keys(newSchemaProperties),
        additionalProperties: false,
    })
    const current = nodeConfigs[routerNode.id]?.output_json_schema ?? '{}'
    if (!isEqual(current, newOutputSchema)) {
        nodeConfigs[routerNode.id] = { ...(nodeConfigs[routerNode.id] ?? {}), output_json_schema: newOutputSchema }
    }
}

function rebuildCoalesceNodeSchema(
    edges: FlowWorkflowEdge[],
    nodes: FlowWorkflowNode[],
    nodeConfigs: Record<string, FlowWorkflowNodeConfig>,
    coalesceNode: FlowWorkflowNode
) {
    const incomingEdges = edges.filter((e) => e.target === coalesceNode.id)
    const schemas: string[] = []
    incomingEdges.forEach((ed) => {
        const srcNode = nodes.find((n) => n.id === ed.source)
        const srcConfig = srcNode ? nodeConfigs[srcNode.id] : undefined
        if (srcConfig?.output_json_schema) schemas.push(srcConfig.output_json_schema)
    })
    const intersectionSchema = computeJsonSchemaIntersection(schemas)
    nodeConfigs[coalesceNode.id] = { ...(nodeConfigs[coalesceNode.id] ?? {}), output_json_schema: intersectionSchema }
}

interface HistorySnapshot {
    nodes: FlowWorkflowNode[]
    edges: FlowWorkflowEdge[]
    nodeConfigs: Record<string, FlowWorkflowNodeConfig>
}

// ─── store ─────────────────────────────────────────────────────────────────

class FlowStore {
    // @xyflow/svelte requires $state.raw for nodes/edges — never mutate, always reassign
    nodes = $state.raw<FlowWorkflowNode[]>([])
    edges = $state.raw<FlowWorkflowEdge[]>([])

    nodeConfigs = $state<Record<string, FlowWorkflowNodeConfig>>({})
    nodeTypes = $state<FlowWorkflowNodeTypesByCategory>({})
    workflowID = $state<string | null>(null)
    selectedNode = $state<string | null>(null)
    selectedEdgeId = $state<string | null>(null)
    sidebarWidth = $state(400)
    projectName = $state('Untitled Project')
    workflowInputVariables = $state<Record<string, any>>({})
    testInputs = $state<TestInput[]>([])
    inputNodeValues = $state<Record<string, any>>({})
    selectedTestInputId = $state<string | null>(null)
    isRunModalOpen = $state(false)
    spurType = $state<SpurType>(SpurType.WORKFLOW)

    history = $state<{
        past: Array<HistorySnapshot>
        future: Array<HistorySnapshot>
    }>({ past: [], future: [] })

    clipboard = $state<{
        nodes: FlowWorkflowNode[]
        edges: FlowWorkflowEdge[]
        configs: Record<string, FlowWorkflowNodeConfig>
    } | null>(null)

    // ── derived ──────────────────────────────────────────────────────────

    selectedNodeData = $derived(
        this.selectedNode ? this.nodeConfigs[this.selectedNode] ?? null : null
    )

    // ── history helpers ──────────────────────────────────────────────────

    #snapshot(): HistorySnapshot {
        return {
            nodes: JSON.parse(JSON.stringify(this.nodes)),
            edges: JSON.parse(JSON.stringify(this.edges)),
            nodeConfigs: JSON.parse(JSON.stringify(this.nodeConfigs)),
        }
    }

    #saveToHistory() {
        this.history = {
            past: [...this.history.past, this.#snapshot()],
            future: [],
        }
    }

    #restoreSnapshot(snapshot: HistorySnapshot) {
        this.nodes = snapshot.nodes
        this.edges = snapshot.edges
        this.nodeConfigs = snapshot.nodeConfigs
        if (this.selectedNode && !snapshot.nodes.some((n) => n.id === this.selectedNode)) {
            this.selectedNode = null
        }
        if (this.selectedEdgeId && !snapshot.edges.some((e) => e.id === this.selectedEdgeId)) {
            this.selectedEdgeId = null
        }
    }

    // ── actions ──────────────────────────────────────────────────────────

    initializeFlow(payload: {
        workflowID: string
        definition: WorkflowDefinition
        name: string
        nodeTypes: FlowWorkflowNodeTypesByCategory
    }) {
        const { workflowID, definition, name, nodeTypes } = payload
        this.workflowID = workflowID
        this.projectName = name
        this.nodeTypes = nodeTypes
        this.spurType = definition.spur_type ?? SpurType.WORKFLOW

        const newConfigs: Record<string, FlowWorkflowNodeConfig> = {}
        const newNodes: FlowWorkflowNode[] = []

        for (const node of definition.nodes) {
            const result = createNode(
                nodeTypes,
                node.node_type,
                node.id,
                { x: node.coordinates.x, y: node.coordinates.y },
                node.parent_id ?? null,
                node.dimensions ?? null,
                node.title ?? null
            )
            if (!result) continue
            newNodes.push(result.node)
            newConfigs[node.id] = node.config
        }

        this.nodes = newNodes
        this.nodeConfigs = newConfigs

        let edges: FlowWorkflowEdge[] = definition.links.map((link) => ({
            id: uuidv4(),
            key: uuidv4(),
            type: 'custom',
            selected: false,
            source: link.source_id,
            target: link.target_id,
            sourceHandle: link.source_handle ?? link.source_id,
            targetHandle: link.target_handle ?? link.source_id,
        }))
        // deduplicate
        edges = edges.filter(
            (edge, idx, self) =>
                idx === self.findIndex((t) => t.source === edge.source && t.target === edge.target)
        )
        this.edges = edges

        // Load test inputs from the definition if present
        this.testInputs = definition.test_inputs ?? []

        // reset history
        this.history = { past: [], future: [] }
    }

    connect(connection: Connection) {
        if (
            isTargetAncestorOfSource(
                connection.source,
                connection.target,
                this.nodes,
                this.edges
            )
        ) return

        // Avoid duplicates
        if (this.edges.find((e) => e.source === connection.source && e.target === connection.target)) return

        this.#saveToHistory()

        const srcNode = this.nodes.find((n) => n.id === connection.source)
        const tgtNode = this.nodes.find((n) => n.id === connection.target)
        if (!tgtNode) return

        // Only allow connections within the same parent
        if (srcNode && srcNode.parentId !== tgtNode.parentId) return

        // Normalize targetHandle so it matches the handle ID that InputHandleRow renders.
        // During drag, @xyflow connects to the temporary "node-body-{id}" handle; after the
        // connection is made that handle disappears. InputHandleRow uses the source node ID
        // (or "routerNodeId.branchHandleId" for RouterNode) as its handle ID, so we normalize
        // here to match what will be rendered.
        const normalizedTargetHandle =
            srcNode?.type === 'RouterNode' && connection.sourceHandle
                ? `${connection.source}.${connection.sourceHandle}`
                : connection.source

        const normalizedConnection = {
            ...connection,
            targetHandle: normalizedTargetHandle,
            type: 'custom',
        }

        this.edges = addEdge(normalizedConnection, this.edges) as FlowWorkflowEdge[]

        const configs = { ...this.nodeConfigs }
        if (tgtNode.type === 'RouterNode') {
            rebuildRouterNodeSchema(this.edges, this.nodes, configs, tgtNode)
            this.nodeConfigs = configs
        }
        if (tgtNode.type === 'CoalesceNode') {
            rebuildCoalesceNodeSchema(this.edges, this.nodes, configs, tgtNode)
            this.nodeConfigs = configs
        }
    }

    setNodes(nodes: FlowWorkflowNode[]) {
        this.nodes = nodes
    }

    setEdges(edges: FlowWorkflowEdge[]) {
        this.edges = edges
    }

    updateNodeDataOnly(id: string, data: any) {
        this.nodes = this.nodes.map((n) => {
            if (n.id !== id) return n
            return {
                ...n,
                data: {
                    ...n.data,
                    ...data,
                    taskStatus: data.taskStatus !== undefined ? data.taskStatus : n.data?.taskStatus,
                },
            }
        })
    }

    updateNodeConfigOnly(id: string, data: any) {
        const current = this.nodeConfigs[id] ?? {}
        const updated: Record<string, FlowWorkflowNodeConfig> = {
            ...this.nodeConfigs,
            [id]: data.few_shot_examples !== undefined
                ? { ...current, ...data, few_shot_examples: data.few_shot_examples }
                : { ...current, ...data },
        }

        if (data?.output_schema || data?.output_json_schema) {
            const routerNodes = this.nodes.filter(
                (t) => t.type === 'RouterNode' && this.edges.some((e) => e.source === id && e.target === t.id)
            )
            routerNodes.forEach((r) => rebuildRouterNodeSchema(this.edges, this.nodes, updated, r))

            const coalesceNodes = this.nodes.filter(
                (t) => t.type === 'CoalesceNode' && this.edges.some((e) => e.source === id && e.target === t.id)
            )
            coalesceNodes.forEach((c) => rebuildCoalesceNodeSchema(this.edges, this.nodes, updated, c))
        }

        this.nodeConfigs = updated
    }

    addToolToAgent(nodeId: string, nodeTypeName: string) {
        const parentNode = this.nodes.find((n) => n.id === nodeId)
        if (!parentNode) return

        const sanitizedType = nodeTypeName.replace(/\s+/g, '_').replace(/Node/g, 'Tool')
        const existingTitles = this.nodes.map((n) => n.data?.title)
        let counter = 1
        let newTitle = `${sanitizedType}_${counter}`
        while (existingTitles.includes(newTitle)) {
            counter++
            newTitle = `${sanitizedType}_${counter}`
        }

        const result = createNode(this.nodeTypes, nodeTypeName, uuidv4(), { x: 0, y: 0 }, nodeId, null, newTitle)
        if (!result) return

        this.nodes = [...this.nodes, result.node]
        this.nodeConfigs = { ...this.nodeConfigs, [result.node.id]: result.config }
    }

    setSelectedNode(nodeId: string | null) {
        this.selectedNode = nodeId
        // Sync SvelteFlow's built-in selection state so the node gets highlighted
        this.nodes = this.nodes.map((n) => ({ ...n, selected: n.id === nodeId }))
    }

    setSelectedEdgeId(edgeId: string | null) {
        this.selectedEdgeId = edgeId
    }

    deleteNode(nodeId: string) {
        this.#saveToHistory()
        this.#removeNodes([nodeId])
    }

    // Batch variant: one history entry for a multi-select delete
    deleteNodes(nodeIds: string[]) {
        if (nodeIds.length === 0) return
        this.#saveToHistory()
        this.#removeNodes(nodeIds)
    }

    // Removes the given nodes, their group children, touching edges, and configs.
    // Does NOT snapshot history — callers decide when a snapshot is taken.
    #removeNodes(nodeIds: string[]) {
        const ids = new Set(nodeIds)
        this.nodes.forEach((n) => {
            if (n.parentId && ids.has(n.parentId)) ids.add(n.id)
        })

        const newConfigs = { ...this.nodeConfigs }
        ids.forEach((id) => delete newConfigs[id])
        this.nodeConfigs = newConfigs

        this.nodes = this.nodes.filter((n) => !ids.has(n.id))
        this.edges = this.edges.filter((e) => !ids.has(e.source) && !ids.has(e.target))

        if (this.selectedNode && ids.has(this.selectedNode)) this.selectedNode = null
    }

    deleteEdge(edgeId: string) {
        this.#saveToHistory()
        const edge = this.edges.find((e) => e.id === edgeId)
        if (!edge) return

        const tgtNode = this.nodes.find((n) => n.id === edge.target)
        const srcConfig = this.nodeConfigs[edge.source]
        const tgtConfig = this.nodeConfigs[edge.target]

        const updated = { ...this.nodeConfigs }

        if (tgtNode?.type === 'RouterNode' && srcConfig && tgtConfig) {
            const srcTitle = srcConfig.title
            let schema = JSON.parse(tgtConfig.output_json_schema ?? '{}')
            if (srcTitle && schema.properties) {
                delete schema.properties[srcTitle]
                schema.required = Object.keys(schema.properties)
            }
            updated[tgtNode.id] = { ...tgtConfig, output_json_schema: JSON.stringify(schema) }
        }

        if (tgtNode?.type === 'CoalesceNode') {
            const remainingEdges = this.edges.filter((e) => e.target === tgtNode.id && e.id !== edgeId)
            const schemas: string[] = []
            remainingEdges.forEach((ed) => {
                const s = this.nodeConfigs[ed.source]?.output_json_schema
                if (s) schemas.push(s)
            })
            updated[tgtNode.id] = {
                ...(tgtConfig ?? {}),
                output_json_schema: computeJsonSchemaIntersection(schemas),
            }
        }

        this.nodeConfigs = updated
        this.edges = this.edges.filter((e) => e.id !== edgeId)
    }

    deleteEdgeByHandle(nodeId: string, handleKey: string) {
        this.edges = this.edges.filter(
            (e) => !((e.source === nodeId && e.sourceHandle === handleKey) || (e.target === nodeId && e.targetHandle === handleKey))
        )
    }

    deleteEdgesBySource(sourceId: string) {
        this.edges = this.edges.filter((e) => e.source !== sourceId)
    }

    setSidebarWidth(width: number) {
        this.sidebarWidth = width
    }

    setProjectName(name: string) {
        this.projectName = name
    }

    setWorkflowInputVariable(key: string, value: any) {
        this.workflowInputVariables = { ...this.workflowInputVariables, [key]: value }

        const inputNode = this.nodes.find((n) => n.type === 'InputNode')
        if (inputNode) {
            const current = this.nodeConfigs[inputNode.id] ?? {}
            const updatedSchema = { ...(current.output_schema ?? {}), [key]: value }
            const updated = {
                ...this.nodeConfigs,
                [inputNode.id]: {
                    ...current,
                    output_schema: updatedSchema,
                    output_json_schema: generateJsonSchema(updatedSchema),
                },
            }
            this.#rebuildConnectedSpecialNodes(updated, inputNode.id)
            this.nodeConfigs = updated
        }
    }

    deleteWorkflowInputVariable(key: string) {
        const { [key]: _, ...rest } = this.workflowInputVariables
        this.workflowInputVariables = rest

        const inputNode = this.nodes.find((n) => n.type === 'InputNode')
        if (inputNode) {
            const current = this.nodeConfigs[inputNode.id] ?? {}
            const { [key]: _k, ...updatedSchema } = current.output_schema ?? {}
            const updated = {
                ...this.nodeConfigs,
                [inputNode.id]: {
                    ...current,
                    output_schema: updatedSchema,
                    output_json_schema: generateJsonSchema(updatedSchema),
                },
            }
            this.#rebuildConnectedSpecialNodes(updated, inputNode.id)
            this.nodeConfigs = updated
        }

        this.edges = this.edges.filter((e) => e.sourceHandle !== key)
    }

    updateWorkflowInputVariableKey(oldKey: string, newKey: string) {
        if (oldKey === newKey) return

        const vars = { ...this.workflowInputVariables }
        vars[newKey] = vars[oldKey]
        delete vars[oldKey]
        this.workflowInputVariables = vars

        const inputNode = this.nodes.find((n) => n.type === 'InputNode')
        if (inputNode) {
            const current = this.nodeConfigs[inputNode.id] ?? {}
            const schema = { ...(current.output_schema ?? {}) }
            if (oldKey in schema) {
                schema[newKey] = schema[oldKey]
                delete schema[oldKey]
            }
            const updated = {
                ...this.nodeConfigs,
                [inputNode.id]: {
                    ...current,
                    output_schema: schema,
                    output_json_schema: generateJsonSchema(schema),
                },
            }
            this.#rebuildConnectedSpecialNodes(updated, inputNode.id)
            this.nodeConfigs = updated
        }

        this.edges = this.edges.map((e) => (e.sourceHandle === oldKey ? { ...e, sourceHandle: newKey } : e))
    }

    resetFlow(definition: WorkflowDefinition) {
        const { nodes, links } = definition
        const newConfigs = { ...this.nodeConfigs }
        const newNodes: FlowWorkflowNode[] = []

        for (const node of nodes) {
            const result = createNode(this.nodeTypes, node.node_type, node.id, {
                x: node.coordinates.x,
                y: node.coordinates.y,
            })
            if (!result) throw new Error(`Failed to create node with type: ${node.node_type}`)
            newNodes.push(result.node)
            newConfigs[node.id] = result.config
        }

        this.nodes = newNodes
        this.nodeConfigs = newConfigs
        this.edges = links.map((link) => ({
            id: uuidv4(),
            key: uuidv4(),
            type: 'custom',
            selected: false,
            source: link.source_id,
            target: link.target_id,
            sourceHandle: link.source_handle ?? this.nodes.find((n) => n.id === link.source_id)?.data?.title,
            targetHandle: link.target_handle ?? this.nodes.find((n) => n.id === link.target_id)?.data?.title,
        }))
    }

    resetRun() {
        this.nodes = this.nodes.map((n) => ({
            ...n,
            data: { ...n.data, run: undefined, taskStatus: undefined, error: undefined },
        }))
    }

    clearCanvas() {
        this.nodes = []
        this.edges = []
        this.selectedNode = null
        this.workflowInputVariables = {}
        this.testInputs = []
        this.inputNodeValues = {}
    }

    setTestInputs(inputs: TestInput[]) {
        this.testInputs = inputs
    }

    addTestInput(input: TestInput) {
        this.testInputs = [...this.testInputs, input]
    }

    updateTestInput(updated: TestInput) {
        this.testInputs = this.testInputs.map((i) => (i.id === updated.id ? updated : i))
    }

    deleteTestInput(id: number) {
        this.testInputs = this.testInputs.filter((i) => i.id !== id)
    }

    setNodeOutputs(nodeOutputs: Record<string, any>) {
        this.nodes = this.nodes.map((n) => {
            if (!n || !nodeOutputs[n.id]) return n
            return {
                ...n,
                data: { ...n.data, run: nodeOutputs[n.id], taskStatus: nodeOutputs[n.id].status },
            }
        })
    }

    undo() {
        const previous = [...this.history.past]
        const snapshot = previous.pop()
        if (!snapshot) return
        this.history = {
            past: previous,
            future: [this.#snapshot(), ...this.history.future],
        }
        this.#restoreSnapshot(snapshot)
    }

    redo() {
        const future = [...this.history.future]
        const snapshot = future.shift()
        if (!snapshot) return
        this.history = {
            past: [...this.history.past, this.#snapshot()],
            future,
        }
        this.#restoreSnapshot(snapshot)
    }

    // ── clipboard ────────────────────────────────────────────────────────

    copySelection() {
        let selected = this.nodes.filter((n) => n.selected)
        if (selected.length === 0 && this.selectedNode) {
            selected = this.nodes.filter((n) => n.id === this.selectedNode)
        }
        if (selected.length === 0) return

        // Include group children of any selected group node
        const ids = new Set(selected.map((n) => n.id))
        this.nodes.forEach((n) => {
            if (n.parentId && ids.has(n.parentId) && !ids.has(n.id)) {
                ids.add(n.id)
                selected = [...selected, n]
            }
        })

        const configs: Record<string, FlowWorkflowNodeConfig> = {}
        ids.forEach((id) => {
            if (this.nodeConfigs[id]) configs[id] = this.nodeConfigs[id]
        })

        this.clipboard = JSON.parse(
            JSON.stringify({
                nodes: selected,
                // Only edges fully inside the selection travel with it
                edges: this.edges.filter((e) => ids.has(e.source) && ids.has(e.target)),
                configs,
            })
        )
    }

    cutSelection() {
        this.copySelection()
        if (!this.clipboard) return
        this.#saveToHistory()
        this.#removeNodes(this.clipboard.nodes.map((n) => n.id))
    }

    paste() {
        if (!this.clipboard || this.clipboard.nodes.length === 0) return
        this.#saveToHistory()

        const idMap: Record<string, string> = {}
        this.clipboard.nodes.forEach((n) => (idMap[n.id] = uuidv4()))

        // Handle IDs embed node ids: either the source node id itself or
        // "routerNodeId.branchHandleId" (see connect()) — remap both forms.
        const remapHandle = (handle: string | null | undefined): string | null | undefined => {
            if (!handle) return handle
            if (idMap[handle]) return idMap[handle]
            const dot = handle.indexOf('.')
            if (dot > 0 && idMap[handle.slice(0, dot)]) {
                return `${idMap[handle.slice(0, dot)]}${handle.slice(dot)}`
            }
            return handle
        }

        // Titles are used as schema keys by Router/Coalesce rebuilds — keep them unique
        const usedTitles = new Set(this.nodes.map((n) => n.data?.title).filter(Boolean))
        const uniqueTitle = (title: string): string => {
            if (!usedTitles.has(title)) {
                usedTitles.add(title)
                return title
            }
            let counter = 1
            while (usedTitles.has(`${title}_copy${counter > 1 ? counter : ''}`)) counter++
            const t = `${title}_copy${counter > 1 ? counter : ''}`
            usedTitles.add(t)
            return t
        }

        const newConfigs = { ...this.nodeConfigs }
        const newNodes = this.clipboard.nodes.map((n) => {
            const newId = idMap[n.id]
            const parentRemapped = n.parentId ? idMap[n.parentId] : undefined
            const title = n.data?.title ? uniqueTitle(n.data.title) : n.data?.title
            const node: FlowWorkflowNode = {
                ...JSON.parse(JSON.stringify(n)),
                id: newId,
                selected: true,
                // Children keep their parent-relative position; top-level nodes offset
                position: parentRemapped
                    ? n.position
                    : { x: n.position.x + 50, y: n.position.y + 50 },
                parentId: parentRemapped,
                extent: parentRemapped ? ('parent' as const) : undefined,
                expandParent: parentRemapped ? true : undefined,
            }
            if (node.data) node.data = { ...node.data, title }
            const config = this.clipboard!.configs[n.id]
            if (config) {
                newConfigs[newId] = { ...JSON.parse(JSON.stringify(config)), title }
            }
            return node
        })

        const newEdges = this.clipboard.edges.map((e) => ({
            ...JSON.parse(JSON.stringify(e)),
            id: uuidv4(),
            key: uuidv4(),
            selected: false,
            source: idMap[e.source],
            target: idMap[e.target],
            sourceHandle: remapHandle(e.sourceHandle),
            targetHandle: remapHandle(e.targetHandle),
        }))

        this.nodes = [...this.nodes.map((n) => ({ ...n, selected: false })), ...newNodes]
        this.edges = [...this.edges, ...newEdges]
        this.nodeConfigs = newConfigs
    }

    updateNodeTitle(nodeId: string, newTitle: string) {
        this.nodes = this.nodes.map((n) =>
            n.id === nodeId ? { ...n, data: { ...n.data, title: newTitle } } : n
        )
        if (this.nodeConfigs[nodeId]) {
            this.nodeConfigs = {
                ...this.nodeConfigs,
                [nodeId]: { ...this.nodeConfigs[nodeId], title: newTitle },
            }
        }
    }

    addNodeWithConfig(result: CreateNodeResult) {
        this.#saveToHistory()
        this.nodes = [...this.nodes, result.node]
        this.nodeConfigs = { ...this.nodeConfigs, [result.node.id]: result.config }
    }

    // Batch variant: one history entry for compound creations (e.g. a loop node
    // plus its input/output children), so a single undo removes the whole group.
    addNodesWithConfigs(results: CreateNodeResult[]) {
        if (results.length === 0) return
        this.#saveToHistory()
        this.nodes = [...this.nodes, ...results.map((r) => r.node)]
        const configs = { ...this.nodeConfigs }
        for (const r of results) configs[r.node.id] = r.config
        this.nodeConfigs = configs
    }

    updateNodeParentAndCoordinates(nodeId: string, parentId: string | undefined, position: Position) {
        this.nodes = this.nodes.map((n) =>
            n.id === nodeId
                ? { ...n, parentId, position, extent: parentId ? ('parent' as const) : undefined, expandParent: parentId ? true : undefined }
                : n
        )
    }

    updateNodesFromPartialRun(outputs: Record<string, any>) {
        this.nodes = this.nodes.map((n) => {
            const nodeOutput = outputs[n.id] ?? (n.data?.title ? outputs[n.data.title] : undefined)
            if (!nodeOutput) return n
            return {
                ...n,
                data: { ...n.data, run: nodeOutput, taskStatus: 'COMPLETED', error: undefined },
            }
        })
    }

    setSelectedTestInputId(id: string | null) {
        this.selectedTestInputId = id
    }

    setRunModalOpen(open: boolean) {
        this.isRunModalOpen = open
    }

    // ── private helpers ──────────────────────────────────────────────────

    #rebuildConnectedSpecialNodes(configs: Record<string, FlowWorkflowNodeConfig>, sourceId: string) {
        const routerNodes = this.nodes.filter(
            (t) => t.type === 'RouterNode' && this.edges.some((e) => e.source === sourceId && e.target === t.id)
        )
        routerNodes.forEach((r) => rebuildRouterNodeSchema(this.edges, this.nodes, configs, r))

        const coalesceNodes = this.nodes.filter(
            (t) => t.type === 'CoalesceNode' && this.edges.some((e) => e.source === sourceId && e.target === t.id)
        )
        coalesceNodes.forEach((c) => rebuildCoalesceNodeSchema(this.edges, this.nodes, configs, c))
    }
}

export const flowStore = new FlowStore()
