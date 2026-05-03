"""
Test suite for SRT parser module.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.srt_parser import parse_srt_file, parse_srt_content, segments_to_text, segments_to_srt


def test_parse_srt_content():
    srt_content = """1
00:00:01,000 --> 00:00:02,000
Hello world

2
00:00:03,000 --> 00:00:04,000
Test subtitle
"""
    segments = parse_srt_content(srt_content)
    assert len(segments) == 2
    assert segments[0].text == "Hello world"
    assert segments[1].text == "Test subtitle"
    assert segments[0].start_time == "00:00:01,000"


def test_parse_srt_content_with_html():
    srt_content = """1
00:00:01,000 --> 00:00:02,000
Hello <b>world</b>
"""
    segments = parse_srt_content(srt_content)
    assert len(segments) == 1
    assert "<b>" not in segments[0].text
    assert segments[0].text == "Hello world"


SRT_CONTENT = """1
00:00:01,000 --> 00:00:02,000
Hello World

2
00:00:03,000 --> 00:00:04,000
This is a test
"""


def test_parse_srt_file(tmp_path):
    srt_file = tmp_path / "test.srt"
    srt_file.write_text(SRT_CONTENT, encoding="utf-8")
    segments = parse_srt_file(str(srt_file))
    assert len(segments) == 2
    assert segments[0].text == "Hello World"
    assert segments[1].text == "This is a test"


def test_segments_to_text():
    from models import SubtitleSegment
    segments = [
        SubtitleSegment(index=1, text="Hello"),
        SubtitleSegment(index=2, text="World"),
    ]
    result = segments_to_text(segments)
    assert result == "Hello World"


def test_segments_to_srt():
    from models import SubtitleSegment
    segments = [
        SubtitleSegment(
            index=1,
            start_time="00:00:01,000",
            end_time="00:00:02,000",
            text="Hello",
        ),
    ]
    result = segments_to_srt(segments)
    assert "00:00:01,000 --> 00:00:02,000" in result
    assert "Hello" in result
