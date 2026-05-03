"""
Test suite for config module.
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import load_config, reset_config, get_config


def setup_function():
    reset_config()


def teardown_function():
    reset_config()


def test_load_config_defaults(tmp_path):
    for key in ["LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL", "ASR_ENGINE"]:
        os.environ.pop(key, None)
    
    config = load_config(env_path="/nonexistent/.env")
    assert config.llm.base_url == "https://api.openai.com/v1"
    assert config.llm.model == "gpt-4o-mini"
    assert config.asr.engine == "funasr"
    assert config.asr.mode == "fast"
    assert config.default_language == "auto"


def test_load_config_with_overrides(tmp_path):
    os.environ.pop("LLM_BASE_URL", None)
    os.environ.pop("LLM_API_KEY", None)
    os.environ.pop("LLM_MODEL", None)
    
    config = load_config(
        env_path="/nonexistent/.env",
        overrides={"OUTPUT_DIR": "./test-output"}
    )
    assert str(config.output_dir).endswith("test-output")


def test_load_config_from_env_file(tmp_path):
    for key in ["LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"]:
        os.environ.pop(key, None)
    
    env_file = tmp_path / "test.env"
    env_file.write_text("LLM_MODEL=test-model\nLLM_BASE_URL=http://test.com\n")
    
    config = load_config(env_path=str(env_file))
    assert config.llm.model == "test-model"


def test_get_config_singleton():
    reset_config()
    c1 = get_config()
    c2 = get_config()
    assert c1 is c2


def test_reset_config():
    c1 = get_config()
    reset_config()
    c2 = get_config()
    assert c1 is not c2
