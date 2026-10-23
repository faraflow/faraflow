# Originally from PySpur (https://github.com/PySpur-Dev/pyspur), licensed under Apache-2.0.
# Modified by Alokin LLC, 2026; modifications licensed under FCL-1.0-ALv2.
# SPDX-License-Identifier: Apache-2.0 AND FCL-1.0-ALv2
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.run_model import RunModel, RunStatus
from ..models.task_model import TaskStatus
from ..schemas.run_schemas import RunListItemSchema, RunResponseSchema, RunStatusSchema

router = APIRouter()


@router.get(
    "/",
    response_model=List[RunListItemSchema],
    description="List all runs",
)
def list_runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    parent_only: bool = True,
    run_type: Optional[str] = None,
    status: Optional[RunStatus] = Query(default=None, description="Filter runs by status"),
    input_query: Optional[str] = Query(default=None, description="Filter runs by input values (text search)"),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * page_size
    query = db.query(RunModel)

    if parent_only:
        query = query.filter(RunModel.parent_run_id.is_(None))
    if run_type:
        query = query.filter(RunModel.run_type == run_type)
    if status:
        query = query.filter(RunModel.status == status)
    if input_query:
        from sqlalchemy import String, cast
        query = query.filter(cast(RunModel.initial_inputs, String).ilike(f'%{input_query}%'))

    runs = query.order_by(RunModel.start_time.desc()).offset(offset).limit(page_size).all()
    return runs


@router.get("/{run_id}/", response_model=RunResponseSchema)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(RunModel).filter(RunModel.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get(
    "/{run_id}/status/light/",
    response_model=RunStatusSchema,
    description="Lightweight run status heartbeat (no tasks). Poll this to detect "
    "changes via `version` before fetching the full run.",
)
def get_run_status_light(run_id: str, db: Session = Depends(get_db)):
    run = db.query(RunModel).filter(RunModel.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/{run_id}/status/", response_model=RunResponseSchema)
def get_run_status(run_id: str, db: Session = Depends(get_db)):
    run = db.query(RunModel).filter(RunModel.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status == RunStatus.RUNNING:
        failed_tasks = [task for task in run.tasks if task.status == TaskStatus.FAILED]
        running_and_pending_tasks = [
            task for task in run.tasks if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]
        ]
        if len(running_and_pending_tasks) == 0:
            if failed_tasks:
                run.status = RunStatus.FAILED
            else:
                run.status = RunStatus.COMPLETED
                if run.end_time is None:
                    from datetime import datetime, timezone
                    run.end_time = datetime.now(timezone.utc)
            db.commit()
            db.refresh(run)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run
