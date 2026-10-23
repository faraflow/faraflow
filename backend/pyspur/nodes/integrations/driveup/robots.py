# Copyright 2026 Alokin LLC
# SPDX-License-Identifier: FCL-1.0-ALv2
import json
import logging
from typing import Dict, Optional, Any
from urllib.parse import urlparse, urlsplit
from pydantic import BaseModel, Field  # type: ignore
from . import URLScrapingNode, URLScrapingNodeInput, URLScrapingNodeConfig, URLScrapingNodeOutput

from protego import Protego


# From: https://github.com/ai-robots-txt/ai.robots.txt
ROBOTS = """
AI2Bot
Ai2Bot-Dolma
Amazonbot
anthropic-ai
Applebot
Applebot-Extended
Brightbot 1.0
Bytespider
CCBot
ChatGPT-User
Claude-Web
ClaudeBot
cohere-ai
cohere-training-data-crawler
Crawlspace
Diffbot
DuckAssistBot
FacebookBot
FriendlyCrawler
Google-Extended
GoogleOther
GoogleOther-Image
GoogleOther-Video
GPTBot
iaskspider/2.0
ICC-Crawler
ImagesiftBot
img2dataset
ISSCyberRiskCrawler
Kangaroo Bot
Meta-ExternalAgent
Meta-ExternalFetcher
OAI-SearchBot
omgili
omgilibot
PanguBot
PerplexityBot
PetalBot
Scrapy
SemrushBot-OCOB
SemrushBot-SWA
Sidetrade indexer bot
Timpibot
VelenPublicWebCrawler
Webzio-Extended
YouBot
""".strip().splitlines()


class RobotsNodeInput(URLScrapingNodeInput):
    pass


class RobotEval(BaseModel):
    contains: bool
    can_fetch: bool

class RobotsNodeOutput(URLScrapingNodeOutput):
    crawl_result: str
    has_robots: bool
    robots: Dict[str, Dict]

class RobotsNodeConfig(URLScrapingNodeConfig):
    # has_fixed_output: bool = True
    # output_json_schema: str = Field(
    #     default=json.dumps(RobotsNodeOutput.model_json_schema()),
    #     description="The JSON schema for the output of the node",
    # )
    pass


class RobotsNode(URLScrapingNode):

    name = "robots_node"
    display_name = "Robots.txt"
    logo = "/images/web.svg"
    category = "Web"

    config_model = RobotsNodeConfig
    input_model = RobotsNodeInput
    output_model = RobotsNodeOutput

    def get_request_data(self, url_template: str) -> Dict:
        us = urlsplit(url_template)
        scheme, netloc = us[0], us[1]
        request = {
            'method': 'GET',
            'url': f'{scheme}://{netloc}/robots.txt',
        }
        return request

    async def process_response(self, response) -> BaseModel:
        if response is not None:
            rp = Protego.parse(response.text)
            robots = {
                robot: {
                    'contains': response.text.find(robot) > -1,
                    'can_fetch': rp.can_fetch(self.request_url(), robot)
                }
                for robot in ROBOTS
            }
            return RobotsNodeOutput(crawl_result=response.text, has_robots=True, robots=robots)
        else:
            # Fetching robots.txt failed (e.g. 403/blocked, unreachable, timeout).
            # Treat this as "no robots.txt available" AND assume AI crawlers cannot
            # access the site: mark every bot as not fetchable. Returning a valid
            # output here (instead of touching response.text / omitting `robots`)
            # keeps the workflow running instead of stopping on the failed request.
            robots = {robot: {'contains': False, 'can_fetch': False} for robot in ROBOTS}
            return RobotsNodeOutput(crawl_result='', has_robots=False, robots=robots)
