# Copyright 2026 Alokin LLC
# SPDX-License-Identifier: FCL-1.0-ALv2
import json
import httpx
import logging
from pydantic import BaseModel, Field  # type: ignore
from ...base import BaseNode, BaseNodeConfig, BaseNodeInput, BaseNodeOutput
from typing import Optional
from ...utils.template_utils import render_template_or_get_first_string
from .http_config import CRAWL_USER_AGENT


class URLScrapingNodeConfig(BaseNodeConfig):
    url_template: str = Field(
        "",
        description="The URL to crawl and process.",
    )
    has_fixed_output: bool = False



class URLScrapingNodeInput(BaseNodeInput):
    pass


class URLScrapingNodeOutput(BaseNodeOutput):
    crawl_result: str = Field(
        ..., description="The crawled data in markdown or structured format."
    )


class URLScrapingNode(BaseNode):
    name = "url_scraping_node"
    display_name = "URL Scraping"
    logo = "/images/web.svg"
    category = "Web"

    config_model = URLScrapingNodeConfig
    input_model = URLScrapingNodeInput
    output_model = URLScrapingNodeOutput

    async def _request(self, method, url,
                       headers=None, params=None, data=None):
        # Present our standard crawl User-Agent so sites that block the default
        # httpx UA still serve us (caller-supplied headers win on conflict).
        headers = {"User-Agent": CRAWL_USER_AGENT, **(headers or {})}
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.request(
                        method,
                        url,
                        headers=headers,
                        data=data,
                        params=params
                        # httpx automatically sets Content-Type and serializes JSON
                )
                response.raise_for_status()
                return response
        except httpx.HTTPError as e:
            print(f"Error during the request: {e}")
            return None

    async def run(self, input: BaseModel) -> BaseModel:
        try:
            # Grab the entire dictionary from the input
            raw_input_dict = input.model_dump()

            # Render url_template
            url_template = render_template_or_get_first_string(
                self.config.url_template, raw_input_dict, self.name
            )


            self._request_url = url_template
            response = await self._request(**self.get_request_data(url_template))
            return await self.process_response(response)
        except Exception as e:
            logging.debug(f"Failed to crawl URL: {e}")
            return None

    def request_url(self):
        return self._request_url

    async def process_response(self, response) -> BaseModel:
        return URLScrapingNodeOutput(crawl_result=response.json())
