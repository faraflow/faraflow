# Copyright 2026 Alokin LLC
# SPDX-License-Identifier: FCL-1.0-ALv2
import logging
import os
from typing import Any, Dict

import httpx
from pydantic import BaseModel, Field

from ...base import BaseNode, BaseNodeConfig, BaseNodeInput, BaseNodeOutput
from ...utils.template_utils import render_template_or_get_first_string

logger = logging.getLogger(__name__)

SERPER_BASE_URL = "https://google.serper.dev"


async def serper_request(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """POST a query to a Serper endpoint (for example "maps" or "search") and return the JSON."""
    # Read the key on every call so a key added under Settings > API Keys works without a restart.
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        raise ValueError("SERPER_API_KEY is not set. Add it under Settings > API Keys.")

    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f"{SERPER_BASE_URL}/{endpoint}", headers=headers, json=payload)

    if response.status_code != 200:
        raise ValueError(f"Serper {endpoint} request failed ({response.status_code}): {response.text[:300]}")
    return response.json()


class SerperNodeConfig(BaseNodeConfig):
    query_template: str = Field(
        "search for {{input_node.query}}",
        description=(
            "The query for the search. Use {{node_title.field}} to insert a value from an "
            "upstream node."
        ),
    )
    hl: str = Field(
        "en",
        description="The language code for the search results",
    )


class SerperNodeInput(BaseNodeInput):
    pass


class SerperNodeOutput(BaseNodeOutput):
    title: str = "Serper"
    results: dict = Field(default_factory=dict, description="Serper results")


class SerperNode(BaseNode):
    """Google Maps search through Serper (places near a location)."""

    name = "serper_node"
    display_name = "Serper Google Maps Search"
    logo = "/images/serper.png"
    category = "Serper"

    config_model = SerperNodeConfig
    input_model = SerperNodeInput
    output_model = SerperNodeOutput

    async def run(self, input: BaseModel) -> BaseModel:
        query = render_template_or_get_first_string(
            self.config.query_template, input.model_dump(), self.name
        )
        results = await serper_request("maps", {"q": query, "hl": self.config.hl})
        return SerperNodeOutput(title=query, results=results)


class SerperSearchNodeConfig(SerperNodeConfig):
    num: int = Field(10, ge=1, le=100, description="The number of results to return")


class SerperSearchNode(BaseNode):
    """Regular Google web search through Serper."""

    name = "serper_search_node"
    display_name = "Serper Google Search"
    logo = "/images/serper.png"
    category = "Serper"

    config_model = SerperSearchNodeConfig
    input_model = SerperNodeInput
    output_model = SerperNodeOutput

    async def run(self, input: BaseModel) -> BaseModel:
        query = render_template_or_get_first_string(
            self.config.query_template, input.model_dump(), self.name
        )
        payload: Dict[str, Any] = {"q": query, "hl": self.config.hl, "num": self.config.num}
        results = await serper_request("search", payload)
        return SerperNodeOutput(title=query, results=results)
