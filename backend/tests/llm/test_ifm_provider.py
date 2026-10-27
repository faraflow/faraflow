# Copyright 2026 Alokin LLC
# SPDX-License-Identifier: FCL-1.0-ALv2
"""Tests for the IFM (K2 Horizon / Jais 3) provider, RFC0015."""

import asyncio
import json
from types import SimpleNamespace
from typing import Any, Dict
from unittest.mock import AsyncMock

import pytest

from pyspur.nodes.llm import _utils
from pyspur.nodes.llm._model_info import LLMModels, LLMProvider
from pyspur.nodes.llm._providers import ifm_served_model_name, setup_ifm_configuration

IFM_MODELS = [m.value for m in LLMModels if m.value.startswith("ifm/")]


@pytest.fixture
def ifm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IFM_API_KEY", "test-ifm-key")
    monkeypatch.setenv("IFM_API_BASE", "http://ifm.test/v1")


def fake_completion() -> AsyncMock:
    message = SimpleNamespace(content='{"output": "hi"}', tool_calls=[])
    return AsyncMock(return_value=SimpleNamespace(choices=[SimpleNamespace(message=message)]))


def test_registry_has_the_models_served_by_the_api() -> None:
    assert sorted(IFM_MODELS) == ["ifm/Jais-3-MoVA-36B-A4B", "ifm/K2-Horizon-375B-A23B"]
    for model_id in IFM_MODELS:
        info = LLMModels.get_model_info(model_id)
        assert info is not None
        assert info.provider == LLMProvider.IFM
        assert info.constraints.max_tokens == 524288
        assert info.constraints.supports_JSON_output
        assert not info.constraints.supports_reasoning


def test_served_model_name_restores_upstream_name() -> None:
    assert ifm_served_model_name("ifm/K2-Horizon-375B-A23B") == "IFM/K2-Horizon-375B-A23B"
    assert ifm_served_model_name("ifm/Jais-3-MoVA-36B-A4B") == "IFM/Jais-3-MoVA-36B-A4B"


def test_setup_ifm_configuration(ifm_env: None) -> None:
    result = setup_ifm_configuration({"model": "ifm/K2-Horizon-375B-A23B", "messages": []})
    assert result["model"] == "openai/IFM/K2-Horizon-375B-A23B"
    assert result["api_base"] == "http://ifm.test/v1"
    assert result["api_key"] == "test-ifm-key"


@pytest.mark.parametrize("missing", ["IFM_API_KEY", "IFM_API_BASE"])
def test_missing_configuration_raises_value_error(
    ifm_env: None, monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    monkeypatch.delenv(missing)
    with pytest.raises(ValueError, match=missing):
        setup_ifm_configuration({"model": "ifm/K2-Horizon-375B-A23B"})


def test_provider_is_ifm_for_backoff() -> None:
    assert _utils._get_provider_from_model("ifm/K2-Horizon-375B-A23B") == "ifm"  # type: ignore[reportPrivateUsage]


def test_ifm_call_is_not_hijacked_by_azure(ifm_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "azure-key")
    acompletion = fake_completion()
    monkeypatch.setattr(_utils, "acompletion", acompletion)

    asyncio.run(
        _utils.completion_with_backoff(
            model="ifm/K2-Horizon-375B-A23B", messages=[{"role": "user", "content": "hi"}]
        )
    )

    kwargs: Dict[str, Any] = acompletion.call_args.kwargs
    assert kwargs["model"] == "openai/IFM/K2-Horizon-375B-A23B"
    assert kwargs["api_base"] == "http://ifm.test/v1"
    assert kwargs["api_key"] == "test-ifm-key"
    assert "deployment_id" not in kwargs


@pytest.mark.parametrize("model_id", IFM_MODELS)
def test_generate_text_requests_json_schema(
    ifm_env: None, monkeypatch: pytest.MonkeyPatch, model_id: str
) -> None:
    acompletion = fake_completion()
    monkeypatch.setattr(_utils, "acompletion", acompletion)
    schema = {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
    }

    asyncio.run(
        _utils.generate_text(
            messages=[{"role": "system", "content": "s"}, {"role": "user", "content": "q"}],
            model_name=model_id,
            json_mode=True,
            output_json_schema=json.dumps(schema),
        )
    )

    response_format = acompletion.call_args.kwargs["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["name"] == "output"
    assert list(response_format["json_schema"]["schema"]["properties"]) == ["answer"]
