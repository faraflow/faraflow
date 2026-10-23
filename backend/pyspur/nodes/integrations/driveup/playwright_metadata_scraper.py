# Copyright 2026 Alokin LLC
# SPDX-License-Identifier: FCL-1.0-ALv2
import json
import extruct
from playwright.async_api import async_playwright
from typing_extensions import Dict
from .metadata_scraper import MetaDataScraper, MetaScrapingNodeOutput
from ...base import BaseNode, BaseNodeConfig, BaseNodeInput, BaseNodeOutput
from pydantic import BaseModel, Field



class PlaywrightScraperNodeInput(BaseNodeInput):
    pass


class PlaywrightScraperNodeOutput(BaseNodeOutput):
    title: str = "Metadata"
    content: dict = Field(default_factory=dict, description="Metadata")


class PlaywrightScraperNodeConfig(BaseNodeConfig):
    url_template: str = Field(
        "",
        description="The URL to crawl and process.",
    )
    # has_fixed_output: bool = True
    # output_json_schema: str = Field(
    #     default=json.dumps(PlaywrightScraperNodeOutput.model_json_schema()),
    #     description="The JSON schema for the output of the node",
    # )


class PlaywrightScraper(MetaDataScraper):
    name = "playwright_scraping_node"
    display_name = "Playwright Metadata Scraper"

    async def _request(self, url: str) -> dict:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            self._request_url = url
            await page.goto(url, wait_until="load")

            content = await page.content()
            await browser.close()

            return content

    async def process_response(self, response) -> BaseModel:
        meta_data = self._extract_metadata(response)
        meta_data = extruct.extract(response, base_url=self._request_url)
        return PlaywrightScraperNodeOutput(content=meta_data)