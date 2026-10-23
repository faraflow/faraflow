# Originally from PySpur (https://github.com/PySpur-Dev/pyspur), licensed under Apache-2.0.
# Modified by Alokin LLC, 2026; modifications licensed under FCL-1.0-ALv2.
# SPDX-License-Identifier: Apache-2.0 AND FCL-1.0-ALv2
import json
import logging
import os

import httpx
from pydantic import BaseModel, Field  # type: ignore

from ...base import BaseNode, BaseNodeConfig, BaseNodeInput, BaseNodeOutput
from ...utils.template_utils import render_template_or_get_first_string
from ..driveup.http_config import CRAWL_USER_AGENT


class JinaReaderNodeInput(BaseNodeInput):
    """Input for the JinaReader node"""

    class Config:
        extra = "allow"


class JinaReaderNodeOutput(BaseNodeOutput):
    title: str = Field("", description="The title of scraped page")
    content: str = Field("", description="The content of the scraped page in markdown format")


class JinaReaderNodeConfig(BaseNodeConfig):
    url_template: str = Field(
        "https://r.jina.ai/{url}",
        description="The URL to crawl and convert into clean markdown.",
    )
    use_readerlm_v2: bool = Field(True, description="Use the Reader LM v2 model to process the URL")
    has_fixed_output: bool = True
    output_json_schema: str = Field(
        default=json.dumps(JinaReaderNodeOutput.model_json_schema()),
        description="The JSON schema for the output of the node",
    )


JINA_ENDPOINT = "https://r.jina.ai/"


class JinaReaderNode(BaseNode):
    name = "jina_reader_node"
    display_name = "Reader"
    logo = "/images/jina.png"
    category = "Jina.AI"

    config_model = JinaReaderNodeConfig
    input_model = JinaReaderNodeInput
    output_model = JinaReaderNodeOutput

    async def run(self, input: BaseModel) -> BaseModel:
        try:
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Engine": "cf-browser-rendering",
                "X-Respond-Timing": "media-idle",
                # Override the UA Jina uses to fetch the page so sites that block
                # default crawler UAs still serve us (and we stay identifiable).
                "X-User-Agent": CRAWL_USER_AGENT,
            }

            logging.debug(f"Jina Headers: {headers}")
            jina_api_key = os.getenv("JINA_API_KEY")
            if jina_api_key:
                headers["Authorization"] = f"Bearer {jina_api_key}"

            if self.config.use_readerlm_v2:
                headers["X-Respond-With"] = "readerlm-v2"

            raw_input_dict = input.model_dump()
            rendered = render_template_or_get_first_string(
                self.config.url_template, raw_input_dict, self.name
            )
            # Strip the Jina prefix if url_template includes it (legacy configs)
            target_url = rendered.removeprefix(JINA_ENDPOINT) if rendered.startswith(JINA_ENDPOINT) else rendered

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    JINA_ENDPOINT,
                    headers=headers,
                    json={"url": target_url},
                    timeout=None,
                )
                logging.debug("Fetched from Jina: {text}".format(text=response.text))
                output = JinaReaderNodeOutput.model_validate(response.json()["data"])
                if output.content.startswith("```markdown"):
                    output.content = output.content[12:-4]
                if not output.content.strip():
                    # The page is blocking automated access or needs JS rendering.
                    # Return empty content instead of raising — raising aborts the
                    # whole workflow, and an empty result is itself a crawlability
                    # signal the downstream gate/verdict node can act on.
                    logging.warning(
                        f"Jina returned no content for {target_url} — "
                        "the page may be blocking automated access or requires JavaScript rendering."
                    )
                    return JinaReaderNodeOutput(title=output.title, content="")
                return output
        except Exception as e:
            logging.error(f"Failed to convert URL: {e}")
            raise
