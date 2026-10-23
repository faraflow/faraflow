# Copyright 2026 Alokin LLC
# SPDX-License-Identifier: FCL-1.0-ALv2
import asyncio
import json
import httpx
import logging
import extruct
from bs4 import BeautifulSoup
# from playwright.async_api import async_playwright
from typing_extensions import Dict
from pydantic import BaseModel, Field  # type: ignore
from ...utils.template_utils import render_template_or_get_first_string
from ...base import BaseNode, BaseNodeConfig, BaseNodeInput, BaseNodeOutput
from .http_config import CRAWL_USER_AGENT

from w3lib.html import get_base_url



logger = logging.getLogger(__name__)



class MetaScrapingNodeInput(BaseNodeInput):
    pass


class MetaScrapingNodeOutput(BaseNodeOutput):
    title: str = "Metadata"
    content: dict = Field(default_factory=dict, description="Metadata")
    status_code: int = Field(0, description="HTTP status of the homepage fetch (0 = request failed)")

class MetaScrapingNodeConfig(BaseNodeConfig):
    url_template: str = Field(
        "",
        description="The URL to crawl and process.",
    )
    # has_fixed_output: bool = True
    # output_json_schema: str = Field(
    #     default=json.dumps(MetaScrapingNodeOutput.model_json_schema()),
    #     description="The JSON schema for the output of the node",
    # )

class MetaDataScraper(BaseNode):
    name = "meta_scraping_node"
    display_name = "Metadata Scraper"
    logo = "/images/web.svg"
    category = "Web"

    config_model = MetaScrapingNodeConfig
    input_model = MetaScrapingNodeInput
    output_model = MetaScrapingNodeOutput

    async def run(self, input: BaseModel) -> BaseModel:

        try:

            # Grab the entire dictionary from the input
            raw_input_dict = input.model_dump()

            # Render url_template
            url = render_template_or_get_first_string(
                self.config.url_template, raw_input_dict, self.name
            )

            logger.debug(f"Scraping URL: {url}")
            response = await self._request(url)
            return await self.process_response(response)
        except Exception as e:
            logger.error(f"Failed to crawl URL: {e}")
            raise e
            return MetaScrapingNodeOutput(crawl_result="")

    async def process_response(self, response) -> BaseModel:
        # A failed/blocked fetch still produces a usable result: empty content
        # plus a status code (0 when the request itself failed). This makes the
        # node the homepage crawlability probe without aborting the run.
        if response is None:
            return MetaScrapingNodeOutput(content={}, status_code=0)
        try:
            base_url = get_base_url(response.text, str(response.url))
            data = extruct.extract(response.text, base_url=base_url)
        except Exception as e:
            # A blocked/error page may not parse — still surface the status so the
            # crawlability verdict can run instead of crashing the workflow.
            logger.error(f"extruct failed for {response.url}: {e}")
            data = {}
        return MetaScrapingNodeOutput(content=data, status_code=response.status_code)

    async def _request(self, url: str):
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                # Do NOT raise_for_status — we want the body + status of a 403,
                # not an exception, so crawlability can be judged downstream.
                return await client.get(url, headers={"User-Agent": CRAWL_USER_AGENT})
        except httpx.HTTPError as e:
            logger.error(f"Homepage fetch failed for {url}: {e}")
            return None

    def _extract_metadata(self, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        return self._parse_head(soup)

    def _parse_head(self, soup: BeautifulSoup) -> dict:
        head = soup.find("head")
        if not head:
            return {}
        return {
            "title": head.find("title").text if head.find("title") else None,
            "author": self._get_meta(head, "author"),
            "meta_description": self._get_meta(head, "description"),
            "schema": self._get_json_ld(head),
            "og_tags": self._get_og_tags(head),
            "canonical": self._get_canonical(head),
        }

    def _get_meta(self, head, name):
        tag = head.find("meta", attrs={"name": name}) or head.find("meta", attrs={"property": name})
        return tag["content"] if tag else None

    def _get_json_ld(self, head):
        script_tag = head.find("script", {"type": "application/ld+json"})
        return json.loads(script_tag.text) if script_tag else None

    def _get_og_tags(self, head):
        og_tags = {}
        for tag in head.find_all("meta", attrs={"property": True}):
            if tag["property"].startswith("og:"):
                og_tags[tag["property"]] = tag["content"]
        return og_tags

    def _get_canonical(self, head):
        link = head.find("link", attrs={"rel": "canonical"})
        return link["href"] if link else None
