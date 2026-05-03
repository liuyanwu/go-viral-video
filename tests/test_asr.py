"""Tests for ASR module."""
import pytest
from modules.asr import ASREngine
from exceptions import ASRError

def test_asr_engine_initialization():
    engine = ASREngine()
    assert engine.config is not None

def test_asr_error_handling():
    with pytest.raises(ASRError) as exc_info:
        raise ASRError("Test error", code=3001, context={"engine": "test"})
    assert exc_info.value.code == 3001
    assert "3001" in str(exc_info.value)
