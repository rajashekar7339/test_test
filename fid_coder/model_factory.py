"""Model factory — GitHub Copilot only.

Models are registered by the ``copilot_auth`` plugin into
``~/.fid_coder/copilot_models.json`` after ``/copilot-login``.
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
from typing import Any, Dict

from pydantic_ai.models.openai import OpenAIChatModelSettings
from pydantic_ai.settings import ModelSettings

from . import callbacks
from .config import get_value, get_yolo_mode

logger = logging.getLogger(__name__)

# Registry for custom model provider classes from plugins
_CUSTOM_MODEL_PROVIDERS: Dict[str, type] = {}


def _load_plugin_model_providers() -> None:
    """Load custom model providers from plugins."""
    global _CUSTOM_MODEL_PROVIDERS
    try:
        from fid_coder.callbacks import on_register_model_providers

        results = on_register_model_providers()
        for result in results:
            if isinstance(result, dict):
                _CUSTOM_MODEL_PROVIDERS.update(result)
    except Exception as e:
        logger.warning("Failed to load plugin model providers: %s", e)


_load_plugin_model_providers()


def get_api_key(env_var_name: str) -> str | None:
    """Get an API key from config first, then fall back to environment."""
    config_value = get_value(env_var_name.lower())
    if config_value:
        return config_value
    return os.environ.get(env_var_name)


def make_model_settings(
    model_name: str, max_tokens: int | None = None
) -> ModelSettings:
    """Create ModelSettings for a Copilot model."""
    from fid_coder.config import get_effective_model_settings

    model_settings_dict: dict = {}
    model_config: dict[str, Any] = {}

    if max_tokens is None:
        try:
            models_config = ModelFactory.load_config()
            model_config = models_config.get(model_name, {})
            context_length = model_config.get("context_length", 128000)
        except Exception:
            context_length = 128000
        max_tokens = max(2048, min(int(0.15 * context_length), 65536))
    else:
        try:
            model_config = ModelFactory.load_config().get(model_name, {})
        except Exception:
            model_config = {}

    model_settings_dict["max_tokens"] = max_tokens
    effective_settings = get_effective_model_settings(model_name)
    model_settings_dict.update(effective_settings)

    if not get_yolo_mode():
        model_settings_dict["parallel_tool_calls"] = False

    model_type = model_config.get("type")
    is_copilot = model_type == "copilot"
    underlying = model_config.get("name", "").lower() if is_copilot else ""

    if is_copilot and underlying.startswith("claude-"):
        from fid_coder.model_utils import get_default_extended_thinking

        default_thinking = get_default_extended_thinking(underlying)
        extended_thinking = effective_settings.get(
            "extended_thinking", default_thinking
        )
        if extended_thinking is True:
            extended_thinking = "enabled"
        elif extended_thinking is False:
            extended_thinking = "off"

        if extended_thinking in ("enabled", "adaptive"):
            from fid_coder.config import model_supports_setting

            if model_supports_setting(model_name, "effort"):
                effort = effective_settings.get("effort", "high")
                model_settings_dict["openai_reasoning_effort"] = effort

        for key in ("extended_thinking", "budget_tokens", "interleaved_thinking"):
            model_settings_dict.pop(key, None)

        return OpenAIChatModelSettings(**model_settings_dict)

    if is_copilot and (
        underlying.startswith("gpt-")
        or underlying.startswith("o3")
        or underlying.startswith("o4")
    ):
        return OpenAIChatModelSettings(**model_settings_dict)

    return ModelSettings(**model_settings_dict)


class ModelFactory:
    """Factory for creating GitHub Copilot models."""

    @staticmethod
    def load_config() -> Dict[str, Any]:
        load_model_config_callbacks = callbacks.get_callbacks("load_model_config")
        if load_model_config_callbacks:
            if len(load_model_config_callbacks) > 1:
                logging.getLogger(__name__).warning(
                    "Multiple load_model_config callbacks registered, using the first"
                )
            config = callbacks.on_load_model_config()[0]
        else:
            bundled_models = pathlib.Path(__file__).parent / "models.json"
            with open(bundled_models, "r") as f:
                config = json.load(f)

        from fid_coder.config import COPILOT_MODELS_FILE

        copilot_path = pathlib.Path(COPILOT_MODELS_FILE)
        if copilot_path.exists():
            try:
                with open(copilot_path, "r") as f:
                    config.update(json.load(f))
            except Exception as exc:
                logging.getLogger(__name__).warning(
                    "Failed to load Copilot models from %s: %s", copilot_path, exc
                )

        try:
            from fid_coder.callbacks import on_load_models_config

            for result in on_load_models_config():
                if isinstance(result, dict):
                    config.update(result)
        except Exception as exc:
            logging.getLogger(__name__).debug(
                "Failed to load plugin models config: %s", exc
            )

        return config

    @staticmethod
    def get_model(model_name: str, config: Dict[str, Any]) -> Any:
        """Return a configured model instance (Copilot via plugin handler)."""
        model_config = config.get(model_name)
        if not model_config:
            raise ValueError(f"Model '{model_name}' not found in configuration.")

        model_type = model_config.get("type")

        if model_type in _CUSTOM_MODEL_PROVIDERS:
            provider_class = _CUSTOM_MODEL_PROVIDERS[model_type]
            try:
                return provider_class(
                    model_name=model_name, model_config=model_config, config=config
                )
            except Exception as e:
                logger.error("Custom model provider '%s' failed: %s", model_type, e)
                return None

        registered_handlers = callbacks.on_register_model_types()
        for handler_info in registered_handlers:
            handlers = (
                handler_info
                if isinstance(handler_info, list)
                else ([handler_info] if handler_info else [])
            )
            for handler_entry in handlers:
                if not isinstance(handler_entry, dict):
                    continue
                if handler_entry.get("type") != model_type:
                    continue
                handler = handler_entry.get("handler")
                if callable(handler):
                    try:
                        return handler(model_name, model_config, config)
                    except Exception as e:
                        logger.error(
                            "Plugin handler for model type '%s' failed: %s",
                            model_type,
                            e,
                        )
                        return None

        raise ValueError(
            f"Unsupported model type: {model_type}. "
            "Fid Coder uses GitHub Copilot only — run /copilot-login."
        )
