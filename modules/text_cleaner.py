"""
Text cleaning and normalization module.
Cleans raw subtitle/transcript text for analysis.
"""

import re
from typing import List

from models import TranscriptResult
from utils.logger import setup_logger

logger = setup_logger("TextCleaner")

# Noise markers to remove
NOISE_MARKERS = [
    r"\[音乐\]", r"\[掌声\]", r"\[笑声\]", r"\[Music\]",
    r"\[Applause\]", r"\[Laughter\]", r"\(音乐\)", r"\(掌声\)",
    r"♪+", r"♫+", r"🎵+", r"🎶+",
]

# Compile noise pattern
NOISE_PATTERN = re.compile("|".join(NOISE_MARKERS), re.IGNORECASE)


class TextCleaner:
    """Clean and normalize transcript text."""

    def clean(self, transcript: TranscriptResult) -> TranscriptResult:
        """
        Clean transcript text and update the result.

        Args:
            transcript: Raw transcript result.

        Returns:
            Updated TranscriptResult with cleaned_text.
        """
        raw = transcript.raw_text
        if not raw:
            raw = " ".join(seg.text for seg in transcript.raw_segments)

        cleaned = self._clean_text(raw)
        transcript.cleaned_text = cleaned

        # Detect language if auto
        if transcript.language == "auto":
            transcript.language = self._detect_language(cleaned)

        logger.info(
            f"Cleaned text: {len(raw)} → {len(cleaned)} chars, "
            f"lang={transcript.language}"
        )
        return transcript

    def _clean_text(self, text: str) -> str:
        """Apply all cleaning steps."""
        text = self._remove_noise_markers(text)
        text = self._remove_timestamps(text)
        text = self._merge_fragments(text)
        text = self._deduplicate_lines(text)
        text = self._normalize_punctuation(text)
        text = self._normalize_whitespace(text)
        return text.strip()

    @staticmethod
    def _remove_noise_markers(text: str) -> str:
        """Remove [音乐], [掌声], ♪, etc."""
        return NOISE_PATTERN.sub("", text)

    @staticmethod
    def _remove_timestamps(text: str) -> str:
        """Remove SRT-style timestamps if any leaked through."""
        # Remove "00:00:00,000 --> 00:00:00,000" patterns
        text = re.sub(
            r"\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}",
            "", text
        )
        # Remove sequence numbers on their own line
        text = re.sub(r"^\d+\s*$", "", text, flags=re.MULTILINE)
        return text

    @staticmethod
    def _merge_fragments(text: str) -> str:
        """Merge fragmented subtitle lines into sentences."""
        # Replace single newlines (not double) with space
        text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
        return text

    @staticmethod
    def _deduplicate_lines(text: str) -> str:
        """Remove consecutive duplicate lines (common in OCR)."""
        lines = text.split("\n")
        deduped = []
        prev = None
        for line in lines:
            stripped = line.strip()
            if stripped and stripped != prev:
                deduped.append(stripped)
                prev = stripped
            elif not stripped and prev != "":
                deduped.append("")
                prev = ""
        return "\n".join(deduped)

    @staticmethod
    def _normalize_punctuation(text: str) -> str:
        """Normalize common punctuation issues."""
        # Detect if primarily Chinese
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        total_chars = len(text.replace(" ", ""))

        if total_chars > 0 and chinese_chars / total_chars > 0.3:
            # Chinese text: normalize to full-width punctuation
            replacements = {
                ",": "，", ".": "。", "!": "！", "?": "？",
                ":": "：", ";": "；", "(": "（", ")": "）",
            }
            for half, full in replacements.items():
                # Only replace if surrounded by Chinese characters
                text = re.sub(
                    f"(?<=[\u4e00-\u9fff]){re.escape(half)}(?=[\u4e00-\u9fff])",
                    full, text
                )
        return text

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """Normalize excessive whitespace."""
        text = re.sub(r"[ \t]+", " ", text)           # Multiple spaces
        text = re.sub(r"\n{3,}", "\n\n", text)        # 3+ newlines
        return text

    @staticmethod
    def _detect_language(text: str) -> str:
        """Simple language detection based on character ratios."""
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        total_chars = len(text.strip())
        if total_chars == 0:
            return "en"
        chinese_ratio = chinese_chars / total_chars
        return "zh" if chinese_ratio > 0.15 else "en"
