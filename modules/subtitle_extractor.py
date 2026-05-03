"""
Subtitle extraction module.
4-tier priority: embedded → platform (yt-dlp) → OCR → ASR fallback.
"""

import subprocess
import shutil
import json
import re
from pathlib import Path
from typing import Optional, List

from models import TranscriptResult, SubtitleSegment, SubtitleSource
from utils.srt_parser import parse_srt_file, segments_to_text
from utils.logger import setup_logger

logger = setup_logger("SubtitleExtractor")


class SubtitleExtractor:
    """
    Multi-tier subtitle extraction.

    Priority:
    1. Embedded subtitles (ffmpeg extract)
    2. Platform subtitles (yt-dlp --write-sub)
    3. ASR fallback (handled by pipeline)
    """

    def extract(self, video_path: str, url: str = "") -> TranscriptResult:
        """
        Attempt to extract subtitles from video.

        Args:
            video_path: Path to the video file.
            url: Original URL (for yt-dlp platform subs).

        Returns:
            TranscriptResult (may be empty if no subs found).
        """
        # L1: Embedded subtitles
        logger.info("[L1] Checking for embedded subtitles...")
        result = self._extract_embedded(video_path)
        if result:
            logger.info("[L1] ✅ Embedded subtitles found")
            return result

        # L2: Platform subtitles via yt-dlp
        if url:
            logger.info("[L2] Trying platform subtitles via yt-dlp...")
            result = self._extract_platform(url, video_path)
            if result:
                logger.info("[L2] ✅ Platform subtitles found")
                return result

        # L3/L4: Return empty — ASR will be triggered by pipeline
        logger.info("No subtitles found, ASR fallback needed")
        return TranscriptResult(source=SubtitleSource.ASR, raw_text="")

    # ──────── L1: Embedded ────────

    def _extract_embedded(self, video_path: str) -> Optional[TranscriptResult]:
        """Extract embedded subtitle streams via ffmpeg."""
        if not shutil.which("ffprobe"):
            return None

        # Check for subtitle streams
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json",
                 "-show_streams", "-select_streams", "s", video_path],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode != 0:
                return None

            streams = json.loads(result.stdout).get("streams", [])
            if not streams:
                return None

            # Extract first subtitle stream
            srt_path = Path(video_path).with_suffix(".srt")
            extract_result = subprocess.run(
                ["ffmpeg", "-y", "-i", video_path,
                 "-map", "0:s:0", str(srt_path)],
                capture_output=True, text=True, timeout=30,
            )

            if extract_result.returncode == 0 and srt_path.exists():
                segments = parse_srt_file(str(srt_path))
                if segments:
                    raw_text = segments_to_text(segments)
                    return TranscriptResult(
                        source=SubtitleSource.EMBEDDED,
                        raw_segments=segments,
                        raw_text=raw_text,
                        srt_path=str(srt_path),
                    )
        except Exception as e:
            logger.debug(f"Embedded extraction failed: {e}")

        return None

    # ──────── L2: Platform (yt-dlp) ────────

    def _extract_platform(self, url: str, video_path: str) -> Optional[TranscriptResult]:
        """Download platform subtitles using yt-dlp."""
        if not shutil.which("yt-dlp"):
            return None

        output_dir = Path(video_path).parent
        sub_prefix = Path(video_path).stem

        cmd = [
            "yt-dlp",
            "--skip-download",
            "--write-sub",
            "--write-auto-sub",
            "--sub-lang", "zh,en,zh-Hans",
            "--sub-format", "srt/vtt/best",
            "--convert-subs", "srt",
            "-o", str(output_dir / f"{sub_prefix}.%(ext)s"),
            url,
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60,
                encoding="utf-8", errors="replace",
            )

            # Find downloaded subtitle files
            for srt_file in output_dir.glob(f"{sub_prefix}*.srt"):
                segments = parse_srt_file(str(srt_file))
                if segments:
                    raw_text = segments_to_text(segments)
                    # Detect language from filename
                    lang = "auto"
                    lang_match = re.search(r"\.([a-z]{2}(?:-[A-Za-z]+)?)\.", srt_file.name)
                    if lang_match:
                        lang = lang_match.group(1)

                    return TranscriptResult(
                        source=SubtitleSource.PLATFORM,
                        language=lang,
                        raw_segments=segments,
                        raw_text=raw_text,
                        srt_path=str(srt_file),
                    )
        except Exception as e:
            logger.debug(f"Platform subtitle extraction failed: {e}")

        return None
