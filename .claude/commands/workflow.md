---
description: Reference guide for reading, updating, and working with Faraflow workflows — data structures, API endpoints, frontend store, and execution flow. Use this when modifying workflow behavior, adding/removing nodes, tracing execution bugs, or understanding the workflow lifecycle.
allowed-tools: [Read, Glob, Grep, Bash]
---
<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->

# Faraflow Workflow Reference

## Data Structures

### Backend (Pydantic) — `backend/pyspur/schemas/workflow_schemas.py`

```
WorkflowDefinitionSchema
  nodes: List[WorkflowNodeSchema]
  links: List[WorkflowLinkSchema]
  test_inputs: List[Dict]
  spur_type: SpurType  # WORKFLOW | CHATBOT | AGENT

WorkflowNodeSchema
  id: str                        # unique node ID
  title: str                     # display name
  node_type: str                 # e.g. "InputNode", "LLMNode", "RouterNode"
  config: Dict[str, Any]         # matches the node's config_model fields
  coordinates: {x, y}           # canvas position
  dimensions: {width, height}
  parent_id: Optional[str]       # set for subworkflow child nodes
  subworkflow: Optional[WorkflowDefinitionSchema]  # nested workflow

WorkflowLinkSchema
  source_id: str
  target_id: str
  source_handle: Optional[str]   # RouterNode branches: "{source_id}.{branch_id}"
  target_handle: Optional[str]
```

### DB Models — `backend/pyspur/models/`

- `workflow_model.py` — `WorkflowModel`: `id` (prefix 'S'), `name`, `description`, `definition` (JSON), timestamps
- `workflow_version_model.py` — `WorkflowVersionModel`: `id`, `version`, `workflow_id`, `definition` (JSON), `definition_hash`
- `run_model.py` — `RunModel`: `id` (prefix 'R'), `workflow_id`, `workflow_version_id`, `status`, `initial_inputs`, `outputs`, `start_time`, `end_time`
- `task_model.py` — `TaskModel`: `id` (prefix 'T'), `run_id`, `node_id`, `status`, `inputs`, `outputs`, `error`, `subworkflow_output`

**RunStatus / TaskStatus enum**: `PENDING → RUNNING → COMPLETED | FAILED | PAUSED | CANCELED`

### Frontend TypeScript — `frontend/src/lib/types/api_types/`

- `workflowSchemas.ts` — `WorkflowDefinition`, `WorkflowNode`, `WorkflowLink`
- `runSchemas.ts` — `RunResponse`, `RunStatus`, `StartRunRequest`, `PartialRunRequest`
- `taskSchemas.ts` — `TaskResponse`, `TaskStatus`

---

## Reading a Workflow

### Via API
```
GET /api/workflows/                    # list (paginated)
GET /api/workflows/{workflow_id}/      # single workflow → WorkflowResponseSchema
GET /api/workflows/{workflow_id}/versions/  # version history
GET /api/runs/{run_id}/               # run with all task details
```

### Via Backend Code
```python
# In a FastAPI route/service with a db session:
from pyspur.models.workflow_model import WorkflowModel
wf = db.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
definition = wf.definition  # dict matching WorkflowDefinitionSchema
```

### Via Frontend Store — `frontend/src/lib/stores/flow.svelte.ts`
```typescript
import { flowStore } from '$lib/stores/flow.svelte';

flowStore.nodes          // FlowWorkflowNode[] — visual nodes (@xyflow)
flowStore.edges          // FlowWorkflowEdge[]
flowStore.nodeConfigs    // Record<nodeId, config> — node configuration
flowStore.workflowID     // current workflow ID
flowStore.spurType       // SpurType
```

---

## Updating a Workflow

### Backend: change definition in DB
```python
# Edit the definition dict and save:
wf.definition = updated_definition_dict
db.commit()
```

### Via API
```
PUT /api/workflows/{workflow_id}/      # body: WorkflowCreateRequest
  { name, description, definition: WorkflowDefinitionSchema }
```

### Via Frontend Store (preferred for UI changes)
```typescript
// Add a node
flowStore.addNode(newNode);

// Delete a node
flowStore.deleteNode(nodeId);

// Connect two nodes
flowStore.connect({ source, target, sourceHandle?, targetHandle? });

// Update node config only (do NOT mutate nodeConfigs directly)
flowStore.updateNodeConfigOnly(nodeId, { ...newConfigFields });

// Update node visual data only
flowStore.updateNodeDataOnly(nodeId, { ...newData });

// Persist to backend (debounced 1s)
import { saveWorkflow, saveWorkflowNow } from '$lib/actions/saveWorkflow.svelte';
saveWorkflow();      // debounced
saveWorkflowNow();   // immediate, returns Promise
```

---

## Execution Flow

### Starting a Run
```
POST /api/workflows/{id}/runv2/
  body: StartRunRequestSchema { initial_inputs, parent_run_id?, files? }
  returns: RunResponseSchema

POST /api/workflows/{id}/partial_run/   # rerun from a specific node
  body: PartialRunRequestSchema { node_id, partial_outputs, rerun_predecessors }
```

### Execution Internals — `backend/pyspur/execution/workflow_executor.py`
1. `WorkflowExecutor.__call__(initial_inputs)` builds DAG from `links`
2. Nodes execute asynchronously; dependencies resolved from DAG
3. Each node: `TaskRecorder.create_task(node_id)` → `NodeFactory.create_node()` → `node(inputs)` → `TaskRecorder.update_task()`
4. `HumanInterventionNode` raises `PauseError` → run marked `PAUSED`

### Resume a Paused Run
```
POST /api/workflows/{run_id}/process_pause_action/
  body: ResumeRunRequestSchema { inputs, user_id, action, comments }
```

### Frontend Polling — `frontend/src/lib/actions/workflowExecution.svelte.ts`
```typescript
import { executionState, startRun, updateWorkflowStatus } from '$lib/actions/workflowExecution.svelte';

executionState.isRunning          // boolean
executionState.currentRunId       // string | null
executionState.workflowRuns       // RunResponse[]
executionState.completionPercentage

startRun(workflowId, initialInputs)  // kicks off run + starts 1s polling
```
Frontend polls `GET /runs/{runId}/` every 1s, applies task outputs to nodes via `applyTasksToNodes`.

---

## Node System

### Node Files — `backend/pyspur/nodes/`
Each node type is a single `.py` file. No registration needed — the factory auto-discovers them.

### Key Classes — `backend/pyspur/nodes/base.py`
```python
class BaseNode:
    config_model: Type[BaseNodeConfig]   # Pydantic config schema
    output_model: Type[BaseNodeOutput]   # Pydantic output schema
    input_model: Type[BaseNodeInput]     # Pydantic input schema (dynamic)

    async def run(self, input: BaseNodeInput) -> BaseNodeOutput: ...  # implement this
```

### Creating a Node Instance
```python
from pyspur.nodes.factory import NodeFactory
node = NodeFactory.create_node(
    node_name="my_node",
    node_type_name="LLMNode",
    config={"llm_info": {...}, "output_schema": {...}}
)
result = await node(input_data)
```

### Config Fields (common)
```python
output_schema: Dict[str, str]      # field_name → type_string
output_json_schema: str            # JSON Schema string
has_fixed_output: bool
```

---

## Common Patterns

**Add a node to a workflow definition:**
```python
definition["nodes"].append({
    "id": "new_node_1",
    "title": "My Node",
    "node_type": "LLMNode",
    "config": { "llm_info": {...}, "output_schema": {"result": "str"} },
    "coordinates": {"x": 400, "y": 200}
})
definition["links"].append({
    "source_id": "input_node",
    "target_id": "new_node_1"
})
```

**Find a node's output schema:**
```python
node_config = node["config"]
output_schema = node_config.get("output_schema")       # Dict[str, str]
output_json_schema = node_config.get("output_json_schema")  # JSON string
```

**Subworkflow nodes:**
The node's `subworkflow` field contains a full nested `WorkflowDefinitionSchema`. Child nodes have `parent_id` set to the subworkflow node's ID.

**RouterNode links:**
`source_handle` format: `"{source_node_id}.{branch_id}"` — needed to distinguish branches.

**Version history:**
Each unique workflow definition (by hash) gets a `WorkflowVersionModel`. All runs reference `workflow_version_id` for reproducibility.

---

## Key File Index

| What | Where |
|------|-------|
| Workflow Pydantic schemas | `backend/pyspur/schemas/workflow_schemas.py` |
| WorkflowModel ORM | `backend/pyspur/models/workflow_model.py` |
| Run/Task ORM models | `backend/pyspur/models/run_model.py`, `task_model.py` |
| Workflow CRUD API | `backend/pyspur/api/workflow_management.py` |
| Execution API | `backend/pyspur/api/workflow_run.py` |
| Async DAG executor | `backend/pyspur/execution/workflow_executor.py` |
| Task persistence | `backend/pyspur/execution/task_recorder.py` |
| Node base class | `backend/pyspur/nodes/base.py` |
| Node factory | `backend/pyspur/nodes/factory.py` |
| Frontend store | `frontend/src/lib/stores/flow.svelte.ts` |
| Frontend execution | `frontend/src/lib/actions/workflowExecution.svelte.ts` |
| Frontend save | `frontend/src/lib/actions/saveWorkflow.svelte.ts` |
| TS workflow types | `frontend/src/lib/types/api_types/workflowSchemas.ts` |
| TS run types | `frontend/src/lib/types/api_types/runSchemas.ts` |
