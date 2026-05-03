"""
Twitter/X web crawler module using yt-dlp for metadata extraction.
Handles both video tweets and image/text tweets.
"""

import json
import subprocess
import shutil
import sys
import re
from typing import Optional, Dict, Any, List

from utils.logger import setup_logger
from utils.rate_limiter import RateLimiter

logger = setup_logger("TwitterCrawler")


def _get_ytdlp_cmd() -> Optional[list]:
    """Find yt-dlp command (CLI or Python module fallback)."""
    if shutil.which("yt-dlp"):
        return ["yt-dlp"]
    try:
        subprocess.run(
            [sys.executable, "-m", "yt_dlp", "--version"],
            capture_output=True, timeout=10,
        )
        return [sys.executable, "-m", "yt_dlp"]
    except Exception:
        return None


class TwitterWebCrawler:
    """Twitter/X web crawler using yt-dlp for metadata extraction."""

    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy
        self._rate_limiter = RateLimiter(max_per_second=0.5, jitter_range=0.3)

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def extract_tweet_id(self, url: str) -> Optional[str]:
        """Extract tweet ID from URL."""
        match = re.search(r"(?:twitter|x)\.com/[^/]+/status/(\d+)", url)
        if match:
            return match.group(1)
        return None

    def fetch_tweet_data(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch tweet metadata using yt-dlp --dump-json (no download)."""
        ytdlp_cmd = _get_ytdlp_cmd()
        if not ytdlp_cmd:
            logger.error("yt-dlp not found")
            return None

        self._rate_limiter.acquire_sync()

        cmd = ytdlp_cmd + [
            "--dump-json",
            "--no-download",
            "--no-warnings",
        ]
        if self.proxy:
            cmd.extend(["--proxy", self.proxy])
        cmd.append(url)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout.strip())
            else:
                logger.error(f"yt-dlp failed: {result.stderr[:500]}")
                return None
        except subprocess.TimeoutExpired:
            logger.error("yt-dlp --dump-json timed out (60s)")
            return None
        except Exception as e:
            logger.error(f"Error fetching tweet data: {e}")
            return None

    def extract_text_content(self, tweet_data: Dict[str, Any]) -> str:
        """Extract text content from tweet data."""
        parts = []
        title = tweet_data.get("title", "").strip()
        desc = tweet_data.get("description", "").strip()

        if title:
            parts.append(title)
        if desc and desc != title:
            parts.append(desc)

        return "\n\n".join(parts)

    def extract_image_urls(self, tweet_data: Dict[str, Any]) -> List[str]:
        """Extract image URLs from tweet thumbnails (excluding avatars)."""
        urls = []
        thumbnails = tweet_data.get("thumbnails", [])
        if not thumbnails and tweet_data.get("thumbnail"):
            thumbnails = [{"url": tweet_data["thumbnail"]}]

        for thumb in thumbnails:
            url = thumb.get("url", "")
            if url and url.startswith("http"):
                lower_url = url.lower()
                if "profile" not in lower_url and "avatar" not in lower_url:
                    urls.append(url)

        return urls

    def extract_metadata(self, tweet_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from tweet data."""
        return {
            "tweet_id": tweet_data.get("id", ""),
            "title": tweet_data.get("title", ""),
            "desc": tweet_data.get("description", ""),
            "author": tweet_data.get("uploader", "") or tweet_data.get("channel", ""),
            "author_id": tweet_data.get("uploader_id", ""),
            "view_count": tweet_data.get("view_count", 0),
            "like_count": tweet_data.get("like_count", 0),
            "comment_count": tweet_data.get("comment_count", 0),
            "retweet_count": tweet_data.get("repost_count", 0),
            "duration": tweet_data.get("duration", 0),
        }

    def has_video(self, tweet_data: Dict[str, Any]) -> bool:
        """Check if tweet contains a video."""
        return bool(
            tweet_data.get("duration", 0) > 0
            or tweet_data.get("_type") == "video"
        )
