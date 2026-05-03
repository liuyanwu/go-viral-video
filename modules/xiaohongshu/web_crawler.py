"""
Xiaohongshu (小红书) web crawler.

Extracts video notes from Xiaohongshu by:
1. Resolving short URLs (xhslink.com)
2. Fetching note page HTML
3. Parsing __INITIAL_STATE__ JSON embedded in the page
4. Extracting watermark-free video URL + metadata

Note: Xiaohongshu uses anti-scraping measures including:
- Cookie-gated content (need valid web_session or a]_1 cookie)
- Dynamic rendering
- X-S / X-T signature headers on API calls
We use page parsing as the primary method with Playwright fallback.
"""

import re
import json
from typing import Optional, Dict, Any, List
from urllib.parse import unquote

import httpx

from utils.logger import setup_logger
from utils.rate_limiter import RateLimiter

logger = setup_logger("XiaohongshuCrawler")

# Default headers mimicking a real browser visit
DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="130", "Google Chrome";v="130"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


class XiaohongshuWebCrawler:
    """
    Xiaohongshu web crawler for video note extraction.

    Strategy:
    - Resolve short URL → full explore URL
    - Fetch page HTML with browser-like headers
    - Parse embedded __INITIAL_STATE__ JSON for video data
    - Extract highest quality video stream URL
    """

    def __init__(
        self,
        cookies: Optional[Dict[str, str]] = None,
        proxy: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        )
        self.cookies = cookies or {}
        self.proxy = proxy
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
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ──────── URL Resolution ────────

    def resolve_short_url(self, short_url: str) -> str:
        """
        Resolve xhslink.com short URL to full xiaohongshu.com URL.

        Args:
            short_url: e.g. https://xhslink.com/xxxxx

        Returns:
            Full URL like https://www.xiaohongshu.com/explore/xxxxx
        """
        try:
            resp = self._client.get(short_url, follow_redirects=True)
            return str(resp.url)
        except Exception as e:
            logger.warning(f"Failed to resolve XHS short URL: {e}")
            return short_url

    def extract_note_id(self, url: str) -> Optional[str]:
        """Extract note_id from a Xiaohongshu URL."""
        # Resolve short URL first
        if "xhslink.com" in url:
            url = self.resolve_short_url(url)

        patterns = [
            r"/explore/([a-f0-9]{24})",
            r"/discovery/item/([a-f0-9]{24})",
            r"noteId=([a-f0-9]{24})",
            r"/explore/([a-f0-9]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    # ──────── Page Parsing ────────

    def fetch_note_data(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Fetch note data by parsing page HTML.

        Xiaohongshu embeds a __INITIAL_STATE__ JSON object in its
        server-rendered HTML containing all note data.

        Args:
            url: Full Xiaohongshu note URL.

        Returns:
            Parsed note data dict, or None.
        """
        if "xhslink.com" in url:
            url = self.resolve_short_url(url)

        try:
            self._rate_limiter.acquire_sync()
            resp = self._client.get(url)
            resp.raise_for_status()
            html = resp.text
            return self._parse_initial_state(html)
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching XHS note: {e}")
        return None

    def _parse_initial_state(self, html: str) -> Optional[Dict[str, Any]]:
        """
        Extract and parse __INITIAL_STATE__ from HTML.

        The state contains note content, video URLs, author info, etc.
        """
        # Pattern 1: window.__INITIAL_STATE__= {...}
        match = re.search(
            r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>',
            html,
            re.DOTALL,
        )
        if not match:
            # Pattern 2: encoded in a script tag
            match = re.search(
                r'<script>window\.__INITIAL_STATE__=(.*?)</script>',
                html,
            )

        if not match:
            logger.warning("__INITIAL_STATE__ not found in page HTML")
            return None

        try:
            raw = match.group(1)
            # XHS sometimes uses 'undefined' which is not valid JSON
            raw = raw.replace("undefined", "null")
            data = json.loads(raw)
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse __INITIAL_STATE__: {e}")
            return None

    # ──────── Video URL Extraction ────────

    def extract_video_url(self, note_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract the best quality video URL from parsed note data.

        Args:
            note_data: Parsed __INITIAL_STATE__ dict.

        Returns:
            Direct video URL, or None if not a video note.
        """
        try:
            # Navigate the nested structure
            # Common paths: note.noteDetailMap.{noteId}.note.video
            note_detail_map = note_data.get("note", {}).get("noteDetailMap", {})

            for note_id, detail in note_detail_map.items():
                note = detail.get("note", {})
                video = note.get("video", {})

                if not video:
                    continue

                # Try different video URL structures
                # Method 1: media.stream.h264 (highest quality list)
                media = video.get("media", {})
                stream = media.get("stream", {})

                for quality in ["h265", "h264", "av1"]:
                    streams = stream.get(quality, [])
                    if streams:
                        # Sort by video bitrate descending
                        sorted_streams = sorted(
                            streams,
                            key=lambda s: s.get("videoBitrate", 0),
                            reverse=True,
                        )
                        for s in sorted_streams:
                            backup_urls = s.get("backupUrls", [])
                            master_url = s.get("masterUrl", "")
                            if master_url:
                                return self._ensure_https(master_url)
                            if backup_urls:
                                return self._ensure_https(backup_urls[0])

                # Method 2: video.url (older format)
                video_url = video.get("url", "")
                if video_url:
                    return self._ensure_https(video_url)

                # Method 3: consumer.originVideoKey
                consumer = video.get("consumer", {})
                origin_key = consumer.get("originVideoKey", "")
                if origin_key:
                    return f"https://sns-video-bd.xhscdn.com/{origin_key}"

        except Exception as e:
            logger.error(f"Error extracting XHS video URL: {e}")

        return None

    def extract_metadata(self, note_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract note metadata from parsed data.

        Returns:
            Dict with title, author, tags, stats, etc.
        """
        meta = {}
        try:
            note_detail_map = note_data.get("note", {}).get("noteDetailMap", {})

            for note_id, detail in note_detail_map.items():
                note = detail.get("note", {})

                meta["note_id"] = note_id
                meta["title"] = note.get("title", "")
                meta["desc"] = note.get("desc", "")
                meta["type"] = note.get("type", "")  # "video" or "normal"

                # Author
                user = note.get("user", {})
                meta["author"] = user.get("nickname", "")
                meta["author_id"] = user.get("userId", "")

                # Interaction stats
                interact_info = note.get("interactInfo", {})
                meta["liked_count"] = interact_info.get("likedCount", "0")
                meta["collected_count"] = interact_info.get("collectedCount", "0")
                meta["comment_count"] = interact_info.get("commentCount", "0")
                meta["share_count"] = interact_info.get("shareCount", "0")

                # Tags
                tag_list = note.get("tagList", [])
                meta["tags"] = [t.get("name", "") for t in tag_list if t.get("name")]

                # Video duration
                video = note.get("video", {})
                if video:
                    consumer = video.get("consumer", {})
                    meta["duration"] = consumer.get("duration", 0)

                break  # Only process first note

        except Exception as e:
            logger.error(f"Error extracting XHS metadata: {e}")

        return meta

    # ──────── Text Content (for image notes) ────────

    def extract_text_content(self, note_data: Dict[str, Any]) -> str:
        """
        Extract text content from a Xiaohongshu note.
        Works for both video and image/text notes.

        Returns:
            Combined title + description text.
        """
        try:
            note_detail_map = note_data.get("note", {}).get("noteDetailMap", {})
            for note_id, detail in note_detail_map.items():
                note = detail.get("note", {})
                title = note.get("title", "")
                desc = note.get("desc", "")
                parts = []
                if title:
                    parts.append(title)
                if desc:
                    parts.append(desc)
                return "\n\n".join(parts)
        except Exception:
            pass
        return ""

    def extract_image_urls(self, note_data: Dict[str, Any]) -> List[str]:
        """
        Extract image URLs from a Xiaohongshu image/text note.

        Returns:
            List of image URLs.
        """
        urls = []
        try:
            note_detail_map = note_data.get("note", {}).get("noteDetailMap", {})
            for note_id, detail in note_detail_map.items():
                note = detail.get("note", {})
                image_list = note.get("imageList", [])
                for img in image_list:
                    url = img.get("urlDefault", "") or img.get("url", "")
                    if url:
                        urls.append(self._ensure_https(url))
                break
        except Exception as e:
            logger.error(f"Error extracting image URLs: {e}")
        return urls

    # ──────── Helpers ────────

    @staticmethod
    def _ensure_https(url: str) -> str:
        """Ensure URL uses HTTPS."""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("http://"):
            return url.replace("http://", "https://", 1)
        return url


def download_xhs_video(
    url: str,
    output_path: str,
    cookies: Optional[Dict[str, str]] = None,
    proxy: Optional[str] = None,
) -> Optional[str]:
    """
    High-level function to download a Xiaohongshu video note.

    Args:
        url: Xiaohongshu note URL (short or full).
        output_path: Path to save the video file.
        cookies: Optional cookies dict.
        proxy: Optional HTTP proxy.

    Returns:
        Path to downloaded file, or None on failure.
    """
    with XiaohongshuWebCrawler(cookies=cookies, proxy=proxy) as crawler:
        # Step 1: Fetch note data
        note_data = crawler.fetch_note_data(url)
        if not note_data:
            logger.error("Failed to fetch XHS note data")
            return None

        # Step 2: Check if it's a video note
        meta = crawler.extract_metadata(note_data)
        if meta.get("type") != "video":
            logger.warning(f"Note is not a video (type={meta.get('type')}), "
                           f"text content will be used directly")
            # For image/text notes, we still return None for download
            # but the text can be extracted separately
            return None

        # Step 3: Extract video URL
        video_url = crawler.extract_video_url(note_data)
        if not video_url:
            logger.error("Could not extract video download URL from XHS")
            return None

        # Step 4: Download the video
        try:
            from pathlib import Path
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            with httpx.Client(
                headers={
                    "User-Agent": crawler.user_agent,
                    "Referer": "https://www.xiaohongshu.com/",
                    "Origin": "https://www.xiaohongshu.com",
                },
                proxy=proxy,
                timeout=120,
                follow_redirects=True,
            ) as dl_client:
                with dl_client.stream("GET", video_url) as resp:
                    resp.raise_for_status()
                    with open(output_path, "wb") as f:
                        for chunk in resp.iter_bytes(chunk_size=65536):
                            f.write(chunk)

            logger.info(f"XHS video downloaded: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"XHS download failed: {e}")
            return None
