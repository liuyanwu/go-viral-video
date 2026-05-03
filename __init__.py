"""
Video Viral Analyzer & Rewriter.

A multi-platform video analysis pipeline that downloads videos,
extracts transcripts, scores virality, and rewrites content.

Dual-mode:
- AI Skill: from skill import run_skill, analyze_video
- CLI Tool: python main.py <URL>
"""

__version__ = "2.0.0"
__author__ = "GoViralVideo Team"

# Public API — importable from package root
from skill import (
    run_skill,
    analyze_video,
    download_video,
    extract_transcript,
    score_virality,
)

from exceptions import (
    GoViralVideoError,
    DownloadError,
    ASRError,
    LLMError,
    ConfigurationError,
)

__all__ = [
    "run_skill",
    "analyze_video",
    "download_video",
    "extract_transcript",
    "score_virality",
    "GoViralVideoError",
    "DownloadError",
    "ASRError",
    "LLMError",
    "ConfigurationError",
]
