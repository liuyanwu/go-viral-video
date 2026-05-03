"""
SRT file parser utility.
Parses SRT subtitle files into structured segments.
"""

import re
from typing import List

from models import SubtitleSegment


def parse_srt_file(srt_path: str) -> List[SubtitleSegment]:
    """
    Parse an SRT file into a list of SubtitleSegments.

    Args:
        srt_path: Path to the .srt file.

    Returns:
        List of parsed subtitle segments.
    """
    with open(srt_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    return parse_srt_content(content)


def parse_srt_content(content: str) -> List[SubtitleSegment]:
    """
    Parse SRT content string into subtitle segments.

    Args:
        content: Raw SRT file content.

    Returns:
        List of parsed subtitle segments.
    """
    segments = []
    # Split by double newline (segment separator)
    blocks = re.split(r"\n\s*\n", content.strip())

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue

        # Line 1: index
        try:
            index = int(lines[0].strip())
        except ValueError:
            continue

        # Line 2: timestamps
        time_match = re.match(
            r"(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})",
            lines[1].strip()
        )
        if not time_match:
            continue

        start_time = time_match.group(1).replace(".", ",")
        end_time = time_match.group(2).replace(".", ",")

        # Lines 3+: text
        text = "\n".join(lines[2:]).strip()
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        segments.append(SubtitleSegment(
            index=index,
            start_time=start_time,
            end_time=end_time,
            text=text,
        ))

    return segments


def segments_to_text(segments: List[SubtitleSegment]) -> str:
    """
    Concatenate subtitle segments into plain text.

    Args:
        segments: List of subtitle segments.

    Returns:
        Concatenated text string.
    """
    return " ".join(seg.text for seg in segments if seg.text.strip())


def segments_to_srt(segments: List[SubtitleSegment]) -> str:
    """
    Convert subtitle segments back to SRT format string.

    Args:
        segments: List of subtitle segments.

    Returns:
        SRT format string.
    """
    lines = []
    for seg in segments:
        lines.append(str(seg.index))
        lines.append(f"{seg.start_time} --> {seg.end_time}")
        lines.append(seg.text)
        lines.append("")
    return "\n".join(lines)
