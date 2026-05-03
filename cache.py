"""
Content caching module for analysis results.

Provides a file-based cache with TTL support to avoid re-processing
the same URLs. Cache entries are stored as JSON files keyed by SHA-256
hash of the input URL.

Usage:
    from cache import ContentCache
    from pathlib import Path
    
    cache = ContentCache(cache_dir=Path("./output/.cache"), ttl_hours=24)
    cached = cache.get("https://example.com/video")
    if cached is None:
        result = run_analysis()
        cache.put("https://example.com/video", result)
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Optional, Any
from models import AnalysisResult


class ContentCache:
    def __init__(self, cache_dir: Path, ttl_hours: int = 24):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_hours * 3600

    def _get_key(self, url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()

    def get(self, url: str) -> Optional[AnalysisResult]:
        key = self._get_key(url)
        cache_file = self.cache_dir / f"{key}.json"
        if not cache_file.exists():
            return None
        meta_file = self.cache_dir / f"{key}.meta"
        if meta_file.exists():
            meta = json.loads(meta_file.read_text())
            if time.time() - meta.get("timestamp", 0) > self.ttl_seconds:
                return None
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            return AnalysisResult.model_validate(data)
        except Exception:
            return None

    def put(self, url: str, result: AnalysisResult):
        key = self._get_key(url)
        cache_file = self.cache_dir / f"{key}.json"
        meta_file = self.cache_dir / f"{key}.meta"
        cache_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        meta_file.write_text(json.dumps({"timestamp": time.time(), "url": url}))

    def clear(self):
        for f in self.cache_dir.glob("*.json"):
            f.unlink()
        for f in self.cache_dir.glob("*.meta"):
            f.unlink()

    def stats(self) -> dict:
        files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in files)
        return {"count": len(files), "size_bytes": total_size}
