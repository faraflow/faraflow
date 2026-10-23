# Copyright 2026 Alokin LLC
# SPDX-License-Identifier: FCL-1.0-ALv2
import os, json, logging
from dotenv import load_dotenv
from typing_extensions import Dict
from pydantic import BaseModel, Field  # type: ignore
import httpx

from ...base import BaseNode, BaseNodeConfig, BaseNodeInput, BaseNodeOutput
from ...utils.template_utils import render_template_or_get_first_string

load_dotenv()

logger = logging.getLogger(__name__)

ALL_THREAT_TYPES = [
    "THREAT_TYPE_UNSPECIFIED",
    "MALWARE",
    "SOCIAL_ENGINEERING",
    "UNWANTED_SOFTWARE",
    "POTENTIALLY_HARMFUL_APPLICATION"
]

ALL_PLATFORM_TYPES = [
    "WINDOWS",
    "LINUX",
    "ANDROID",
    "OSX",
    "IOS",
    "ANY_PLATFORM"
]


class SafeBrowsingNodeConfig(BaseNodeConfig):
    url_template: str = Field(
        "{url}",
        description="The URL to run Safe Browsing check",
    )


class SafeBrowsingInputNode(BaseNodeInput):
    pass

class SafeBrowsingOutputNode(BaseNodeOutput):
    title: str = Field(
        "", description="The title of scraped page"
    )
    content: Dict = Field(
        dict, description="The content of the scraped page in markdown format"
    )


class SafeBrowsingNode(BaseNode):
    name = "safebrowsing_node"
    display_name = "Google Safe Browsing"
    logo = "/images/google.png"
    category = "Google"

    config_model = SafeBrowsingNodeConfig
    input_model = SafeBrowsingInputNode
    output_model = SafeBrowsingOutputNode

    async def _scan(self, urls, data=None, threat_types=None, platform_types=None):
        api_url = "https://safebrowsing.googleapis.com/v4/threatMatches:find"
        api_key = os.getenv("GOOGLE_API_KEY")
        threat_types = threat_types or ALL_THREAT_TYPES
        platform_types = platform_types or ["ANY_PLATFORM"]  #ALL_PLATFORM_TYPES

        params = {
            'key': api_key
        }

        data = {
            "client": {
                "clientId": "python-client",
                "clientVersion": "1.0.0"
            },
            "threatInfo": {
                "threatTypes": threat_types,
                "platformTypes": platform_types,
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": url} for url in urls]
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                        "POST",
                        api_url,
                        params=params,
                        json=data,
                        timeout=None
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            print(f"Error during the request: {e}")
            return None

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

            response = await self._scan([url])
            logger.debug(response)
            return SafeBrowsingOutputNode(title='Safe Browsing', content=response)

        except Exception as e:
            logger.error(f"Failed to convert URL: {e}")
            return SafeBrowsingOutputNode(title="", content="")
