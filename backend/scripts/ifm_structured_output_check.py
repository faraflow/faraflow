"""Minimal repro for IFM structured output (RFC0015).

Run inside the backend container:

    python scripts/ifm_structured_output_check.py [model]

Loads ../.env, then sends the same request faraflow would, with schema variants.
"""

import asyncio
import copy
import json
import sys

from dotenv import load_dotenv
from litellm import acompletion

load_dotenv("/pyspur/.env")

from pyspur.nodes.llm._providers import setup_ifm_configuration  # noqa: E402
from pyspur.nodes.llm._utils import (  # noqa: E402
    _json_schema_response_format,
    sanitize_json_schema,
    strip_additional_properties_from_non_objects,
)

MODEL = sys.argv[1] if len(sys.argv) > 1 else "ifm/K2-Horizon-375B-A23B"
SCHEMA = {
    "type": "object",
    "properties": {"joke": {"type": "string"}, "rating": {"type": "integer"}},
}


async def attempt(label: str, schema: dict) -> None:
    kwargs = setup_ifm_configuration(
        {
            "model": MODEL,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": "Tell me a short joke and rate it 1-10."}],
            "response_format": _json_schema_response_format(schema),
        }
    )
    try:
        response = await acompletion(**kwargs, drop_params=True)
        choice = response.choices[0]
        content = choice.message.content or ""
        try:
            json.loads(content)
            valid = "json"
        except ValueError:
            valid = "NOT-JSON"
        print(f"[OK ] {label}: {valid} finish={choice.finish_reason} {content[:60]!r}")
    except Exception as e:
        print(f"[ERR] {label}: {str(e)[:300]}")


NESTED = {
    "type": "object",
    "properties": {
        "joke": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "meta": {"type": "object", "properties": {"rating": {"type": "integer"}}},
    },
}


async def main() -> None:
    sanitized = sanitize_json_schema(copy.deepcopy(SCHEMA))
    print("schema sent by faraflow today:", json.dumps(sanitized))
    await attempt("faraflow sanitized schema (before fix)", sanitized)
    await attempt(
        "fixed: additionalProperties only on objects",
        strip_additional_properties_from_non_objects(copy.deepcopy(sanitized)),
    )
    nested = sanitize_json_schema(copy.deepcopy(NESTED))
    await attempt(
        "fixed: nested", strip_additional_properties_from_non_objects(copy.deepcopy(nested))
    )


asyncio.run(main())
