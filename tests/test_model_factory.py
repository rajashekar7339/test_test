"""Tests for the Copilot-only model factory."""

from unittest.mock import patch

import pytest

from fid_coder.model_factory import ModelFactory, get_api_key, make_model_settings


def test_get_api_key_from_env(monkeypatch):
    monkeypatch.setenv("TEST_API_KEY", "secret")
    with patch("fid_coder.model_factory.get_value", return_value=None):
        assert get_api_key("TEST_API_KEY") == "secret"


def test_get_api_key_prefers_config(monkeypatch):
    monkeypatch.setenv("TEST_API_KEY", "env-secret")
    with patch("fid_coder.model_factory.get_value", return_value="cfg-secret"):
        assert get_api_key("TEST_API_KEY") == "cfg-secret"


def test_load_config_merges_copilot_models(tmp_path, monkeypatch):
    copilot_file = tmp_path / "copilot_models.json"
    copilot_file.write_text(
        '{"copilot-gpt-4o": {"type": "copilot", "name": "gpt-4o", "context_length": 128000}}'
    )
    monkeypatch.setattr("fid_coder.config.COPILOT_MODELS_FILE", str(copilot_file))
    with patch("fid_coder.callbacks.get_callbacks", return_value=[]):
        config = ModelFactory.load_config()
    assert "copilot-gpt-4o" in config
    assert config["copilot-gpt-4o"]["type"] == "copilot"


def test_get_model_missing_raises():
    with pytest.raises(ValueError, match="not found"):
        ModelFactory.get_model("nope", {})


def test_get_model_unsupported_type():
    with pytest.raises(ValueError, match="Unsupported model type"):
        ModelFactory.get_model("x", {"x": {"type": "openai", "name": "gpt-4o"}})


def test_make_model_settings_copilot_gpt():
    fake_config = {
        "copilot-gpt-4o": {
            "type": "copilot",
            "name": "gpt-4o",
            "context_length": 128000,
        }
    }
    with patch.object(ModelFactory, "load_config", return_value=fake_config):
        with patch("fid_coder.config.get_effective_model_settings", return_value={}):
            with patch("fid_coder.model_factory.get_yolo_mode", return_value=True):
                settings = make_model_settings("copilot-gpt-4o")
                assert settings.get("max_tokens") is not None
