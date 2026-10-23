<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
# Runs & Trace Page

## Backend API

Runs are managed in `backend/pyspur/api/run_management.py`, registered with prefix `/run`:

| Endpoint | Description |
|----------|-------------|
| `GET /api/run/` | List all runs (paginated, parent-only by default) |
| `GET /api/run/{run_id}/` | Get a specific run |
| `GET /api/run/{run_id}/status/` | Get run status (also updates status if all tasks failed) |

Run IDs like `R3` are string identifiers stored in `RunModel.id`.

The frontend utility is `getRunStatus(runId)` in `src/lib/utils/api.ts`, which calls `GET /api/run/{run_id}/status/`.

## Trace Page (`/trace/[id]`)

Located at `frontend/src/routes/trace/[id]/+page.svelte`.

### Data flow

1. On mount: fetch node types, then fetch run via `getRunStatus(runId)`
2. Run response includes `workflow_version.definition` (the workflow graph) and `tasks` (execution results per node)
3. `rolloutWorkflowDefinition` expands any subworkflow nodes in-place (AgentNode, etc.) using task data
4. The resulting `workflowData` and `tasksData` are passed to `TraceCanvas`
5. `TraceCanvas` calls `flowStore.initializeFlow` to build the canvas, then `flowStore.updateNodeDataOnly` per task to apply run status/outputs

### Known bugs fixed

- **`bind:edges` in TraceCanvas** (same root cause as EditorCanvas): was passing raw `flowStore.edges` (no `type: 'custom'`) instead of `styledEdges`. Fixed to `edges={styledEdges}`.
- **Hardcoded `isDark: false`** in `getStyledEdges` call — was ignoring dark mode. Fixed to use reactive `isDark` derived from `mode-watcher`.
- **Silent spinner on missing definition**: if the run has no `workflow_version.definition`, the page showed a spinner forever with no feedback. Now shows an error message.

### Why the canvas might appear empty

If `flowStore.initializeFlow` creates no nodes, the canvas renders but shows nothing. This happens when:

- `createNode` returns `null` for every node type in the definition — occurs when `nodeTypesStore.data` doesn't contain the node type (e.g., backend is missing a plugin, or the node type name differs)
- The workflow definition itself has an empty `nodes` array

To debug: open the browser console and look for errors after navigating to `/trace/{run_id}`. The `createNode` function logs no errors; add a `console.warn` on the `if (!result) continue` line in `flow.svelte.ts:initializeFlow` to surface missing node types.

### Task status coloring

`TraceCanvas` applies task statuses (PENDING / COMPLETED / FAILED / PAUSED) to nodes via `flowStore.updateNodeDataOnly`. Node components read `node.data.taskStatus` to apply visual styling (e.g., green border for COMPLETED, red for FAILED).
