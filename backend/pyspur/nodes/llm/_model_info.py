# Originally from PySpur (https://github.com/PySpur-Dev/pyspur), licensed under Apache-2.0.
# Modified by Alokin LLC, 2026; modifications licensed under FCL-1.0-ALv2.
# SPDX-License-Identifier: Apache-2.0 AND FCL-1.0-ALv2
from enum import Enum
from typing import Optional, Set

from pydantic import BaseModel

from ...utils.mime_types_utils import (
    MIME_TYPES_BY_CATEGORY,
    MimeCategory,
    RecognisedMimeType,
)


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    AZURE_OPENAI = "azure"
    DEEPSEEK = "deepseek"
    XAI = "xai"
    IFM = "ifm"


class ModelConstraints(BaseModel):
    max_tokens: int
    min_temperature: float = 0.0
    max_temperature: float = 1.0
    supports_JSON_output: bool = True
    supports_max_tokens: bool = True
    supports_temperature: bool = True
    supported_mime_types: Set[RecognisedMimeType] = set()  # Empty set means no multimodal support
    supports_reasoning: bool = False
    reasoning_separator: str = r"<think>.*?</think>"
    supports_thinking: bool = False
    thinking_budget_tokens: Optional[int] = None

    def add_mime_categories(self, categories: Set[MimeCategory]) -> "ModelConstraints":
        """Add MIME type support for entire categories.

        Args:
            categories: Set of MimeCategory to add support for. All MIME types
                      in these categories will be added.

        Returns:
            self: Returns self for method chaining.

        """
        for category in categories:
            self.supported_mime_types.update(MIME_TYPES_BY_CATEGORY[category])
        return self

    def add_mime_types(self, mime_types: Set[RecognisedMimeType]) -> "ModelConstraints":
        """Add support for specific MIME types.

        Args:
            mime_types: Set of specific RecognisedMimeType to add support for.

        Returns:
            self: Returns self for method chaining.

        """
        self.supported_mime_types.update(mime_types)
        return self

    def is_mime_type_supported(self, mime_type: RecognisedMimeType) -> bool:
        """Check if a specific MIME type is supported.

        Args:
            mime_type: The RecognisedMimeType to check.

        Returns:
            bool: True if the MIME type is supported, False otherwise.

        """
        return mime_type in self.supported_mime_types


class LLMModel(BaseModel):
    id: str
    provider: LLMProvider
    name: str
    constraints: ModelConstraints


class LLMModels(str, Enum):
    # OpenAI Models
    GPT_5_5 = "openai/gpt-5.5"
    GPT_5_5_PRO = "openai/gpt-5.5-pro"
    GPT_5_4 = "openai/gpt-5.4"
    GPT_5_4_MINI = "openai/gpt-5.4-mini"
    GPT_5_4_NANO = "openai/gpt-5.4-nano"
    GPT_4_1 = "openai/gpt-4.1"
    GPT_4_1_MINI = "openai/gpt-4.1-mini"
    GPT_4_1_NANO = "openai/gpt-4.1-nano"
    O3 = "openai/o3"
    O4_MINI = "openai/o4-mini"
    O1_PRO = "openai/o1-pro"
    O3_MINI = "openai/o3-mini"
    O3_MINI_2025_01_31 = "openai/o3-mini-2025-01-31"
    GPT_4O_MINI = "openai/gpt-4o-mini"
    GPT_4O = "openai/gpt-4o"
    GPT_4O_MINI_SEARCH_PREVIEW = "openai/gpt-4o-mini-search-preview"
    GPT_4O_SEARCH_PREVIEW = "openai/gpt-4o-search-preview"
    O1_PREVIEW = "openai/o1-preview"
    O1_MINI = "openai/o1-mini"
    O1 = "openai/o1"
    O1_2024_12_17 = "openai/o1-2024-12-17"
    O1_MINI_2024_09_12 = "openai/o1-mini-2024-09-12"
    O1_PREVIEW_2024_09_12 = "openai/o1-preview-2024-09-12"
    CHATGPT_4O_LATEST = "openai/chatgpt-4o-latest"

    # Azure OpenAI Models
    AZURE_GPT_4 = "azure/gpt-4"
    AZURE_GPT_35_TURBO = "azure/gpt-35-turbo"

    # Anthropic Models
    CLAUDE_OPUS_4_7 = "anthropic/claude-opus-4-7"
    CLAUDE_SONNET_4_6 = "anthropic/claude-sonnet-4-6"
    CLAUDE_HAIKU_4_5 = "anthropic/claude-haiku-4-5"
    CLAUDE_OPUS_4_6 = "anthropic/claude-opus-4-6"
    CLAUDE_SONNET_4_5 = "anthropic/claude-sonnet-4-5"
    CLAUDE_OPUS_4_5 = "anthropic/claude-opus-4-5"
    CLAUDE_OPUS_4_1 = "anthropic/claude-opus-4-1"
    CLAUDE_3_5_SONNET_LATEST = "anthropic/claude-3-5-sonnet-latest"
    CLAUDE_3_5_HAIKU_LATEST = "anthropic/claude-3-5-haiku-latest"
    CLAUDE_3_OPUS_LATEST = "anthropic/claude-3-opus-latest"

    # Google Models
    GEMINI_2_5_PRO = "gemini/gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini/gemini-2.5-flash"
    GEMINI_2_5_FLASH_LITE = "gemini/gemini-2.5-flash-lite"
    GEMINI_3_1_PRO_PREVIEW = "gemini/gemini-3.1-pro-preview"
    GEMINI_3_FLASH_PREVIEW = "gemini/gemini-3-flash-preview"
    GEMINI_3_5_FLASH = "gemini/gemini-3.5-flash"
    GEMINI_3_5_FLASH_LITE = "gemini/gemini-3.5-flash-lite"
    GEMINI_3_8_FLASH = "gemini/gemini-3.8-flash"
    GEMINI_2_0_FLASH_EXP = "gemini/gemini-2.0-flash-exp"
    GEMINI_2_0_FLASH = "gemini/gemini-2.0-flash"
    GEMINI_1_5_PRO = "gemini/gemini-1.5-pro"
    GEMINI_1_5_FLASH = "gemini/gemini-1.5-flash"
    GEMINI_1_5_PRO_LATEST = "gemini/gemini-1.5-pro-latest"
    GEMINI_1_5_FLASH_LATEST = "gemini/gemini-1.5-flash-latest"

    # Deepseek Models
    DEEPSEEK_CHAT = "deepseek/deepseek-chat"
    DEEPSEEK_REASONER = "deepseek/deepseek-reasoner"

    # Ollama Models
    OLLAMA_MISTRAL_SMALL = "ollama/mistral-small:24b"
    OLLAMA_DEEPSEEK_R1 = "ollama/deepseek-r1"
    OLLAMA_PHI4 = "ollama/phi4"
    OLLAMA_LLAMA3_3_70B = "ollama/llama3.3:70b"
    OLLAMA_LLAMA3_2 = "ollama/llama3.2"
    OLLAMA_LLAMA3_2_3B = "ollama/llama3.2:3b"
    OLLAMA_LLAMA3_2_1B = "ollama/llama3.2:1b"
    OLLAMA_LLAMA3_1_8B = "ollama/llama3.1:8b"
    OLLAMA_LLAMA3_1_70B = "ollama/llama3.1:70b"
    OLLAMA_LLAMA3_8B = "ollama/llama3:8b"
    OLLAMA_LLAMA3_70B = "ollama/llama3:70b"
    OLLAMA_GEMMA_3_1B = "ollama/gemma3:1b"
    OLLAMA_GEMMA_3_4B = "ollama/gemma3:4b"
    OLLAMA_GEMMA_3_12B = "ollama/gemma3:12b"
    OLLAMA_GEMMA_3_27B = "ollama/gemma3:27b"
    OLLAMA_GEMMA_2 = "ollama/gemma2"
    OLLAMA_GEMMA_2_2B = "ollama/gemma2:2b"
    OLLAMA_MISTRAL = "ollama/mistral"
    OLLAMA_CODELLAMA = "ollama/codellama"
    OLLAMA_MIXTRAL = "ollama/mixtral-8x7b-instruct-v0.1"

    XAI_GROK_2 = "xai/grok-2-latest"

    # IFM Models (K2 Horizon and Jais 3), served through an OpenAI-compatible endpoint
    IFM_K2_HORIZON_375B_A23B = "ifm/K2-Horizon-375B-A23B"
    IFM_JAIS_3_MOVA_36B_A4B = "ifm/Jais-3-MoVA-36B-A4B"

    @classmethod
    def get_model_info(cls, model_id: str) -> LLMModel | None:
        model_registry = {
            cls.GPT_5_5.value: LLMModel(
                id=cls.GPT_5_5.value,
                provider=LLMProvider.OPENAI,
                name="GPT-5.5",
                constraints=ModelConstraints(
                    max_tokens=128000, max_temperature=2.0
                ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            cls.GPT_5_5_PRO.value: LLMModel(
                id=cls.GPT_5_5_PRO.value,
                provider=LLMProvider.OPENAI,
                name="GPT-5.5 Pro",
                constraints=ModelConstraints(
                    max_tokens=128000, max_temperature=2.0
                ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            cls.GPT_5_4.value: LLMModel(
                id=cls.GPT_5_4.value,
                provider=LLMProvider.OPENAI,
                name="GPT-5.4",
                constraints=ModelConstraints(
                    max_tokens=128000, max_temperature=2.0
                ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            cls.GPT_5_4_MINI.value: LLMModel(
                id=cls.GPT_5_4_MINI.value,
                provider=LLMProvider.OPENAI,
                name="GPT-5.4 Mini",
                constraints=ModelConstraints(
                    max_tokens=128000, max_temperature=2.0
                ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            cls.GPT_5_4_NANO.value: LLMModel(
                id=cls.GPT_5_4_NANO.value,
                provider=LLMProvider.OPENAI,
                name="GPT-5.4 Nano",
                constraints=ModelConstraints(
                    max_tokens=128000, max_temperature=2.0
                ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            cls.GPT_4_1.value: LLMModel(
                id=cls.GPT_4_1.value,
                provider=LLMProvider.OPENAI,
                name="GPT-4.1",
                constraints=ModelConstraints(
                    max_tokens=32768, max_temperature=2.0
                ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            cls.GPT_4_1_MINI.value: LLMModel(
                id=cls.GPT_4_1_MINI.value,
                provider=LLMProvider.OPENAI,
                name="GPT-4.1 Mini",
                constraints=ModelConstraints(
                    max_tokens=32768, max_temperature=2.0
                ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            cls.GPT_4_1_NANO.value: LLMModel(
                id=cls.GPT_4_1_NANO.value,
                provider=LLMProvider.OPENAI,
                name="GPT-4.1 Nano",
                constraints=ModelConstraints(
                    max_tokens=32768, max_temperature=2.0
                ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            cls.O3.value: LLMModel(
                id=cls.O3.value,
                provider=LLMProvider.OPENAI,
                name="O3",
                constraints=ModelConstraints(
                    max_tokens=100000,
                    max_temperature=2.0,
                    supports_max_tokens=False,
                    supports_temperature=False,
                ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            cls.O4_MINI.value: LLMModel(
                id=cls.O4_MINI.value,
                provider=LLMProvider.OPENAI,
                name="O4 Mini",
                constraints=ModelConstraints(
                    max_tokens=100000,
                    max_temperature=2.0,
                    supports_max_tokens=False,
                    supports_temperature=False,
                ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            cls.O3_MINI.value: LLMModel(
                id=cls.O3_MINI.value,
                provider=LLMProvider.OPENAI,
                name="O3 Mini",
                constraints=ModelConstraints(
                    max_tokens=100000,
                    max_temperature=2.0,
                    supports_max_tokens=False,
                    supports_temperature=False,
                ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            cls.O3_MINI_2025_01_31.value: LLMModel(
                id=cls.O3_MINI_2025_01_31.value,
                provider=LLMProvider.OPENAI,
                name="O3 Mini (2025-01-31)",
                constraints=ModelConstraints(
                    max_tokens=100000,
                    max_temperature=2.0,
                    supports_max_tokens=False,
                    supports_temperature=False,
                ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            cls.GPT_4O_MINI.value: LLMModel(
                id=cls.GPT_4O_MINI.value,
                provider=LLMProvider.OPENAI,
                name="GPT-4O Mini",
                constraints=ModelConstraints(
                    max_tokens=16384, max_temperature=2.0
                ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            cls.GPT_4O.value: LLMModel(
                id=cls.GPT_4O.value,
                provider=LLMProvider.OPENAI,
                name="GPT-4O",
                constraints=ModelConstraints(
                    max_tokens=16384, max_temperature=2.0
                ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            cls.GPT_4O_MINI_SEARCH_PREVIEW.value: LLMModel(
                    id=cls.GPT_4O_MINI_SEARCH_PREVIEW.value,
                    provider=LLMProvider.OPENAI,
                    name="GPT-4O Mini Search Preview",
                    constraints=ModelConstraints(
                            max_tokens=16384,
                            supports_temperature=False
                    ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            cls.GPT_4O_SEARCH_PREVIEW.value: LLMModel(
                    id=cls.GPT_4O_SEARCH_PREVIEW.value,
                    provider=LLMProvider.OPENAI,
                    name="GPT-4O Search Preview",
                    constraints=ModelConstraints(
                            max_tokens=16384,
                            supports_temperature=False
                    ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            cls.O1_PREVIEW.value: LLMModel(
                id=cls.O1_PREVIEW.value,
                provider=LLMProvider.OPENAI,
                name="O1 Preview",
                constraints=ModelConstraints(
                    max_tokens=32768,
                    max_temperature=2.0,
                    supports_max_tokens=False,
                    supports_temperature=False,
                ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            cls.O1_MINI.value: LLMModel(
                id=cls.O1_MINI.value,
                provider=LLMProvider.OPENAI,
                name="O1 Mini",
                constraints=ModelConstraints(
                    max_tokens=65536,
                    max_temperature=2.0,
                    supports_max_tokens=False,
                    supports_temperature=False,
                ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            cls.O1.value: LLMModel(
                id=cls.O1.value,
                provider=LLMProvider.OPENAI,
                name="O1",
                constraints=ModelConstraints(
                    max_tokens=100000,
                    max_temperature=2.0,
                    supports_max_tokens=False,
                    supports_temperature=False,
                ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            cls.O1_PRO.value: LLMModel(
                id=cls.O1_PRO.value,
                provider=LLMProvider.OPENAI,
                name="O1 Pro",
                constraints=ModelConstraints(
                    max_tokens=100000,
                    max_temperature=2.0,
                    supports_max_tokens=False,
                    supports_temperature=False,
                    supports_JSON_output=True,
                ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            cls.O1_2024_12_17.value: LLMModel(
                id=cls.O1_2024_12_17.value,
                provider=LLMProvider.OPENAI,
                name="O1 (2024-12-17)",
                constraints=ModelConstraints(
                    max_tokens=100000,
                    max_temperature=2.0,
                    supports_max_tokens=False,
                    supports_temperature=False,
                ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            cls.O1_MINI_2024_09_12.value: LLMModel(
                id=cls.O1_MINI_2024_09_12.value,
                provider=LLMProvider.OPENAI,
                name="O1 Mini (2024-09-12)",
                constraints=ModelConstraints(
                    max_tokens=65536,
                    max_temperature=2.0,
                    supports_max_tokens=False,
                    supports_temperature=False,
                ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            cls.O1_PREVIEW_2024_09_12.value: LLMModel(
                id=cls.O1_PREVIEW_2024_09_12.value,
                provider=LLMProvider.OPENAI,
                name="O1 Preview (2024-09-12)",
                constraints=ModelConstraints(
                    max_tokens=32768,
                    max_temperature=2.0,
                    supports_max_tokens=False,
                    supports_temperature=False,
                ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            cls.CHATGPT_4O_LATEST.value: LLMModel(
                id=cls.CHATGPT_4O_LATEST.value,
                provider=LLMProvider.OPENAI,
                name="ChatGPT-4o Latest (Legacy)",
                constraints=ModelConstraints(
                    max_tokens=4096, max_temperature=2.0
                ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            # Azure OpenAI Models
            cls.AZURE_GPT_4.value: LLMModel(
                id=cls.AZURE_GPT_4.value,
                provider=LLMProvider.AZURE_OPENAI,
                name="Azure GPT-4",
                constraints=ModelConstraints(max_tokens=4096, max_temperature=2.0),
            ),
            cls.AZURE_GPT_35_TURBO.value: LLMModel(
                id=cls.AZURE_GPT_35_TURBO.value,
                provider=LLMProvider.AZURE_OPENAI,
                name="Azure GPT-3.5 Turbo",
                constraints=ModelConstraints(max_tokens=4096, max_temperature=2.0),
            ),
            # Anthropic Models
            cls.CLAUDE_OPUS_4_7.value: LLMModel(
                id=cls.CLAUDE_OPUS_4_7.value,
                provider=LLMProvider.ANTHROPIC,
                name="Claude Opus 4.7",
                constraints=ModelConstraints(
                    max_tokens=128000,
                    max_temperature=1.0,
                    supports_thinking=True,
                    thinking_budget_tokens=1024,
                ).add_mime_categories({MimeCategory.IMAGES, MimeCategory.DOCUMENTS}),
            ),
            cls.CLAUDE_SONNET_4_6.value: LLMModel(
                id=cls.CLAUDE_SONNET_4_6.value,
                provider=LLMProvider.ANTHROPIC,
                name="Claude Sonnet 4.6",
                constraints=ModelConstraints(
                    max_tokens=64000,
                    max_temperature=1.0,
                    supports_thinking=True,
                    thinking_budget_tokens=1024,
                ).add_mime_categories({MimeCategory.IMAGES, MimeCategory.DOCUMENTS}),
            ),
            cls.CLAUDE_HAIKU_4_5.value: LLMModel(
                id=cls.CLAUDE_HAIKU_4_5.value,
                provider=LLMProvider.ANTHROPIC,
                name="Claude Haiku 4.5",
                constraints=ModelConstraints(
                    max_tokens=64000,
                    max_temperature=1.0,
                ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            cls.CLAUDE_OPUS_4_6.value: LLMModel(
                id=cls.CLAUDE_OPUS_4_6.value,
                provider=LLMProvider.ANTHROPIC,
                name="Claude Opus 4.6",
                constraints=ModelConstraints(
                    max_tokens=128000,
                    max_temperature=1.0,
                    supports_thinking=True,
                    thinking_budget_tokens=1024,
                ).add_mime_categories({MimeCategory.IMAGES, MimeCategory.DOCUMENTS}),
            ),
            cls.CLAUDE_SONNET_4_5.value: LLMModel(
                id=cls.CLAUDE_SONNET_4_5.value,
                provider=LLMProvider.ANTHROPIC,
                name="Claude Sonnet 4.5",
                constraints=ModelConstraints(
                    max_tokens=64000,
                    max_temperature=1.0,
                    supports_thinking=True,
                    thinking_budget_tokens=1024,
                ).add_mime_categories({MimeCategory.IMAGES, MimeCategory.DOCUMENTS}),
            ),
            cls.CLAUDE_OPUS_4_5.value: LLMModel(
                id=cls.CLAUDE_OPUS_4_5.value,
                provider=LLMProvider.ANTHROPIC,
                name="Claude Opus 4.5",
                constraints=ModelConstraints(
                    max_tokens=64000,
                    max_temperature=1.0,
                    supports_thinking=True,
                    thinking_budget_tokens=1024,
                ).add_mime_categories({MimeCategory.IMAGES, MimeCategory.DOCUMENTS}),
            ),
            cls.CLAUDE_OPUS_4_1.value: LLMModel(
                id=cls.CLAUDE_OPUS_4_1.value,
                provider=LLMProvider.ANTHROPIC,
                name="Claude Opus 4.1",
                constraints=ModelConstraints(
                    max_tokens=32000,
                    max_temperature=1.0,
                    supports_thinking=True,
                    thinking_budget_tokens=1024,
                ).add_mime_categories({MimeCategory.IMAGES, MimeCategory.DOCUMENTS}),
            ),
            cls.CLAUDE_3_5_SONNET_LATEST.value: LLMModel(
                id=cls.CLAUDE_3_5_SONNET_LATEST.value,
                provider=LLMProvider.ANTHROPIC,
                name="Claude 3.5 Sonnet Latest",
                constraints=ModelConstraints(
                    max_tokens=8192,
                    max_temperature=1.0,
                ).add_mime_categories({MimeCategory.IMAGES, MimeCategory.DOCUMENTS}),
            ),
            cls.CLAUDE_3_5_HAIKU_LATEST.value: LLMModel(
                id=cls.CLAUDE_3_5_HAIKU_LATEST.value,
                provider=LLMProvider.ANTHROPIC,
                name="Claude 3.5 Haiku Latest",
                constraints=ModelConstraints(
                    max_tokens=8192,
                    max_temperature=1.0,
                ),
            ),
            cls.CLAUDE_3_OPUS_LATEST.value: LLMModel(
                id=cls.CLAUDE_3_OPUS_LATEST.value,
                provider=LLMProvider.ANTHROPIC,
                name="Claude 3 Opus Latest",
                constraints=ModelConstraints(
                    max_tokens=4096,
                    max_temperature=1.0,
                ).add_mime_categories({MimeCategory.IMAGES}),
            ),
            # Google Models
            cls.GEMINI_2_5_PRO.value: LLMModel(
                id=cls.GEMINI_2_5_PRO.value,
                provider=LLMProvider.GEMINI,
                name="Gemini 2.5 Pro",
                constraints=ModelConstraints(
                    max_tokens=65536,
                    max_temperature=2.0,
                ).add_mime_categories(
                    {
                        MimeCategory.IMAGES,
                        MimeCategory.AUDIO,
                        MimeCategory.VIDEO,
                        MimeCategory.DOCUMENTS,
                        MimeCategory.TEXT,
                    }
                ),
            ),
            cls.GEMINI_2_5_FLASH.value: LLMModel(
                id=cls.GEMINI_2_5_FLASH.value,
                provider=LLMProvider.GEMINI,
                name="Gemini 2.5 Flash",
                constraints=ModelConstraints(
                    max_tokens=65536,
                    max_temperature=2.0,
                ).add_mime_categories(
                    {
                        MimeCategory.IMAGES,
                        MimeCategory.AUDIO,
                        MimeCategory.VIDEO,
                        MimeCategory.TEXT,
                    }
                ),
            ),
            cls.GEMINI_2_5_FLASH_LITE.value: LLMModel(
                id=cls.GEMINI_2_5_FLASH_LITE.value,
                provider=LLMProvider.GEMINI,
                name="Gemini 2.5 Flash-Lite",
                constraints=ModelConstraints(
                    max_tokens=65536,
                    max_temperature=2.0,
                ).add_mime_categories(
                    {
                        MimeCategory.IMAGES,
                        MimeCategory.AUDIO,
                        MimeCategory.VIDEO,
                        MimeCategory.DOCUMENTS,
                        MimeCategory.TEXT,
                    }
                ),
            ),
            cls.GEMINI_3_1_PRO_PREVIEW.value: LLMModel(
                id=cls.GEMINI_3_1_PRO_PREVIEW.value,
                provider=LLMProvider.GEMINI,
                name="Gemini 3.1 Pro Preview",
                constraints=ModelConstraints(
                    max_tokens=65536,
                    max_temperature=2.0,
                ).add_mime_categories(
                    {
                        MimeCategory.IMAGES,
                        MimeCategory.AUDIO,
                        MimeCategory.VIDEO,
                        MimeCategory.DOCUMENTS,
                        MimeCategory.TEXT,
                    }
                ),
            ),
            cls.GEMINI_3_FLASH_PREVIEW.value: LLMModel(
                id=cls.GEMINI_3_FLASH_PREVIEW.value,
                provider=LLMProvider.GEMINI,
                name="Gemini 3 Flash Preview",
                constraints=ModelConstraints(
                    max_tokens=65536,
                    max_temperature=2.0,
                ).add_mime_categories(
                    {
                        MimeCategory.IMAGES,
                        MimeCategory.AUDIO,
                        MimeCategory.VIDEO,
                        MimeCategory.DOCUMENTS,
                        MimeCategory.TEXT,
                    }
                ),
            ),
            cls.GEMINI_3_8_FLASH.value: LLMModel(
                id=cls.GEMINI_3_8_FLASH.value,
                provider=LLMProvider.GEMINI,
                name="Gemini 3.8 Flash",
                constraints=ModelConstraints(
                    max_tokens=65536,
                    max_temperature=2.0,
                ).add_mime_categories(
                    {
                        MimeCategory.IMAGES,
                        MimeCategory.AUDIO,
                        MimeCategory.VIDEO,
                        MimeCategory.DOCUMENTS,
                        MimeCategory.TEXT,
                    }
                ),
            ),
            cls.GEMINI_3_5_FLASH.value: LLMModel(
                id=cls.GEMINI_3_5_FLASH.value,
                provider=LLMProvider.GEMINI,
                name="Gemini 3.5 Flash",
                constraints=ModelConstraints(
                    max_tokens=65536,
                    max_temperature=2.0,
                ).add_mime_categories(
                    {
                        MimeCategory.IMAGES,
                        MimeCategory.AUDIO,
                        MimeCategory.VIDEO,
                        MimeCategory.DOCUMENTS,
                        MimeCategory.TEXT,
                    }
                ),
            ),
            cls.GEMINI_3_5_FLASH_LITE.value: LLMModel(
                id=cls.GEMINI_3_5_FLASH_LITE.value,
                provider=LLMProvider.GEMINI,
                name="Gemini 3.5 Flash Lite",
                constraints=ModelConstraints(
                    max_tokens=65536,
                    max_temperature=2.0,
                ).add_mime_categories(
                    {
                        MimeCategory.IMAGES,
                        MimeCategory.AUDIO,
                        MimeCategory.VIDEO,
                        MimeCategory.DOCUMENTS,
                        MimeCategory.TEXT,
                    }
                ),
            ),
            cls.GEMINI_1_5_PRO.value: LLMModel(
                id=cls.GEMINI_1_5_PRO.value,
                provider=LLMProvider.GEMINI,
                name="Gemini 1.5 Pro",
                constraints=ModelConstraints(
                    max_tokens=8192,
                    max_temperature=1.0,
                ).add_mime_categories({MimeCategory.IMAGES, MimeCategory.AUDIO}),
            ),
            cls.GEMINI_1_5_FLASH.value: LLMModel(
                id=cls.GEMINI_1_5_FLASH.value,
                provider=LLMProvider.GEMINI,
                name="Gemini 1.5 Flash",
                constraints=ModelConstraints(
                    max_tokens=8192, max_temperature=1.0
                ).add_mime_categories(
                    {
                        MimeCategory.IMAGES,
                        MimeCategory.AUDIO,
                        MimeCategory.VIDEO,
                        MimeCategory.DOCUMENTS,
                        MimeCategory.TEXT,
                    }
                ),
            ),
            cls.GEMINI_1_5_PRO_LATEST.value: LLMModel(
                id=cls.GEMINI_1_5_PRO_LATEST.value,
                provider=LLMProvider.GEMINI,
                name="Gemini 1.5 Pro Latest",
                constraints=ModelConstraints(
                    max_tokens=8192, max_temperature=1.0
                ).add_mime_categories(
                    {
                        MimeCategory.IMAGES,
                        MimeCategory.AUDIO,
                        MimeCategory.VIDEO,
                        MimeCategory.DOCUMENTS,
                        MimeCategory.TEXT,
                    }
                ),
            ),
            cls.GEMINI_1_5_FLASH_LATEST.value: LLMModel(
                id=cls.GEMINI_1_5_FLASH_LATEST.value,
                provider=LLMProvider.GEMINI,
                name="Gemini 1.5 Flash Latest",
                constraints=ModelConstraints(
                    max_tokens=8192, max_temperature=1.0
                ).add_mime_categories(
                    {
                        MimeCategory.IMAGES,
                        MimeCategory.AUDIO,
                        MimeCategory.VIDEO,
                        MimeCategory.DOCUMENTS,
                        MimeCategory.TEXT,
                    }
                ),
            ),
            cls.GEMINI_2_0_FLASH_EXP.value: LLMModel(
                id=cls.GEMINI_2_0_FLASH_EXP.value,
                provider=LLMProvider.GEMINI,
                name="Gemini 2.0 Flash Exp",
                constraints=ModelConstraints(
                    max_tokens=8192, max_temperature=1.0
                ).add_mime_categories(
                    {
                        MimeCategory.IMAGES,
                        MimeCategory.AUDIO,
                        MimeCategory.VIDEO,
                        MimeCategory.DOCUMENTS,
                        MimeCategory.TEXT,
                    }
                ),
            ),
            cls.GEMINI_2_0_FLASH.value: LLMModel(
                id=cls.GEMINI_2_0_FLASH.value,
                provider=LLMProvider.GEMINI,
                name="Gemini 2.0 Flash",
                constraints=ModelConstraints(
                    max_tokens=8192,
                    max_temperature=2.0,
                ).add_mime_categories(
                    {
                        MimeCategory.IMAGES,
                        MimeCategory.AUDIO,
                        MimeCategory.VIDEO,
                        MimeCategory.DOCUMENTS,
                        MimeCategory.TEXT,
                    }
                ),
            ),
            # Deepseek Models
            cls.DEEPSEEK_CHAT.value: LLMModel(
                id=cls.DEEPSEEK_CHAT.value,
                provider=LLMProvider.DEEPSEEK,
                name="Deepseek Chat",
                constraints=ModelConstraints(
                    max_tokens=8192,
                    max_temperature=2.0,
                    supports_JSON_output=False,
                ),
            ),
            cls.DEEPSEEK_REASONER.value: LLMModel(
                id=cls.DEEPSEEK_REASONER.value,
                provider=LLMProvider.DEEPSEEK,
                name="Deepseek Reasoner",
                constraints=ModelConstraints(
                    max_tokens=8192,
                    max_temperature=2.0,
                    supports_JSON_output=False,
                    supports_max_tokens=False,
                ),
            ),
            # Ollama Models
            cls.OLLAMA_PHI4.value: LLMModel(
                id=cls.OLLAMA_PHI4.value,
                provider=LLMProvider.OLLAMA,
                name="Phi 4",
                constraints=ModelConstraints(max_tokens=4096, max_temperature=2.0, supports_JSON_output=False),
            ),
            cls.OLLAMA_LLAMA3_3_70B.value: LLMModel(
                id=cls.OLLAMA_LLAMA3_3_70B.value,
                provider=LLMProvider.OLLAMA,
                name="Llama 3.3 (70B)",
                constraints=ModelConstraints(max_tokens=4096, max_temperature=2.0),
            ),
            cls.OLLAMA_LLAMA3_2.value: LLMModel(
                id=cls.OLLAMA_LLAMA3_2.value,
                provider=LLMProvider.OLLAMA,
                name="Llama 3.2",
                constraints=ModelConstraints(max_tokens=4096, max_temperature=2.0, supports_JSON_output=False),
            ),
            cls.OLLAMA_LLAMA3_2_3B.value: LLMModel(
                id=cls.OLLAMA_LLAMA3_2_3B.value,
                provider=LLMProvider.OLLAMA,
                name="Llama 3.2 (3B)",
                constraints=ModelConstraints(max_tokens=4096, max_temperature=2.0, supports_JSON_output=False),
            ),
            cls.OLLAMA_LLAMA3_2_1B.value: LLMModel(
                id=cls.OLLAMA_LLAMA3_2_1B.value,
                provider=LLMProvider.OLLAMA,
                name="Llama 3.2 (1B)",
                constraints=ModelConstraints(max_tokens=4096, max_temperature=2.0, supports_JSON_output=False),
            ),
            cls.OLLAMA_LLAMA3_1_8B.value: LLMModel(
                id=cls.OLLAMA_LLAMA3_1_8B.value,
                provider=LLMProvider.OLLAMA,
                name="Llama 3.1 (8B)",
                constraints=ModelConstraints(max_tokens=4096, max_temperature=2.0, supports_JSON_output=False),
            ),
            cls.OLLAMA_LLAMA3_1_70B.value: LLMModel(
                id=cls.OLLAMA_LLAMA3_1_70B.value,
                provider=LLMProvider.OLLAMA,
                name="Llama 3.1 (70B)",
                constraints=ModelConstraints(max_tokens=4096, max_temperature=2.0, supports_JSON_output=False),
            ),
            cls.OLLAMA_LLAMA3_8B.value: LLMModel(
                id=cls.OLLAMA_LLAMA3_8B.value,
                provider=LLMProvider.OLLAMA,
                name="Llama 3 (8B)",
                constraints=ModelConstraints(max_tokens=4096, max_temperature=2.0, supports_JSON_output=False),
            ),
            cls.OLLAMA_LLAMA3_70B.value: LLMModel(
                id=cls.OLLAMA_LLAMA3_70B.value,
                provider=LLMProvider.OLLAMA,
                name="Llama 3 (70B)",
                constraints=ModelConstraints(max_tokens=4096, max_temperature=2.0, supports_JSON_output=False),
            ),
            cls.OLLAMA_GEMMA_3_1B.value: LLMModel(
                id=cls.OLLAMA_GEMMA_3_1B.value,
                provider=LLMProvider.OLLAMA,
                name="Gemma 3 (1B)",
                constraints=ModelConstraints(max_tokens=4096, max_temperature=2.0, supports_JSON_output=False),
            ),
            cls.OLLAMA_GEMMA_3_4B.value: LLMModel(
                id=cls.OLLAMA_GEMMA_3_4B.value,
                provider=LLMProvider.OLLAMA,
                name="Gemma 3 (4B)",
                constraints=ModelConstraints(max_tokens=4096, max_temperature=2.0, supports_JSON_output=False),
            ),
            cls.OLLAMA_GEMMA_3_12B.value: LLMModel(
                id=cls.OLLAMA_GEMMA_3_12B.value,
                provider=LLMProvider.OLLAMA,
                name="Gemma 3 (12B)",
                constraints=ModelConstraints(max_tokens=4096, max_temperature=2.0, supports_JSON_output=False),
            ),
            cls.OLLAMA_GEMMA_3_27B.value: LLMModel(
                id=cls.OLLAMA_GEMMA_3_27B.value,
                provider=LLMProvider.OLLAMA,
                name="Gemma 3 (27B)",
                constraints=ModelConstraints(max_tokens=4096, max_temperature=2.0, supports_JSON_output=False),
            ),
            cls.OLLAMA_GEMMA_2.value: LLMModel(
                id=cls.OLLAMA_GEMMA_2.value,
                provider=LLMProvider.OLLAMA,
                name="Gemma 2",
                constraints=ModelConstraints(max_tokens=4096, max_temperature=2.0, supports_JSON_output=False),
            ),
            cls.OLLAMA_GEMMA_2_2B.value: LLMModel(
                id=cls.OLLAMA_GEMMA_2_2B.value,
                provider=LLMProvider.OLLAMA,
                name="Gemma 2 (2B)",
                constraints=ModelConstraints(max_tokens=4096, max_temperature=2.0, supports_JSON_output=False),
            ),
            cls.OLLAMA_MISTRAL.value: LLMModel(
                id=cls.OLLAMA_MISTRAL.value,
                provider=LLMProvider.OLLAMA,
                name="Mistral",
                constraints=ModelConstraints(max_tokens=4096, max_temperature=2.0, supports_JSON_output=False),
            ),
            cls.OLLAMA_CODELLAMA.value: LLMModel(
                id=cls.OLLAMA_CODELLAMA.value,
                provider=LLMProvider.OLLAMA,
                name="CodeLlama",
                constraints=ModelConstraints(max_tokens=4096, max_temperature=2.0, supports_JSON_output=False),
            ),
            cls.OLLAMA_MIXTRAL.value: LLMModel(
                id=cls.OLLAMA_MIXTRAL.value,
                provider=LLMProvider.OLLAMA,
                name="Mixtral 8x7B Instruct",
                constraints=ModelConstraints(max_tokens=4096, max_temperature=2.0, supports_JSON_output=False),
            ),
            cls.OLLAMA_DEEPSEEK_R1.value: LLMModel(
                id=cls.OLLAMA_DEEPSEEK_R1.value,
                provider=LLMProvider.OLLAMA,
                name="Deepseek R1",
                constraints=ModelConstraints(
                    max_tokens=8192,
                    max_temperature=2.0,
                    supports_JSON_output=False,
                    supports_max_tokens=False,
                    supports_reasoning=True,
                ),
            ),
            cls.OLLAMA_MISTRAL_SMALL.value: LLMModel(
                id=cls.OLLAMA_MISTRAL_SMALL.value,
                provider=LLMProvider.OLLAMA,
                name="Mistral Small 24B",
                constraints=ModelConstraints(max_tokens=4096, max_temperature=2.0, supports_JSON_output=False),
            ),
            cls.XAI_GROK_2.value: LLMModel(
                    id=cls.XAI_GROK_2.value,
                    provider=LLMProvider.XAI,
                    name="xAI Grok 2 Latest",
                    constraints=ModelConstraints(
                            max_tokens=131072,
                            max_temperature=1.0,
                    ),
            ),
            cls.IFM_K2_HORIZON_375B_A23B.value: LLMModel(
                id=cls.IFM_K2_HORIZON_375B_A23B.value,
                provider=LLMProvider.IFM,
                name="K2 Horizon 375B-A23B",
                constraints=ModelConstraints(max_tokens=524288, max_temperature=2.0),
            ),
            cls.IFM_JAIS_3_MOVA_36B_A4B.value: LLMModel(
                id=cls.IFM_JAIS_3_MOVA_36B_A4B.value,
                provider=LLMProvider.IFM,
                name="Jais 3 MoVA 36B-A4B",
                constraints=ModelConstraints(max_tokens=524288, max_temperature=2.0),
            ),
        }
        return model_registry.get(model_id)
