# Originally from PySpur (https://github.com/PySpur-Dev/pyspur), licensed under Apache-2.0.
# Modified by Alokin LLC, 2026; modifications licensed under FCL-1.0-ALv2.
# SPDX-License-Identifier: Apache-2.0 AND FCL-1.0-ALv2
# type: ignore
import asyncio
import base64
import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

import litellm
from docx2python import docx2python
from dotenv import load_dotenv
from litellm import acompletion
from litellm.types.utils import Message
from ollama import AsyncClient
from pydantic import BaseModel, Field
from tenacity import AsyncRetrying, stop_after_attempt, wait_random_exponential

from ...utils.file_utils import encode_file_to_base64_data_url
from ...utils.mime_types_utils import get_mime_type_for_url
from ...utils.path_utils import is_external_url, resolve_file_path
from ._model_info import LLMModels
from ._providers import OllamaOptions, setup_azure_configuration, setup_ifm_configuration

# uncomment for debugging litellm issues
# litellm.set_verbose=True
load_dotenv()

# Enable parameter dropping for unsupported parameters
litellm.drop_params = True

# Clean up Azure API base URL if needed
azure_api_base = os.getenv("AZURE_OPENAI_API_BASE", "").rstrip("/")
if azure_api_base.endswith("/openai"):
    azure_api_base = azure_api_base.rstrip("/openai")
os.environ["AZURE_OPENAI_API_BASE"] = azure_api_base

# Set OpenAI base URL if provided
openai_base_url = os.getenv("OPENAI_API_BASE")
if openai_base_url:
    litellm.api_base = openai_base_url

# If Azure OpenAi is configured, set it as the default provider
if os.getenv("AZURE_OPENAI_API_KEY"):
    litellm.api_key = os.getenv("AZURE_OPENAI_API_KEY")

_provider_backoff_until: dict[str, datetime] = {}


def _get_provider_from_model(model: str) -> str:
    if model.startswith("ifm/"):
        return "ifm"
    try:
        _, provider, _, _ = litellm.get_llm_provider(model)
        return provider or "unknown"
    except Exception:
        return model.split("/")[0] if "/" in model else "openai"


def _set_provider_backoff(provider: str, seconds: float = 60.0) -> None:
    new_until = datetime.now() + timedelta(seconds=seconds)
    current = _provider_backoff_until.get(provider)
    if not current or new_until > current:
        _provider_backoff_until[provider] = new_until
        logging.warning(
            f"Rate limit hit for provider '{provider}'. "
            f"Backing off {seconds:.0f}s (until {new_until.strftime('%H:%M:%S')})."
        )


async def _wait_for_provider_capacity(provider: str) -> None:
    while True:
        until = _provider_backoff_until.get(provider)
        if not until:
            return
        remaining = (until - datetime.now()).total_seconds()
        if remaining <= 0:
            _provider_backoff_until.pop(provider, None)
            return
        logging.info(f"Provider '{provider}' is rate-limited. Waiting {remaining:.0f}s...")
        await asyncio.sleep(min(remaining, 10))


def _extract_retry_after(error_str: str) -> float | None:
    patterns = [
        r"retry after (\d+\.?\d*)\s*seconds?",
        r"try again in (\d+\.?\d*)\s*seconds?",
        r"\"retry_after\":\s*(\d+\.?\d*)",
        r"Retry-After[:\s]+(\d+\.?\d*)",
        r"Please try again in (\d+\.?\d*)\s*seconds?",
    ]
    for p in patterns:
        m = re.search(p, error_str, re.IGNORECASE)
        if m:
            return float(m.group(1))
    return None


class ModelInfo(BaseModel):
    model: LLMModels = Field(LLMModels.GPT_4O, description="The LLM model to use for completion")
    max_tokens: Optional[int] = Field(
        ...,
        ge=1,
        le=65536,
        description="Maximum number of tokens the model can generate",
    )
    temperature: Optional[float] = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Temperature for randomness, between 0.0 and 1.0",
    )
    top_p: Optional[float] = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Top-p sampling value, between 0.0 and 1.0",
    )


def create_messages(
    system_message: str,
    user_message: str,
    few_shot_examples: Optional[List[Dict[str, str]]] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> List[Dict[str, str]]:
    messages = [{"role": "system", "content": system_message}]
    if few_shot_examples:
        for example in few_shot_examples:
            messages.append({"role": "user", "content": example["input"]})
            messages.append({"role": "assistant", "content": example["output"]})
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    return messages


def create_messages_with_images(
    system_message: str,
    base64_image: str,
    user_message: str = "",
    few_shot_examples: Optional[List[Dict]] = None,
    history: Optional[List[Dict]] = None,
) -> List[Dict[str, str]]:
    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": system_message}],
        }
    ]
    if few_shot_examples:
        for example in few_shot_examples:
            messages.append(
                {
                    "role": "user",
                    "content": [{"type": "text", "text": example["input"]}],
                }
            )
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": example["img"]},
                        }
                    ],
                }
            )
            messages.append(
                {
                    "role": "assistant",
                    "content": [{"type": "text", "text": example["output"]}],
                }
            )
    if history:
        messages.extend(history)
    messages.append(
        {
            "role": "user",
            "content": [{"type": "image_url", "image_url": {"url": base64_image}}],
        }
    )
    if user_message:
        messages[-1]["content"].append({"type": "text", "text": user_message})
    return messages


def async_retry(*dargs, **dkwargs):
    def decorator(f: Callable) -> Callable:
        r = AsyncRetrying(*dargs, **dkwargs)

        async def wrapped_f(*args, **kwargs):
            async for attempt in r:
                with attempt:
                    return await f(*args, **kwargs)

        return wrapped_f

    return decorator


@async_retry(
    wait=wait_random_exponential(min=5, max=60),
    stop=stop_after_attempt(3),
    reraise=True,
    retry=lambda e: not isinstance(
        e,
        (
            litellm.exceptions.AuthenticationError,
            ValueError,
            litellm.exceptions.RateLimitError,
        ),
    ),
)
async def _completion_with_transient_backoff(**kwargs) -> Message:
    """Call the LLM completion endpoint with backoff for transient errors.

    Supports IFM, Azure OpenAI, standard OpenAI, or Ollama based on the model name.
    """
    try:
        model = kwargs.get("model", "")
        logging.info("=== LLM Request Configuration ===")
        logging.info(f"Requested Model: {model}")

        # IFM goes first so that a configured Azure key does not take over its calls
        if model.startswith("ifm/"):
            ifm_kwargs = setup_ifm_configuration(kwargs)
            logging.info(f"Using IFM config for model: {ifm_kwargs['model']}")
            response = await acompletion(**ifm_kwargs, drop_params=True)
            return response.choices[0].message

        # Use Azure if either 'azure/' is prefixed or if an Azure API key
        # is provided and not using Ollama
        elif model.startswith("azure/") or (
            os.getenv("AZURE_OPENAI_API_KEY") and not model.startswith("ollama/")
        ):
            azure_kwargs = setup_azure_configuration(kwargs)
            logging.info(f"Using Azure config for model: {azure_kwargs['model']}")
            try:
                response = await acompletion(**azure_kwargs, drop_params=True)
                return response.choices[0].message.content
            except Exception as e:
                logging.error(f"Error calling Azure OpenAI: {e}")
                raise

        elif model.startswith("ollama/"):
            logging.info("=== Ollama Configuration ===")
            response = await acompletion(**kwargs, drop_params=True)
            return response.choices[0].message
        else:
            logging.info("=== Standard Configuration ===")
            response = await acompletion(**kwargs, drop_params=True)
            return response.choices[0].message

    except Exception as e:
        logging.error("=== LLM Request Error ===")
        # Create a save copy of kwargs without sensitive information
        save_config = kwargs.copy()
        save_config["api_key"] = "********" if "api_key" in save_config else None
        logging.error(f"Error occurred with configuration: {save_config}")
        logging.error(f"Error type: {type(e).__name__}")
        logging.error(f"Error message: {str(e)}")
        if hasattr(e, "response"):
            logging.error(f"Response status: {getattr(e.response, 'status_code', 'N/A')}")
            logging.error(f"Response body: {getattr(e.response, 'text', 'N/A')}")
        raise e


async def completion_with_backoff(**kwargs) -> Message:
    provider = _get_provider_from_model(kwargs.get("model", ""))
    max_rate_limit_attempts = 8

    for attempt in range(max_rate_limit_attempts):
        await _wait_for_provider_capacity(provider)
        try:
            return await _completion_with_transient_backoff(**kwargs)
        except litellm.exceptions.RateLimitError as e:
            retry_after = _extract_retry_after(str(e)) or 60.0
            _set_provider_backoff(provider, retry_after)
            if attempt >= max_rate_limit_attempts - 1:
                raise

    raise RuntimeError("Unreachable")  # type: ignore


def sanitize_json_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Make a JSON schema compatible with the LLM providers.

    * sets "additionalProperties" to False
    * adds all properties to the "required" list recursively
    """
    if "additionalProperties" not in schema:
        schema["additionalProperties"] = False
    if "properties" in schema:
        for key, value in schema["properties"].items():
            if "required" not in schema:
                schema["required"] = []
            if key not in schema["required"]:
                schema["required"].append(key)
            sanitize_json_schema(value)
    if "$defs" in schema:
        for key in schema["$defs"]:
            schema["$defs"][key] = sanitize_json_schema(schema["$defs"][key])
    return schema


def strip_additional_properties_from_non_objects(schema: Any) -> Any:
    """Keep "additionalProperties" only on object schemas.

    IFM rejects it on other types: "Invalid fields for schema with types ['string']".
    """
    if isinstance(schema, dict):
        if schema.get("type") != "object":
            schema.pop("additionalProperties", None)
        for value in schema.values():
            strip_additional_properties_from_non_objects(value)
    elif isinstance(schema, list):
        for value in schema:
            strip_additional_properties_from_non_objects(value)
    return schema


def _json_schema_response_format(output_json_schema: Dict[str, Any]) -> Dict[str, Any]:
    if "name" not in output_json_schema and "schema" not in output_json_schema:
        output_json_schema = {
            "schema": output_json_schema,
            "strict": True,
            "name": "output",
        }
    return {"type": "json_schema", "json_schema": output_json_schema}


async def generate_text(
    messages: List[Dict[str, str]],
    model_name: str,
    temperature: float = 0.5,
    json_mode: bool = False,
    max_tokens: int = 16384,
    api_base: Optional[str] = None,
    url_variables: Optional[Dict[str, str]] = None,
    output_json_schema: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: Optional[str] = "auto",
    thinking: Optional[Dict[str, Any]] = None,
) -> Message:
    """Generate text using the specified LLM model.

    Args:
        messages: List of message dictionaries with 'role' and 'content'
        model_name: Name of the LLM model to use
        temperature: Temperature for randomness, between 0.0 and 1.0
        json_mode: Flag to indicate if JSON output is required
        max_tokens: Maximum number of tokens the model can generate
        api_base: Base URL for the API
        url_variables: Dictionary of URL variables for file inputs
        output_json_schema: JSON schema for the output format
        tools: List of function schemas for function calling
        tool_choice: By default the model will determine when and how many tools to use. You can
            force specific behavior with the tool_choice parameter.
            auto: (Default) Call zero, one, or multiple functions. tool_choice: "auto"
            required: Call one or more functions. tool_choice: "required"
            Forced Function: Call exactly one specific function.
                tool_choice: {"type": "function", "function": {"name": "get_weather"}}

        thinking: Thinking parameters for the model

    """
    kwargs = {
        "model": model_name,
        "max_tokens": max_tokens,
        "messages": messages,
        "temperature": temperature,
    }

    # Add function calling parameters if provided
    if tools:
        kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice

    # Get model info to check capabilities
    model_info = LLMModels.get_model_info(model_name)

    # Only add thinking parameters if explicitly requested and supported by the model
    if thinking and model_info and model_info.constraints.supports_thinking:
        kwargs["thinking"] = thinking

    if model_name == "deepseek/deepseek-reasoner":
        kwargs.pop("temperature")

    # Get model info to check if it supports JSON output
    if model_info and not model_info.constraints.supports_temperature:
        kwargs.pop("temperature", None)
    if model_info and not model_info.constraints.supports_max_tokens:
        kwargs.pop("max_tokens", None)
    supports_json = model_info and model_info.constraints.supports_JSON_output

    # Only process JSON schema if the model supports it
    if supports_json:
        if output_json_schema is None:
            output_json_schema = {
                "type": "object",
                "properties": {"output": {"type": "string"}},
                "required": ["output"],
            }
        elif output_json_schema.strip() != "":
            output_json_schema = json.loads(output_json_schema)
            output_json_schema = sanitize_json_schema(output_json_schema)
        else:
            raise ValueError("Invalid output schema", output_json_schema)
        output_json_schema["additionalProperties"] = False

        if model_name.startswith("ifm/"):
            # litellm cannot look up response-schema support for the IFM provider, and IFM
            # documents response_format with json_schema, so request it directly
            kwargs["response_format"] = _json_schema_response_format(
                strip_additional_properties_from_non_objects(output_json_schema)
            )
        # check if the model supports response format
        elif "response_format" in litellm.get_supported_openai_params(
            model=model_name, custom_llm_provider=model_info.provider
        ):
            if litellm.supports_response_schema(
                model=model_name, custom_llm_provider=model_info.provider
            ) or model_name.startswith("anthropic"):
                kwargs["response_format"] = _json_schema_response_format(output_json_schema)
            else:
                kwargs["response_format"] = {"type": "json_object"}
                schema_for_prompt = json.dumps(output_json_schema)
                system_message = next(
                    message for message in messages if message["role"] == "system"
                )
                system_message["content"] += (
                    "\nYou must respond with valid JSON only."
                    + " No other text before or after the JSON Object."
                    + "The JSON Object must adhere to this schema: "
                    + schema_for_prompt
                )

    if json_mode and supports_json:
        if model_name.startswith("ollama"):
            if api_base is None:
                api_base = os.getenv("OLLAMA_BASE_URL")
            options = OllamaOptions(temperature=temperature, max_tokens=max_tokens)
            raw_response = await ollama_with_backoff(
                model=model_name,
                options=options,
                messages=messages,
                format="json",
                api_base=api_base,
            )
            response = raw_response
            message_response = Message(
                content=json.dumps(raw_response),
                tool_calls=[],
            )
        # Handle inputs with URL variables
        elif url_variables:
            # check if the mime type is supported
            mime_type = get_mime_type_for_url(url_variables["image"])
            if not model_info.constraints.is_mime_type_supported(mime_type):
                raise ValueError(
                    f"""Unsupported file type: "{mime_type.value}" for model {model_name}."""
                    f""" Supported types: {
                        [mime.value for mime in model_info.constraints.supported_mime_types]
                    }"""
                )

            # Transform messages to include URL content
            transformed_messages = []
            for msg in messages:
                if msg["role"] == "user":
                    content = [{"type": "text", "text": msg["content"]}]
                    # Add any URL variables as image_url or other supported types
                    for _, url in url_variables.items():
                        if url:  # Only add if URL is provided
                            # Check if the URL is a base64 data URL
                            if is_external_url(url) or url.startswith("data:"):
                                content.append(
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": url},
                                    }
                                )
                            else:
                                # For file paths, encode the file with appropriate MIME type
                                try:
                                    # Use the new path resolution utility
                                    file_path = resolve_file_path(url)
                                    logging.info(f"Reading file from: {file_path}")

                                    # Check if file is a DOCX file
                                    if str(file_path).lower().endswith(".docx"):
                                        # Convert DOCX to XML
                                        xml_content = convert_docx_to_xml(str(file_path))
                                        # Encode the XML content directly
                                        data_url = (
                                            f"data:text/xml;base64,"
                                            f"{base64.b64encode(xml_content.encode()).decode()}"
                                        )
                                    else:
                                        data_url = encode_file_to_base64_data_url(str(file_path))

                                    content.append(
                                        {
                                            "type": "image_url",
                                            "image_url": {"url": data_url},
                                        }
                                    )
                                except Exception as e:
                                    logging.error(f"Error reading file {url}: {str(e)}")
                                    raise
                    msg["content"] = content
                transformed_messages.append(msg)
            kwargs["messages"] = transformed_messages
            message_response: Message = await completion_with_backoff(**kwargs)
            response = message_response.content
            raw_response = response
        else:
            message_response: Message = await completion_with_backoff(**kwargs)
            response = message_response.content
            raw_response = response
    else:
        if model_name.startswith("ollama"):
            if api_base is None:
                api_base = os.getenv("OLLAMA_BASE_URL")
            options = OllamaOptions(temperature=temperature, max_tokens=max_tokens)
            raw_response = await ollama_with_backoff(
                model=model_name,
                options=options,
                messages=messages,
                format="json",
                api_base=api_base,
            )
            response = raw_response
            message_response = Message(
                content=json.dumps(raw_response),
                tool_calls=[],
            )
        else:
            message_response: Message = await completion_with_backoff(**kwargs)
            response = message_response.content

    # For models that don't support JSON output, wrap the response in a JSON structure
    if not supports_json:
        sanitized_response = response.replace('"', '\\"').replace("\n", "\\n")
        if model_info and model_info.constraints.supports_reasoning:
            separator = model_info.constraints.reasoning_separator
            sanitized_response = re.sub(separator, "", sanitized_response, flags=re.DOTALL)

        # Check for provider-specific fields
        if hasattr(raw_response, "choices") and len(raw_response.choices) > 0:
            if hasattr(raw_response.choices[0].message, "provider_specific_fields"):
                provider_fields = raw_response.choices[0].message.provider_specific_fields
                message_response.content = json.dumps(
                    {
                        "output": sanitized_response,
                        "provider_specific_fields": provider_fields,
                    }
                )
                return message_response
        message_response.content = f'{{"output": "{sanitized_response}"}}'
        return message_response

    # Ensure response is valid JSON for models that support it
    if supports_json:
        try:
            if message_response.tool_calls and len(message_response.tool_calls) > 0:
                # If the model made tool calls, return the raw response
                return message_response
            else:
                # Attempt to parse the response as JSON to validate it
                _ = json.loads(response)
                return message_response
        except json.JSONDecodeError:
            logging.error(f"Response is not valid JSON: {response}")
            # Try to fix common json issues
            if not response.startswith("{"):
                # Extract JSON if there is extra text
                json_match = re.search(r"\{.*\}", response, re.DOTALL)
                if json_match:
                    response = json_match.group(0)
                    try:
                        json.loads(response)
                        message_response.content = response
                        return message_response
                    except json.JSONDecodeError:
                        pass

            # If all attempts to parse JSON fail, wrap the response in a JSON structure
            sanitized_response = response.replace('"', '\\"').replace("\n", "\\n")
            # Check for provider-specific fields
            if hasattr(raw_response, "choices") and len(raw_response.choices) > 0:
                if hasattr(raw_response.choices[0].message, "provider_specific_fields"):
                    provider_fields = raw_response.choices[0].message.provider_specific_fields
                    message_response.content = json.dumps(
                        {
                            "output": sanitized_response,
                            "provider_specific_fields": provider_fields,
                        }
                    )
                    return message_response
            message_response.content = f'{{"output": "{sanitized_response}"}}'
            return message_response

    return message_response


def convert_output_schema_to_json_schema(
    output_schema: Dict[str, Any],
) -> Dict[str, Any]:
    """Convert a simple output schema to a JSON schema.

    Simple output schema is a dictionary with field names and types.
    Types can be one of 'str', 'int', 'float' or 'bool'.
    """
    json_schema = {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }
    for field, field_type in output_schema.items():
        if field_type == "str" or field_type == "string":
            json_schema["properties"][field] = {"type": "string"}
        elif field_type == "int" or field_type == "integer":
            json_schema["properties"][field] = {"type": "integer"}
        elif field_type == "float" or field_type == "number":
            json_schema["properties"][field] = {"type": "number"}
        elif field_type == "bool" or field_type == "boolean":
            json_schema["properties"][field] = {"type": "boolean"}
        json_schema["required"].append(field)
    return json_schema


def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


@async_retry(wait=wait_random_exponential(min=30, max=120), stop=stop_after_attempt(3))
async def ollama_with_backoff(
    model: str,
    messages: list[dict[str, str]],
    format: Optional[str | dict[str, Any]] = None,
    options: Optional[OllamaOptions] = None,
    api_base: Optional[str] = None,
) -> str:
    """Make an async Ollama API call with exponential backoff retry logic.

    Args:
        model: The name of the Ollama model to use
        messages: List of message dictionaries with 'role' and 'content'
        format: Format for the response, either 'json' or a dictionary
        options: OllamaOptions instance with model parameters
        api_base: Base URL for the Ollama API

    Returns:
        Either a string response or a validated Pydantic model instance

    """
    client = AsyncClient(host=api_base)
    try:
        response = await client.chat(
            model=model.replace("ollama/", ""),
            messages=messages,
            format=format,
            options=(options or OllamaOptions()).to_dict(),
        )
        return response.message.content
    except Exception as e:
        logging.error(f"Error calling Ollama API: {e}")
        raise e


def convert_docx_to_xml(file_path: str) -> str:
    """Convert a DOCX file to XML format.

    Args:
        file_path: Path to the DOCX file
    Returns:
        XML string representation of the DOCX file

    """
    try:
        with docx2python(file_path) as docx_content:
            # Convert the document content to XML format
            xml_content = "<?xml version='1.0' encoding='UTF-8'?>\n<document>\n"

            # Add metadata
            xml_content += "<metadata>\n"
            for key, value in docx_content.properties.items():
                if value:  # Only add non-empty properties
                    xml_content += f"<{key}>{value}</{key}>\n"
            xml_content += "</metadata>\n"

            # Add document content
            xml_content += "<content>\n"
            for paragraph in docx_content.text:
                if paragraph:  # Skip empty paragraphs
                    xml_content += f"<paragraph>{paragraph}</paragraph>\n"
            xml_content += "</content>\n"
            xml_content += "</document>"

            return xml_content
    except Exception as e:
        logging.error(f"Error converting DOCX to XML: {str(e)}")
        raise
