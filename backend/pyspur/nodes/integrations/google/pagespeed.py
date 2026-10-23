# Copyright 2026 Alokin LLC
# SPDX-License-Identifier: FCL-1.0-ALv2
import os, json, logging
from dotenv import load_dotenv
from typing_extensions import Dict
from pydantic import BaseModel, Field  # type: ignore
import httpx
from glom import glom, Delete

from ...base import BaseNode, BaseNodeConfig, BaseNodeInput, BaseNodeOutput
from ...utils.template_utils import render_template_or_get_first_string

load_dotenv()


logger = logging.getLogger(__name__)

class PagespeedNodeConfig(BaseNodeConfig):
    url_template: str = Field(
        "{url}",
        description="The URL to run PageSpeed analysis",
    )
    check_mobile: bool = Field(True, description="Check for mobile pagespeed")

class PagespeedNodeInput(BaseNodeInput):
    pass

class PagespeedNodeOutput(BaseNodeOutput):
    title: str = "PageSpeed"
    content: Dict = {}

class PagespeedNode(BaseNode):
    name = "pagesoeed_node"
    display_name = "Google PageSpeed"
    logo = "/images/google.png"
    category = "Google"

    config_model = PagespeedNodeConfig
    input_model = PagespeedNodeInput
    output_model = PagespeedNodeOutput

    async def _scan(self, url, strategy):
        api_url = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed'
        api_key = os.getenv("GOOGLE_API_KEY")

        params = {
            'key': api_key,
            'url': url,
            'strategy': strategy,
            # Request all Lighthouse categories. PageSpeed defaults to performance-only;
            # without these the accessibility/best-practices/seo scores come back null.
            'category': ['PERFORMANCE', 'ACCESSIBILITY', 'BEST_PRACTICES', 'SEO'],
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                        "GET",
                        api_url,
                        params=params,
                        # httpx automatically sets Content-Type and serializes JSON
                        timeout=None
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            print(f"Error during the request: {e}")
            raise e

    def prune_response(self, response):
        # Keep `lighthouseResult.audits` — that is where the core web vital values
        # (LCP/CLS/TBT/...) and accessibility audit details live. Instead, drop the
        # genuine bulk: the full-page screenshot blob and each audit's heavy `details`.
        keys = [
            'lighthouseResult.i18n',
            'lighthouseResult.categoryGroups',
            # 'lighthouseResult.fullPageScreenshot',
            'lighthouseResult.timing',
            'lighthouseResult.entities',
            'lighthouseResult.stackPacks',
        ]

        g = response
        for key in keys:
            g = glom(g, Delete(key, ignore_missing=True))

        # Strip the large per-audit `details` tables, preserving the scalar fields
        # downstream nodes need (id/title/description/score/numericValue/displayValue).
        audits = glom(g, 'lighthouseResult.audits', default=None)
        if isinstance(audits, dict):
            for audit in audits.values():
                if isinstance(audit, dict):
                    audit.pop('details', None)
        return g


    async def run(self, input: BaseModel) -> BaseModel:

        try:
            headers = {
                'Accept': 'application/json',
            }

            # Grab the entire dictionary from the input
            raw_input_dict = input.model_dump()

            # Render url_template
            url = render_template_or_get_first_string(
                self.config.url_template, raw_input_dict, self.name
            )

            response = await self._scan(url, strategy='mobile' if self.config.check_mobile else 'desktop')
            response = self.prune_response(response)
            return PagespeedNodeOutput(title='PageSpeed', content=response)

        except Exception as e:
            logger.error(f"Failed to convert URL: {e}")
            return None
