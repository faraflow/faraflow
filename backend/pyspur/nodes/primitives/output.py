# Originally from PySpur (https://github.com/PySpur-Dev/pyspur), licensed under Apache-2.0.
# Modified by Alokin LLC, 2026; modifications licensed under FCL-1.0-ALv2.
# SPDX-License-Identifier: Apache-2.0 AND FCL-1.0-ALv2
from typing import Any, Dict

from pydantic import BaseModel, Field, create_model

from ...utils.pydantic_utils import get_nested_field
from ..base import (
    BaseNode,
    BaseNodeConfig,
    BaseNodeInput,
    BaseNodeOutput,
)


class OutputNodeConfig(BaseNodeConfig):
    """
    Configuration for the OutputNode, focusing on mapping from input fields
    (possibly nested via dot notation) to output fields.
    """

    output_map: Dict[str, str] = Field(
        default_factory=dict,
        title="Output Map",
        description="A dictionary mapping input field names (dot-notation allowed) to output field names.",
    )


class OutputNode(BaseNode):
    """
    Node for defining a typed output schema automatically by inferring it
    from the output_map. If output_map is empty, it will simply pass the
    entire input through unmodified.
    """

    name = "output_node"
    display_name = "Output"
    config_model = OutputNodeConfig
    input_model = BaseNodeInput
    output_model = BaseNodeOutput

    async def run(self, input: BaseModel) -> BaseModel:
        """
        Maps the incoming input fields (possibly nested) to the node's output
        fields according to self.config.output_map. If no output_map is set,
        returns the entire input as output.

        Args:
            input (BaseModel): The input model (from predecessor nodes).

        Returns:
            BaseModel: The node's typed output model instance.
        """
        if self.config.output_map:
            # If user provided mappings, create a new model with the mapped fields
            model_fields: Dict[str, Any] = {}
            for output_key, input_key in self.config.output_map.items():
                model_fields[output_key] = (
                    type(get_nested_field(field_name_with_dots=input_key, model=input)),
                    ...,
                )
            self.output_model = create_model(
                f"{self.name}",
                **model_fields,
                __base__=BaseNodeOutput,
                __config__=None,
                __module__=self.__module__,
            )
            output_dict: Dict[str, Any] = {
                output_key: get_nested_field(input_key, input)
                for output_key, input_key in self.config.output_map.items()
            }
        else:
            # No output_map — pass all inputs through as-is
            output_dict = input.model_dump()
            model_fields = {k: (type(v), ...) for k, v in output_dict.items()}
            self.output_model = create_model(
                f"{self.name}",
                **model_fields,
                __base__=BaseNodeOutput,
                __config__=None,
                __module__=self.__module__,
            )

        return self.output_model(**output_dict)
