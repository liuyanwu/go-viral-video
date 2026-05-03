"""
Long video chunk processor for memory-efficient processing.
Splits audio/text into manageable chunks with overlap handling.
"""

import subprocess
import shutil
from pathlib import Path
from typing import List, Optional
from utils.logger import setup_logger

logger = setup_logger("ChunkProcessor")

class ChunkProcessor:
    """Split long videos/audio into chunks for efficient processing."""
    
    def __init__(self, chunk_duration_seconds: int = 300, overlap_seconds: int = 5):
        self.chunk_duration = chunk_duration_seconds
        self.overlap = overlap_seconds
    
    def split_audio(self, audio_path: str, output_dir: Path) -> List[str]:
        """Split audio file into chunks with overlap."""
        if not shutil.which("ffmpeg"):
            raise RuntimeError("ffmpeg not found")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        chunk_pattern = str(output_dir / "chunk_%03d.wav")
        
        cmd = [
            "ffmpeg", "-y", "-i", audio_path,
            "-f", "segment",
            "-segment_time", str(self.chunk_duration),
            "-c", "copy",
            "-reset_timestamps", "1",
            chunk_pattern,
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            logger.warning(f"FFmpeg split failed: {result.stderr[:200]}")
            return [audio_path]  # Fallback to single chunk
        
        chunks = sorted(output_dir.glob("chunk_*.wav"))
        return [str(c) for c in chunks]
    
    def merge_text(self, chunks: List[str], overlap_chars: int = 50) -> str:
        """Merge text chunks, removing duplicate overlap regions."""
        if not chunks:
            return ""
        if len(chunks) == 1:
            return chunks[0]
        
        merged = chunks[0]
        for i in range(1, len(chunks)):
            prev_end = merged[-overlap_chars:] if len(merged) > overlap_chars else merged
            curr = chunks[i]
            # Find overlap and skip duplicate
            overlap_pos = curr.find(prev_end[-20:]) if len(prev_end) >= 20 else -1
            if overlap_pos >= 0:
                merged += curr[overlap_pos + len(prev_end[-20:]):]
            else:
                merged += "\n" + curr
        return merged
    
    def split_text_by_tokens(self, text: str, max_tokens: int = 30000) -> List[str]:
        """Split text into chunks by approximate token count (1 token ~ 1.5 chars for Chinese)."""
        max_chars = int(max_tokens * 1.5)
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        start = 0
        while start < len(text):
            end = start + max_chars
            if end >= len(text):
                chunks.append(text[start:])
                break
            # Find sentence boundary
            boundary = text.rfind("\n", start + max_chars // 2, end)
            if boundary == -1:
                boundary = text.rfind("。", start + max_chars // 2, end)
            if boundary == -1:
                boundary = end
            
            chunks.append(text[start:boundary])
            start = boundary
        return chunks
