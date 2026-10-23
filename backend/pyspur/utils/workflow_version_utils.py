# Originally from PySpur (https://github.com/PySpur-Dev/pyspur), licensed under Apache-2.0.
# Modified by Alokin LLC, 2026; modifications licensed under FCL-1.0-ALv2.
# SPDX-License-Identifier: Apache-2.0 AND FCL-1.0-ALv2
import hashlib
import json
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from ..models.workflow_version_model import WorkflowVersionModel
from ..nodes.primitives.input import InputNodeConfig
from ..schemas.workflow_schemas import (
    WorkflowDefinitionSchema,
    WorkflowResponseSchema,
)


def extract_model_version(definition: Optional[Dict[str, Any]]) -> str:
    """Return the model_version declared on the workflow's input node.

    The version lives on the top-level InputNode's config. Falls back to the
    InputNodeConfig default when the workflow definition does not declare one.
    """
    default = InputNodeConfig.model_fields["model_version"].default
    if not definition:
        return default
    for node in definition.get("nodes", []):
        if node.get("node_type") == "InputNode" and node.get("parent_id") is None:
            return node.get("config", {}).get("model_version") or default
    return default


def get_latest_workflow_version(workflow_id: str, db: Session) -> int:
    """
    Retrieve the latest version number of a workflow.
    Returns the latest version number if it exists, otherwise 0.
    """
    latest_version = (
        db.query(WorkflowVersionModel)
        .filter(WorkflowVersionModel.workflow_id == workflow_id)
        .order_by(WorkflowVersionModel.version.desc())
        .first()
    )

    return latest_version.version if latest_version else 0


def hash_workflow_definition(definition: WorkflowDefinitionSchema) -> str:
    """
    Create a hash of the workflow definition for comparison.
    """
    definition_str = json.dumps(definition, sort_keys=True)
    return hashlib.sha256(definition_str.encode("utf-8")).hexdigest()


def fetch_workflow_version(
    workflow_id: str, workflow: WorkflowResponseSchema, db: Session
) -> WorkflowVersionModel:
    """
    Retrieve an existing workflow version with the same definition or create a new one.
    """
    definition_hash = hash_workflow_definition(workflow.definition)
    existing_version = (
        db.query(WorkflowVersionModel)
        .filter(
            WorkflowVersionModel.workflow_id == workflow_id,
            WorkflowVersionModel.definition_hash == definition_hash,
        )
        .first()
    )

    if existing_version:
        return existing_version

    latest_version_number = get_latest_workflow_version(workflow_id, db)
    new_version = WorkflowVersionModel(
        workflow_id=workflow_id,
        version=latest_version_number + 1,
        name=workflow.name,
        description=workflow.description,
        definition=workflow.definition,
        definition_hash=definition_hash,
    )
    db.add(new_version)
    db.commit()
    return new_version
