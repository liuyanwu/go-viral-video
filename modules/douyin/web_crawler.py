"""
Douyin web API crawler with anti-detection.

Supports: single video detail fetch with ABogus/XBogus signing,
short URL resolution, watermark-free video URL extraction.
"""

import re
import json
from typing import Optional, Dict, Any

import httpx

from modules.douyin.xbogus import generate_x_bogus
from modules.douyin.fingerprint import get_random_user_agent, BrowserFingerprint
from modules.douyin.endpoints import (
    DOUYIN_DOMAIN, ENDPOINTS, DEFAULT_HEADERS,
    build_video_detail_url,
)
from utils.logger import setup_logger
from utils.rate_limiter import RateLimiter

logger = setup_logger("DouyinCrawler")


class DouyinWebCrawler:
    """
    Douyin web API crawler with full anti-detection support.

    Features:
    - XBogus URL signing
    - Cookie injection
    - User-Agent rotation
    - Short URL resolution
    - Watermark-free video URL extraction
    - Highest bitrate selection
    """

    def __init__(
        self,
        cookies: Optional[Dict[str, str]] = None,
        proxy: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        self.user_agent = user_agent or get_random_user_agent()
        self.cookies = cookies or {}
        self.proxy = proxy
        self.fingerprint = BrowserFingerprint.generate("Chrome")
        self._rate_limiter = RateLimiter(max_per_second=1.0, jitter_range=0.3)

        self._client = httpx.Client(
            headers={
                **DEFAULT_HEADERS,
                "User-Agent": self.user_agent,
            },
            cookies=self.cookies,
            proxy=self.proxy,
            timeout=30,
            follow_redirects=True,
        )

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ──────── Short URL Resolution ────────

    def resolve_short_url(self, short_url: str) -> str:
        """
        Resolve a Douyin short URL to its full URL.

        Args:
            short_url: e.g. https://v.douyin.com/xxxxx

        Returns:
            Full URL with aweme_id.
        """
        try:
            resp = self._client.get(short_url, follow_redirects=True)
            return str(resp.url)
        except Exception as e:
            logger.warning(f"Failed to resolve short URL: {e}")
            return short_url

    def extract_aweme_id(self, url: str) -> Optional[str]:
        """Extract aweme_id from a Douyin URL (short or full)."""
        # Try direct extraction first
        for pattern in [r"/video/(\d+)", r"/note/(\d+)", r"modal_id=(\d+)"]:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        # If short URL, resolve and try again
        if "v.douyin.com" in url or "v.iesdouyin.com" in url:
            resolved = self.resolve_short_url(url)
            for pattern in [r"/video/(\d+)", r"/note/(\d+)", r"modal_id=(\d+)"]:
                match = re.search(pattern, resolved)
                if match:
                    return match.group(1)

        return None

    # ──────── Video Detail API ────────

    def fetch_video_detail(self, aweme_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch video detail data from Douyin API.

        Args:
            aweme_id: The video's aweme_id.

        Returns:
            Raw API response dict, or None on failure.
        """
        url = build_video_detail_url(aweme_id)

        # Sign the URL with XBogus
        signed_url, xb, ua = generate_x_bogus(url, self.user_agent)

        try:
            self._rate_limiter.acquire_sync()
            resp = self._client.get(signed_url)
            resp.raise_for_status()
            data = resp.json()

            if data.get("status_code") == 0:
                return data
            else:
                logger.warning(f"API returned status: {data.get('status_code')}")
                return data

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching video detail: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching video detail: {e}")

        return None

    # ──────── Video URL Extraction ────────

    def extract_video_url(self, detail_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract the best quality watermark-free video URL from API response.

        Args:
            detail_data: Raw API response from fetch_video_detail.

        Returns:
            Direct video download URL, or None.
        """
        try:
            aweme = detail_data.get("aweme_detail", {})
            video = aweme.get("video", {})

            # Method 1: bit_rate list (highest quality)
            bit_rate_list = video.get("bit_rate", [])
            if bit_rate_list:
                # Sort by bitrate descending
                sorted_rates = sorted(
                    bit_rate_list,
                    key=lambda x: x.get("bit_rate", 0),
                    reverse=True,
                )
                for rate in sorted_rates:
                    play_addr = rate.get("play_addr", {})
                    url_list = play_addr.get("url_list", [])
                    if url_list:
                        url = url_list[0]
                        # Remove watermark: replace 'playwm' with 'play'
                        url = url.replace("playwm", "play")
                        return url

            # Method 2: play_addr directly
            play_addr = video.get("play_addr", {})
            url_list = play_addr.get("url_list", [])
            if url_list:
                url = url_list[0]
                url = url.replace("playwm", "play")
                return url

            # Method 3: download_addr
            download_addr = video.get("download_addr", {})
            url_list = download_addr.get("url_list", [])
            if url_list:
                return url_list[0]

        except Exception as e:
            logger.error(f"Error extracting video URL: {e}")

        return None

    def extract_video_metadata(self, detail_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract video metadata from API response.

        Returns:
            Dict with title, author, duration, cover, etc.
        """
        meta = {}
        try:
            aweme = detail_data.get("aweme_detail", {})
            meta["title"] = aweme.get("desc", "")
            meta["aweme_id"] = aweme.get("aweme_id", "")

            author = aweme.get("author", {})
            meta["author"] = author.get("nickname", "")
            meta["author_id"] = author.get("sec_uid", "")

            video = aweme.get("video", {})
            meta["duration"] = video.get("duration", 0) / 1000  # ms to seconds

            meta["create_time"] = aweme.get("create_time", 0)

            stats = aweme.get("statistics", {})
            meta["digg_count"] = stats.get("digg_count", 0)
            meta["comment_count"] = stats.get("comment_count", 0)
            meta["share_count"] = stats.get("share_count", 0)
            meta["play_count"] = stats.get("play_count", 0)

        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")

        return meta

    # ──────── RENDER_DATA Extraction (Page Parsing) ────────

    def fetch_video_from_page(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Fetch video data by parsing the page's RENDER_DATA.
        Fallback method when API is blocked.

        Args:
            url: Full Douyin video page URL.

        Returns:
            Dict with video_url and metadata, or None.
        """
        try:
            resp = self._client.get(url)
            resp.raise_for_status()
            html = resp.text

            # Extract RENDER_DATA from script tag
            match = re.search(
                r'<script id="RENDER_DATA" type="application/json">(.*?)</script>',
                html,
            )
            if not match:
                logger.warning("RENDER_DATA not found in page")
                return None

            from urllib.parse import unquote
            render_data = json.loads(unquote(match.group(1)))

            # Navigate the nested structure to find video data
            for key, value in render_data.items():
                if isinstance(value, dict):
                    aweme = value.get("aweme", {}).get("detail", {})
                    if aweme:
                        return {"aweme_detail": aweme}

        except Exception as e:
            logger.error(f"Error parsing page RENDER_DATA: {e}")

        return None


def download_douyin_video(
    url: str,
    output_path: str,
    cookies: Optional[Dict[str, str]] = None,
    proxy: Optional[str] = None,
) -> Optional[str]:
    """
    High-level function to download a Douyin video.

    Tries API first, falls back to page parsing.

    Args:
        url: Douyin video URL (short or full).
        output_path: Path to save the video file.
        cookies: Optional Douyin cookies dict.
        proxy: Optional HTTP proxy.

    Returns:
        Path to downloaded file, or None on failure.
    """
    with DouyinWebCrawler(cookies=cookies, proxy=proxy) as crawler:
        # Step 1: Extract aweme_id
        aweme_id = crawler.extract_aweme_id(url)
        if not aweme_id:
            logger.warning("Could not extract aweme_id, trying page parse...")
            detail = crawler.fetch_video_from_page(url)
        else:
            # Step 2: Fetch via API
            detail = crawler.fetch_video_detail(aweme_id)
            if not detail:
                logger.info("API failed, trying page parse...")
                detail = crawler.fetch_video_from_page(url)

        if not detail:
            logger.error("All Douyin extraction methods failed")
            return None

        # Step 3: Extract video URL
        video_url = crawler.extract_video_url(detail)
        if not video_url:
            logger.error("Could not extract video download URL")
            return None

        # Step 4: Download the video
        try:
            from pathlib import Path
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            with httpx.Client(
                headers={"User-Agent": crawler.user_agent, "Referer": "https://www.douyin.com/"},
                proxy=proxy,
                timeout=120,
                follow_redirects=True,
            ) as dl_client:
                with dl_client.stream("GET", video_url) as resp:
                    resp.raise_for_status()
                    with open(output_path, "wb") as f:
                        for chunk in resp.iter_bytes(chunk_size=65536):
                            f.write(chunk)

            logger.info(f"Downloaded: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None
