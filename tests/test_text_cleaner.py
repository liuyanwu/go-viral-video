"""
Test suite for text cleaner module.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import TranscriptResult, SubtitleSegment, SubtitleSource
from modules.text_cleaner import TextCleaner


def test_remove_noise_markers():
    cleaner = TextCleaner()
    text = "Hello [音乐] world [Applause] test [掌声]"
    result = cleaner._clean_text(text)
    assert "[音乐]" not in result
    assert "[Applause]" not in result
    assert "[掌声]" not in result


def test_remove_timestamps():
    cleaner = TextCleaner()
    text = "00:00:01,000 --> 00:00:02,000\nHello world"
    result = cleaner._remove_timestamps(text)
    assert "00:00:01" not in result
    assert "Hello world" in result


def test_merge_fragments():
    cleaner = TextCleaner()
    text = "Hello\nworld\ntest"
    result = cleaner._merge_fragments(text)
    assert result == "Hello world test"


def test_deduplicate_lines():
    cleaner = TextCleaner()
    text = "Hello\nHello\nWorld"
    result = cleaner._deduplicate_lines(text)
    assert result == "Hello\nWorld"


def test_detect_language_chinese():
    cleaner = TextCleaner()
    assert cleaner._detect_language("你好世界") == "zh"
    assert cleaner._detect_language("Hello 你好") == "zh"


def test_detect_language_english():
    cleaner = TextCleaner()
    assert cleaner._detect_language("Hello world") == "en"


def test_clean_full_pipeline():
    cleaner = TextCleaner()
    transcript = TranscriptResult(
        source=SubtitleSource.ASR,
        language="auto",
        raw_text="Hello [音乐] world 你好",
    )
    result = cleaner.clean(transcript)
    assert "[音乐]" not in result.cleaned_text
    assert result.language in ("zh", "en")
