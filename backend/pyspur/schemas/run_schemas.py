# Originally from PySpur (https://github.com/PySpur-Dev/pyspur), licensed under Apache-2.0.
# Modified by Alokin LLC, 2026; modifications licensed under FCL-1.0-ALv2.
# SPDX-License-Identifier: Apache-2.0 AND FCL-1.0-ALv2
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, computed_field

from ..models.run_model import RunStatus
from ..nodes.logic.human_intervention import PauseAction
from .task_schemas import TaskResponseSchema, TaskStatus
from .workflow_schemas import WorkflowVersionResponseSchema


class StartRunRequestSchema(BaseModel):
    initial_inputs: Optional[Dict[str, Dict[str, Any]]] = None
    # Lineage only — records which run this one was created from (rerun / batch
    # grouping). Carries NO caching or continue semantics; to continue a run,
    # use /run_partial/ with original_run_id instead.
    parent_run_id: Optional[str] = None
    files: Optional[Dict[str, List[str]]] = None  # Maps node_id to list of file paths


class RunResponseSchema(BaseModel):
    id: str
    workflow_id: str
    workflow_version_id: Optional[str] = None
    workflow_version: Optional[WorkflowVersionResponseSchema] = None
    status: RunStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    initial_inputs: Optional[Dict[str, Dict[str, Any]]] = None
    outputs: Optional[Dict[str, Dict[str, Any]]] = None
    model_version: Optional[str] = None
    tasks: List[TaskResponseSchema] = []
    parent_run_id: Optional[str] = None
    run_type: str = "interactive"
    output_file_id: Optional[str] = None
    input_dataset_id: Optional[str] = None
    message: Optional[str] = None  # Add message field for additional info

    @computed_field
    def duration(self) -> Optional[float]:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            now = datetime.now(self.start_time.tzinfo)
            return (now - self.start_time).total_seconds()
        return None

    @computed_field(return_type=float)
    def percentage_complete(self):
        if not self.tasks:
            return 0
        completed_tasks = sum(1 for task in self.tasks if task.status == TaskStatus.COMPLETED)
        return completed_tasks / len(self.tasks) * 100

    class Config:
        from_attributes = True


class RunStatusSchema(BaseModel):
    """Lightweight heartbeat for frequent status polling.

    Pure single-row read — references no `tasks`, so serialization triggers zero
    task queries. `version` is a monotonic change token; pollers compare it to
    decide whether to fetch the full run.
    """

    id: str
    status: RunStatus
    version: int
    start_time: datetime
    end_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class RunListItemSchema(BaseModel):
    """Lightweight run row for list endpoints — no tasks/outputs/workflow_version.

    Carries only what the Runs panels actually display.
    """

    id: str
    workflow_id: Optional[str] = None
    status: RunStatus
    version: int
    run_type: str = "interactive"
    start_time: datetime
    end_time: Optional[datetime] = None
    initial_inputs: Optional[Dict[str, Dict[str, Any]]] = None
    parent_run_id: Optional[str] = None

    class Config:
        from_attributes = True


class PartialRunRequestSchema(BaseModel):
    node_ids: Optional[List[str]] = None  # explicit list; empty/null + original_run_id = auto-detect failures
    initial_inputs: Optional[Dict[str, Dict[str, Any]]] = None
    partial_outputs: Optional[Dict[str, Dict[str, Any] | List[Dict[str, Any]]]] = None
    original_run_id: Optional[str] = None  # if set with no node_ids, auto-continues from all failed nodes
    # With original_run_id: re-run this node and all its descendants, reusing the
    # original run's COMPLETED outputs for every node outside that subtree.
    continue_from_node_id: Optional[str] = None


class ResumeRunRequestSchema(BaseModel):
    """Schema for resuming a paused workflow run."""

    inputs: Dict[str, Any]  # Human-provided inputs for the paused node
    user_id: str  # ID of the user resuming the workflow
    action: PauseAction  # Action taken (APPROVE/DECLINE/OVERRIDE)
    comments: Optional[str] = None  # Optional comments about the decision


class BatchRunRequestSchema(BaseModel):
    dataset_id: str
    mini_batch_size: int = 10
