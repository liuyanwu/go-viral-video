"""
Test suite for pipeline module (mocked).
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import (
    AnalysisResult, VideoInfo, TranscriptResult,
    SubtitleSource, Platform, ContentSummary,
    ViralityAnalysis, ViralityScores, HookType,
    ContentStructure, RewriteResult,
)


def create_mock_result():
    """Create a mock AnalysisResult for testing."""
    return AnalysisResult(
        video=VideoInfo(
            url="https://example.com/video",
            platform=Platform.YOUTUBE,
            video_id="test123",
            title="Test Video",
            author="Test Author",
            duration_seconds=60.0,
        ),
        transcript=TranscriptResult(
            source=SubtitleSource.ASR,
            language="en",
            raw_text="Hello world test",
            cleaned_text="Hello world test",
        ),
        summary=ContentSummary(
            one_sentence="A test video",
            key_points=["Point 1", "Point 2"],
            target_audience="Everyone",
            content_type="tutorial",
        ),
        virality=ViralityAnalysis(
            scores=ViralityScores(
                hook=70, emotion=60, retention=80, cta=50, social_currency=65, overall=65,
            ),
            hook_type=HookType.CURIOSITY,
            viral_potential="medium",
            explanation="Test explanation",
        ),
        structure=ContentStructure(),
        rewrites=RewriteResult(),
        processing_time_seconds=1.5,
    )


def test_mock_result_creation():
    result = create_mock_result()
    assert result.video.platform == Platform.YOUTUBE
    assert result.transcript.source == SubtitleSource.ASR
    assert result.summary is not None
    assert result.virality is not None


def test_result_to_json():
    result = create_mock_result()
    import json
    json_str = result.model_dump_json(exclude_none=True)
    data = json.loads(json_str)
    assert data["video"]["platform"] == "youtube"
    assert data["transcript"]["source"] == "asr"


def test_result_to_markdown():
    result = create_mock_result()
    md = result.to_markdown()
    assert "# 📊 Video Viral Analysis Report" in md
    assert "Test Video" in md
    assert "65/100" in md


def test_pipeline_early_exit_on_no_transcript():
    """Test that pipeline exits early when no transcript is available."""
    from pipeline import Pipeline
    from config import reset_config

    reset_config()

    with patch.object(Pipeline, "__init__", lambda self: None):
        pipeline = Pipeline()
        pipeline.services = MagicMock()
        pipeline.services.cache = MagicMock()
        pipeline.services.cache.get.return_value = None
        pipeline.config = MagicMock()
        pipeline.config.max_transcript_chars = 4000

        pipeline.downloader = MagicMock()
        pipeline.downloader.download.return_value = VideoInfo(
            url="test",
            platform=Platform.LOCAL,
            local_path="test.mp4",
        )

        pipeline.subtitle_extractor = MagicMock()
        pipeline.subtitle_extractor.extract.return_value = TranscriptResult(
            source=SubtitleSource.ASR,
            raw_text="",
        )

        pipeline.asr_engine = MagicMock()
        pipeline.asr_engine.transcribe.return_value = TranscriptResult(
            source=SubtitleSource.ASR,
            raw_text="",
        )

        result = pipeline.run(url_or_path="test.mp4", skip_analysis=False)
        assert result.transcript.source == SubtitleSource.ASR
        assert result.summary is None
        assert result.virality is None
