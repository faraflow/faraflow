# Copyright 2026 Alokin LLC
# SPDX-License-Identifier: FCL-1.0-ALv2
import json
import logging
from typing import Dict
from urllib.parse import urlparse, urlsplit
from pydantic import BaseModel, Field  # type: ignore
from . import URLScrapingNode, URLScrapingNodeInput, URLScrapingNodeConfig, URLScrapingNodeOutput

logger = logging.getLogger(__name__)

class BeagleSecurityNodeInput(URLScrapingNodeInput):
    pass

class BeagleSecurityNodeConfig(URLScrapingNodeConfig):
    pass

class BeagleSecurityNodeOutput(URLScrapingNodeOutput):
    analysis: dict

class BeagleSecurityNode(URLScrapingNode):

    name = "beagle_security_node"
    display_name = "Beagle Security"
    logo = "/images/beaglesecurity.png"
    category = "Beagle Security"

    config_model = BeagleSecurityNodeConfig
    input_model = BeagleSecurityNodeInput
    output_model = BeagleSecurityNodeOutput

    def get_request_data(self, url_template: str) -> Dict:
        us = urlsplit(url_template)
        scheme, netloc = us[0], us[1]
        request = {
            'method': 'GET',
            'url': f'https://api.beaglesecurity.com/v2/freecheck/surfacescan',
            'params': {
                'url': url_template,
                'isprivate': 'true'
            }
        }
        logger.debug(request)
        return request

    async def process_response(self, response) -> BaseModel:
        return BeagleSecurityNodeOutput(crawl_result="", analysis=response.json())
