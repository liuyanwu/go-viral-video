"""Edge case tests for robustness."""
import pytest
from models import TranscriptResult, SubtitleSource

def test_empty_transcript():
    t = TranscriptResult(source=SubtitleSource.ASR, raw_text="", cleaned_text="")
    assert len(t.raw_text) == 0

def test_very_long_transcript():
    long_text = "测试" * 100000  # 200k chars
    t = TranscriptResult(source=SubtitleSource.ASR, raw_text=long_text, cleaned_text=long_text)
    assert len(t.raw_text) == 200000

def test_transcript_with_special_chars():
    special = "Hello\nWorld\t测试\n\n\n中文"
    t = TranscriptResult(source=SubtitleSource.ASR, raw_text=special, cleaned_text=special)
    assert t.raw_text == special

def test_cache_ttl_expiration():
    import tempfile
    import time
    from pathlib import Path
    from cache import ContentCache
    from models import AnalysisResult, VideoInfo, Platform
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ContentCache(Path(tmpdir), ttl_hours=0)  # 0 hour TTL = immediate expiration
        result = AnalysisResult(
            video=VideoInfo(url="http://test.com", platform=Platform.UNKNOWN),
            transcript=TranscriptResult(source=SubtitleSource.MANUAL),
        )
        cache.put("http://test.com", result)
        time.sleep(1)  # Wait for expiration
        cached = cache.get("http://test.com")
        assert cached is None
