# Copyright 2026 Alokin LLC
# SPDX-License-Identifier: FCL-1.0-ALv2
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, create_model

from ..base import BaseNodeInput, BaseNodeOutput
from ...schemas.workflow_schemas import (
    WorkflowDefinitionSchema,
    WorkflowLinkSchema,
    WorkflowNodeSchema,
)
from ..registry import NodeRegistry
from ..subworkflow.base_subworkflow_node import (
    BaseSubworkflowNode,
    BaseSubworkflowNodeConfig,
)
from ._utils import ModelInfo


def _field_name(prefix: str, model: ModelInfo) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", model.model.split("/")[-1].lower()).strip("_")
    return f"{prefix}_{slug}"


def _drop_input_map(schema: dict) -> None:
    schema.get("properties", {}).pop("input_map", None)
    if "required" in schema:
        schema["required"] = [k for k in schema["required"] if k != "input_map"]


class AskNodeConfig(BaseSubworkflowNodeConfig):
    # input_map is not exposed: all upstream outputs are available in Jinja templates by node title.
    model_config = ConfigDict(json_schema_extra=_drop_input_map)

    models: List[ModelInfo] = Field(
        default_factory=list,
        description="List of LLM models to query in parallel",
    )
    output_key_prefix: str = Field(
        default="ask",
        description="Prefix for output field names (e.g. 'search_visibility' → 'search_visibility_gpt_4o')",
    )
    system_message: str = Field(
        default="You are a helpful assistant.",
        description="System message shared by all models",
    )
    user_message: str = Field(
        default="",
        description="User message template (Jinja2); all input fields are available as variables",
    )
    output_json_schema: Optional[str] = Field(
        default=None,
        description="JSON schema string shared by all models for structured output",
    )


class AskNodeInput(BaseNodeInput):
    pass


class AskNodeOutput(BaseNodeOutput):
    pass


@NodeRegistry.register(category="AI", display_name="Ask Multiple LLMs")
class AskNode(BaseSubworkflowNode):
    name = "AskNode"
    display_name = "Ask Multiple LLMs"
    config_model = AskNodeConfig
    workflow: WorkflowDefinitionSchema

    input_model = AskNodeInput
    output_model = AskNodeOutput

    def setup_subworkflow(self) -> None:
        nodes: list[WorkflowNodeSchema] = []
        links: list[WorkflowLinkSchema] = []

        input_node_id = "ask_input_node"
        input_node = WorkflowNodeSchema(
            id=input_node_id,
            title=input_node_id,
            node_type="InputNode",
            config={"enforce_schema": False},
        )
        nodes.append(input_node)

        llm_node_ids: list[str] = []
        for model_info in self.config.models:
            field_id = _field_name(self.config.output_key_prefix, model_info)
            llm_node = WorkflowNodeSchema(
                id=field_id,
                title=field_id,
                node_type="SingleLLMCallNode",
                config={
                    "llm_info": model_info.model_dump(),
                    "system_message": self.config.system_message,
                    "user_message": self.config.user_message,
                    "output_json_schema": self.config.output_json_schema,
                },
            )
            nodes.append(llm_node)
            llm_node_ids.append(field_id)
            links.append(WorkflowLinkSchema(source_id=input_node_id, target_id=field_id))

        output_node_id = "ask_output_node"
        output_node = WorkflowNodeSchema(
            id=output_node_id,
            title=output_node_id,
            node_type="OutputNode",
            config={"output_map": {}},
        )
        nodes.append(output_node)
        for llm_node_id in llm_node_ids:
            links.append(WorkflowLinkSchema(source_id=llm_node_id, target_id=output_node_id))

        self.subworkflow = WorkflowDefinitionSchema(nodes=nodes, links=links)
        super().setup_subworkflow()

    def setup(self) -> None:
        super().setup()

    async def run(self, input: BaseModel) -> BaseModel:
        """Run the subworkflow and return the merged outputs of all successful LLM sub-nodes."""
        try:
            await super().run(input)
        except RuntimeError:
            pass  # output_node unreachable — collect whatever sub-nodes completed below

        prefix = self.config.output_key_prefix
        expected_ids = {_field_name(prefix, m) for m in self.config.models}
        succeeded: Dict[str, Any] = {
            k: v
            for k, v in (self.subworkflow_output or {}).items()
            if k in expected_ids
        }

        if not succeeded:
            raise RuntimeError(
                f"AskNode '{self.config.output_key_prefix}': all LLM sub-nodes failed."
            )

        merged: Dict[str, Any] = {
            k: v.model_dump() if hasattr(v, "model_dump") else v
            for k, v in succeeded.items()
        }
        output_model = create_model(
            "AskNodeOutput",
            **{k: (type(v), ...) for k, v in merged.items()},
            __base__=AskNodeOutput,
        )
        # Update so BaseNode.__call__ validates against the correct schema
        self.output_model = output_model
        return output_model(**merged)
