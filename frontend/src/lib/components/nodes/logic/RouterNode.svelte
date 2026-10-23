<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
<script lang="ts">
    import { Handle, Position, useUpdateNodeInternals } from '@xyflow/svelte'
    import Icon from '@iconify/svelte'
    import { Button } from '$lib/components/ui/button'
    import { Input } from '$lib/components/ui/input'
    import { flowStore } from '$lib/stores/flow.svelte'
    import BaseNode from '../BaseNode.svelte'
    import { ComparisonOperator, type RouteConditionGroup, type RouteConditionRule } from '$lib/types/api_types/routerSchemas'

    interface Props {
        id: string
        data?: any
        positionAbsoluteX?: number
        positionAbsoluteY?: number
    }

    let { id, data, positionAbsoluteX = 0, positionAbsoluteY = 0 }: Props = $props()

    let isCollapsed = $state(false)

    const updateNodeInternals = useUpdateNodeInternals()

    const OPERATORS: { value: ComparisonOperator; label: string }[] = [
        { value: ComparisonOperator.CONTAINS, label: 'Contains' },
        { value: ComparisonOperator.EQUALS, label: 'Equals' },
        { value: ComparisonOperator.NUMBER_EQUALS, label: 'Number Equals' },
        { value: ComparisonOperator.GREATER_THAN, label: 'Greater Than' },
        { value: ComparisonOperator.LESS_THAN, label: 'Less Than' },
        { value: ComparisonOperator.STARTS_WITH, label: 'Starts With' },
        { value: ComparisonOperator.NOT_STARTS_WITH, label: 'Does Not Start With' },
        { value: ComparisonOperator.IS_EMPTY, label: 'Is Empty' },
        { value: ComparisonOperator.IS_NOT_EMPTY, label: 'Is Not Empty' },
    ]

    const DEFAULT_CONDITION: RouteConditionRule = {
        variable: '',
        operator: ComparisonOperator.CONTAINS,
        value: '',
    }

    const nodeConfig = $derived(flowStore.nodeConfigs[id])

    const nodeData = $derived({
        title: nodeConfig?.title || 'Conditional Router',
        color: data?.color || '#F6AD55',
        acronym: 'RN',
        run: data?.run,
        config: nodeConfig,
        taskStatus: data?.taskStatus,
    })

    // Predecessor nodes and input variables
    const predecessors = $derived.by(() => {
        const edges = flowStore.edges.filter((e) => e.target === id)
        return edges
            .map((e) => {
                const src = flowStore.nodes.find((n) => n.id === e.source)
                if (!src) return null
                if (src.type === 'RouterNode' && e.sourceHandle) {
                    return { ...src, handle_id: e.sourceHandle }
                }
                return src
            })
            .filter(Boolean)
            .filter((n, i, self) => self.findIndex((x) => x!.id === n!.id) === i)
    })

    const inputVariables = $derived.by(() => {
        return predecessors.flatMap((node) => {
            if (!node) return []
            const predConfig = flowStore.nodeConfigs[node.id]
            const nodeTitle = predConfig?.title || node.id
            let props: Record<string, any> = {}
            try {
                const parsed = predConfig?.output_json_schema ? JSON.parse(predConfig.output_json_schema) : {}
                props = parsed.properties || {}
            } catch {}
            return Object.entries(props).map(([key, val]) => ({
                value: `${nodeTitle}.${key}`,
                label: `${nodeTitle}.${key} (${(val as any).type || 'unknown'})`,
            }))
        })
    })

    // Initialize route_map if empty
    $effect(() => {
        if (!nodeConfig?.route_map || Object.keys(nodeConfig.route_map).length === 0) {
            flowStore.updateNodeConfigOnly(id, {
                ...nodeConfig,
                route_map: { route1: { conditions: [{ variable: '', operator: ComparisonOperator.CONTAINS, value: '' }] } },
            })
        }
    })

    // Update node internals when route_map changes
    $effect(() => {
        if (nodeConfig?.route_map) {
            updateNodeInternals(id)
        }
    })

    function handleUpdateRouteMap(newRouteMap: Record<string, RouteConditionGroup>) {
        flowStore.updateNodeConfigOnly(id, { ...nodeConfig, route_map: newRouteMap })
    }

    function addRoute() {
        const routeNumbers = Object.keys(nodeConfig?.route_map || {})
            .map((k) => parseInt(k.replace('route', '')))
            .filter((n) => !isNaN(n))
        const nextNum = routeNumbers.length > 0 ? Math.max(...routeNumbers) + 1 : 1
        handleUpdateRouteMap({
            ...(nodeConfig?.route_map || {}),
            [`route${nextNum}`]: { conditions: [{ ...DEFAULT_CONDITION }] },
        })
    }

    function removeRoute(routeKey: string) {
        if (!nodeConfig?.route_map) return
        flowStore.deleteEdgeByHandle(id, routeKey)
        const { [routeKey]: _, ...remaining } = nodeConfig.route_map
        handleUpdateRouteMap(remaining)
    }

    function addCondition(routeKey: string) {
        if (!nodeConfig?.route_map) return
        handleUpdateRouteMap({
            ...nodeConfig.route_map,
            [routeKey]: {
                conditions: [
                    ...(nodeConfig.route_map[routeKey].conditions || []),
                    { variable: '', operator: ComparisonOperator.CONTAINS, value: '', logicalOperator: 'AND' as const },
                ],
            },
        })
    }

    function removeCondition(routeKey: string, idx: number) {
        if (!nodeConfig?.route_map) return
        handleUpdateRouteMap({
            ...nodeConfig.route_map,
            [routeKey]: {
                conditions: nodeConfig.route_map[routeKey].conditions.filter((_, i) => i !== idx),
            },
        })
    }

    function updateCondition(routeKey: string, idx: number, field: keyof RouteConditionRule, value: string) {
        if (!nodeConfig?.route_map) return
        handleUpdateRouteMap({
            ...nodeConfig.route_map,
            [routeKey]: {
                conditions: nodeConfig.route_map[routeKey].conditions.map((c, i) =>
                    i === idx ? { ...c, [field]: value } : c
                ),
            },
        })
    }
</script>

<BaseNode
    {id}
    {isCollapsed}
    setIsCollapsed={(v) => (isCollapsed = v)}
    data={nodeData}
    {positionAbsoluteX}
    {positionAbsoluteY}
    style="width: auto; max-height: 1200px; display: flex; flex-direction: column;"
    className="hover:!bg-background"
>
    <div class="flex flex-col flex-grow overflow-hidden">
        {#if !isCollapsed && nodeConfig?.route_map}
            <div
                class="p-5 overflow-y-auto"
                style="touch-action: none;"
                role="presentation"
                onwheelcapture={(e) => e.stopPropagation()}
                onclick={(e) => e.stopPropagation()}
            >
                <!-- Expressions header -->
                <div class="sticky top-0 bg-background/95 backdrop-blur-sm z-10 pb-4">
                    <hr class="my-2 border-border" />
                    <div class="flex items-center gap-2 mb-4">
                        <span class="text-sm font-medium text-foreground">Expressions</span>
                        <hr class="flex-grow border-border" />
                    </div>
                </div>

                <!-- Routes -->
                <div class="flex flex-col gap-4">
                    {#each Object.entries(nodeConfig.route_map) as [routeKey, route]}
                        <div class="border border-border rounded-lg p-3 bg-background">
                            <div class="flex flex-col gap-3">
                                <!-- Route header -->
                                <div class="flex justify-between items-center">
                                    <span class="text-sm font-medium text-foreground">{routeKey}</span>
                                    {#if Object.keys(nodeConfig.route_map).length > 1}
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            class="h-7 w-7 text-destructive hover:text-destructive"
                                            onclick={() => removeRoute(routeKey)}
                                        >
                                            <Icon icon="solar:trash-bin-trash-linear" width={16} />
                                        </Button>
                                    {/if}
                                </div>

                                <!-- Conditions -->
                                {#each route.conditions as condition, conditionIndex}
                                    <div class="flex flex-col gap-2">
                                        {#if conditionIndex > 0}
                                            <!-- AND/OR toggle -->
                                            <div class="flex items-center gap-2 justify-center">
                                                <div class="flex rounded-md border border-border overflow-hidden text-xs">
                                                    <button
                                                        type="button"
                                                        class="px-2 py-1 transition-colors {condition.logicalOperator === 'AND' ? 'bg-primary text-primary-foreground' : 'bg-background hover:bg-muted'}"
                                                        onclick={() => updateCondition(routeKey, conditionIndex, 'logicalOperator', 'AND')}
                                                    >AND</button>
                                                    <button
                                                        type="button"
                                                        class="px-2 py-1 transition-colors {condition.logicalOperator === 'OR' ? 'bg-primary text-primary-foreground' : 'bg-background hover:bg-muted'}"
                                                        onclick={() => updateCondition(routeKey, conditionIndex, 'logicalOperator', 'OR')}
                                                    >OR</button>
                                                </div>
                                            </div>
                                        {/if}

                                        <div class="grid grid-cols-[1fr,auto] gap-2">
                                            <!-- Variable select -->
                                            <select
                                                class="text-sm border border-border rounded-md px-2 py-1 bg-background w-full"
                                                value={condition.variable}
                                                onchange={(e) => updateCondition(routeKey, conditionIndex, 'variable', (e.target as HTMLSelectElement).value)}
                                            >
                                                <option value="">Select variable</option>
                                                {#each inputVariables as variable}
                                                    <option value={variable.value}>{variable.label}</option>
                                                {/each}
                                            </select>

                                            {#if route.conditions.length > 1}
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    class="h-8 w-8 text-destructive hover:text-destructive"
                                                    onclick={() => removeCondition(routeKey, conditionIndex)}
                                                >
                                                    <Icon icon="solar:trash-bin-trash-linear" width={14} />
                                                </Button>
                                            {/if}

                                            <!-- Operator + Value -->
                                            <div class="flex gap-2 col-span-2">
                                                <select
                                                    class="text-sm border border-border rounded-md px-2 py-1 bg-background w-[140px] flex-none"
                                                    value={condition.operator}
                                                    onchange={(e) => updateCondition(routeKey, conditionIndex, 'operator', (e.target as HTMLSelectElement).value)}
                                                >
                                                    {#each OPERATORS as op}
                                                        <option value={op.value}>{op.label}</option>
                                                    {/each}
                                                </select>

                                                {#if !['is_empty', 'is_not_empty'].includes(condition.operator)}
                                                    <Input
                                                        class="text-sm h-8 flex-1"
                                                        placeholder="Value"
                                                        value={condition.value}
                                                        oninput={(e) => updateCondition(routeKey, conditionIndex, 'value', (e.target as HTMLInputElement).value)}
                                                    />
                                                {/if}
                                            </div>
                                        </div>
                                    </div>
                                {/each}

                                <!-- Add Condition -->
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    class="text-foreground justify-start"
                                    onclick={() => addCondition(routeKey)}
                                >
                                    <Icon icon="solar:add-circle-linear" width={16} class="mr-1" />
                                    Add Condition
                                </Button>

                                <!-- Route output handle -->
                                <div class="handle-row w-full flex items-center justify-end mt-2">
                                    <div class="flex flex-grow flex-shrink mr-2 items-center">
                                        <span class="text-sm font-medium ml-auto text-foreground">{routeKey}</span>
                                    </div>
                                    <div class="border-l border-border h-full mx-0"></div>
                                    <div class="flex items-center justify-center w-6 h-6">
                                        <Handle
                                            type="source"
                                            position={Position.Right}
                                            id={routeKey}
                                            class="!w-3 !h-3 !bg-primary/70 !border-2 !border-background"
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>
                    {/each}

                    <!-- Add Route -->
                    <Button
                        variant="ghost"
                        size="sm"
                        class="text-foreground justify-start"
                        onclick={addRoute}
                    >
                        <Icon icon="solar:add-circle-linear" width={16} class="mr-1" />
                        Add Route
                    </Button>
                </div>
            </div>
        {/if}

        <!-- Collapsed handles -->
        {#if isCollapsed && nodeConfig?.route_map}
            {#each Object.keys(nodeConfig.route_map) as routeKey}
                <div class="handle-row w-full flex items-center justify-end mt-2">
                    <div class="flex items-center justify-center w-6 h-6">
                        <Handle
                            type="source"
                            position={Position.Right}
                            id={routeKey}
                            class="!w-3 !h-3 !bg-primary/70 !border-2 !border-background !opacity-50"
                        />
                    </div>
                </div>
            {/each}
        {/if}
    </div>
</BaseNode>

<style>
    .handle-row {
        min-height: 32px;
        position: relative;
    }
</style>
