"""
Instagram web API crawler module.
Supports Reels, Posts, and Stories extraction.
"""

import httpx
import re
from typing import Optional, Dict, Any, List
from utils.logger import setup_logger
from utils.rate_limiter import RateLimiter
from utils.anti_detect import browser_headers

logger = setup_logger("InstagramCrawler")

INSTAGRAM_DOMAIN = "https://www.instagram.com"

class InstagramWebCrawler:
    """Instagram web crawler with anti-detection."""
    
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy
        self._rate_limiter = RateLimiter(max_per_second=0.5, jitter_range=0.5)
        self._client = httpx.Client(
            headers=browser_headers(referer=INSTAGRAM_DOMAIN),
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
    
    def extract_shortcode(self, url: str) -> Optional[str]:
        """Extract shortcode from Instagram URL."""
        patterns = [
            r"/(?:p|reel|reels)/([A-Za-z0-9_-]+)",
            r"/stories/[^/]+/(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def fetch_media_data(self, shortcode: str) -> Optional[Dict[str, Any]]:
        """Fetch media data via Instagram embed endpoint."""
        is_story = shortcode.isdigit()

        if is_story:
            url = f"{INSTAGRAM_DOMAIN}/stories/{shortcode}/"
        else:
            url = f"{INSTAGRAM_DOMAIN}/p/{shortcode}/embed/?captioned=true"

        try:
            self._rate_limiter.acquire_sync()
            resp = self._client.get(url)
            resp.raise_for_status()
            return {"shortcode": shortcode, "url": url, "html": resp.text[:5000]}
        except Exception as e:
            logger.error(f"Error fetching Instagram media: {e}")
            return None
    
    def extract_text_content(self, media_data: Dict[str, Any]) -> str:
        """Extract caption/text from Instagram post."""
        parts = []
        caption = media_data.get("caption", "") or ""
        if caption:
            parts.append(caption)
        return "\n\n".join(parts)

    def extract_image_urls(self, media_data: Dict[str, Any]) -> List[str]:
        """Extract image URLs from Instagram post (carousel support)."""
        urls = []
        html = media_data.get("html", "")
        img_pattern = re.compile(r'src="(https://[^"]*cdninstagram[^"]*)"')
        for match in img_pattern.finditer(html):
            url = match.group(1)
            if url not in urls:
                urls.append(url)
        return urls
    
    def extract_video_url(self, media_data: Dict[str, Any]) -> Optional[str]:
        """Extract video URL from media data."""
        return media_data.get("video_url")
    
    def extract_metadata(self, media_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from media data."""
        return {
            "shortcode": media_data.get("shortcode", ""),
            "caption": media_data.get("caption", ""),
            "media_type": media_data.get("media_type", "unknown"),
            "like_count": media_data.get("like_count", 0),
            "comment_count": media_data.get("comment_count", 0),
        }
