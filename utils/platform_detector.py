"""
Platform detection from URLs.
Identifies which social media platform a URL belongs to and extracts video IDs.
"""

import re
from typing import Optional, Tuple
from models import Platform


# Pattern definitions: (compiled_regex, platform, id_group_name)
_PLATFORM_PATTERNS = [
    # Douyin
    (re.compile(r"(?:www\.)?douyin\.com/video/(\d+)"), Platform.DOUYIN, "video_id"),
    (re.compile(r"(?:www\.)?douyin\.com/note/(\d+)"), Platform.DOUYIN, "video_id"),
    (re.compile(r"v\.douyin\.com/([A-Za-z0-9]+)"), Platform.DOUYIN, "short_id"),
    (re.compile(r"v\.iesdouyin\.com"), Platform.DOUYIN, None),
    (re.compile(r"(?:www\.)?douyin\.com/user/"), Platform.DOUYIN, None),
    (re.compile(r"live\.douyin\.com/(\d+)"), Platform.DOUYIN, "room_id"),

    # TikTok
    (re.compile(r"(?:www\.)?tiktok\.com/@[^/]+/video/(\d+)"), Platform.TIKTOK, "video_id"),
    (re.compile(r"(?:vm|vt)\.tiktok\.com/([A-Za-z0-9]+)"), Platform.TIKTOK, "short_id"),
    (re.compile(r"(?:www\.)?tiktok\.com/"), Platform.TIKTOK, None),

    # Xiaohongshu (小红书)
    (re.compile(r"(?:www\.)?xiaohongshu\.com/(?:explore|discovery/item)/([a-f0-9]+)"), Platform.XIAOHONGSHU, "note_id"),
    (re.compile(r"(?:www\.)?xiaohongshu\.com/user/profile/[^/]+/([a-f0-9]+)"), Platform.XIAOHONGSHU, "note_id"),
    (re.compile(r"xhslink\.com/([A-Za-z0-9]+)"), Platform.XIAOHONGSHU, "short_id"),
    (re.compile(r"(?:www\.)?xiaohongshu\.com/"), Platform.XIAOHONGSHU, None),

    # Bilibili
    (re.compile(r"(?:www\.)?bilibili\.com/video/(BV[A-Za-z0-9]+)"), Platform.BILIBILI, "bv_id"),
    (re.compile(r"(?:www\.)?bilibili\.com/video/av(\d+)"), Platform.BILIBILI, "av_id"),
    (re.compile(r"b23\.tv/([A-Za-z0-9]+)"), Platform.BILIBILI, "short_id"),
    (re.compile(r"(?:www\.)?bilibili\.com/"), Platform.BILIBILI, None),

    # YouTube
    (re.compile(r"(?:www\.)?youtube\.com/watch\?v=([A-Za-z0-9_-]{11})"), Platform.YOUTUBE, "video_id"),
    (re.compile(r"youtu\.be/([A-Za-z0-9_-]{11})"), Platform.YOUTUBE, "video_id"),
    (re.compile(r"(?:www\.)?youtube\.com/shorts/([A-Za-z0-9_-]{11})"), Platform.YOUTUBE, "video_id"),
    (re.compile(r"(?:www\.)?youtube\.com/embed/([A-Za-z0-9_-]{11})"), Platform.YOUTUBE, "video_id"),
    (re.compile(r"(?:www\.)?youtube\.com/live/([A-Za-z0-9_-]{11})"), Platform.YOUTUBE, "video_id"),
    (re.compile(r"(?:www\.)?youtube\.com/"), Platform.YOUTUBE, None),

    # Instagram
    (re.compile(r"(?:www\.)?instagram\.com/(?:p|reel|reels)/([A-Za-z0-9_-]+)"), Platform.INSTAGRAM, "post_id"),
    (re.compile(r"(?:www\.)?instagram\.com/"), Platform.INSTAGRAM, None),

    # Twitter / X
    (re.compile(r"(?:www\.)?(?:twitter|x)\.com/[^/]+/status/(\d+)"), Platform.TWITTER, "tweet_id"),
    (re.compile(r"(?:www\.)?(?:twitter|x)\.com/"), Platform.TWITTER, None),

    # Kuaishou
    (re.compile(r"(?:www\.)?kuaishou\.com/"), Platform.KUAISHOU, None),
    (re.compile(r"v\.kuaishou\.com/"), Platform.KUAISHOU, None),
]


def detect_platform(url: str) -> Tuple[Platform, dict]:
    """
    Detect the platform and extract metadata from a URL.

    Args:
        url: Input URL string.

    Returns:
        Tuple of (Platform enum, metadata dict with extracted IDs).
    """
    url = url.strip()
    metadata = {}

    for pattern, platform, id_name in _PLATFORM_PATTERNS:
        match = pattern.search(url)
        if match:
            if id_name and match.lastindex:
                metadata[id_name] = match.group(1)
            metadata["platform"] = platform
            return platform, metadata

    # Check if it's a local file path
    if _is_local_file(url):
        return Platform.LOCAL, {"local_path": url}

    return Platform.UNKNOWN, {}


def _is_local_file(path: str) -> bool:
    """Check if the input is a local file path."""
    from pathlib import Path
    try:
        p = Path(path)
        return p.exists() and p.is_file()
    except (OSError, ValueError):
        return False


def is_douyin_url(url: str) -> bool:
    """Quick check if URL is Douyin."""
    return detect_platform(url)[0] == Platform.DOUYIN


def is_xiaohongshu_url(url: str) -> bool:
    """Quick check if URL is Xiaohongshu."""
    return detect_platform(url)[0] == Platform.XIAOHONGSHU


def is_short_url(url: str) -> bool:
    """Check if URL is a short/redirect URL that needs resolution."""
    short_domains = [
        "v.douyin.com", "v.iesdouyin.com",
        "vm.tiktok.com", "vt.tiktok.com",
        "b23.tv",
        "youtu.be",
        "xhslink.com",
    ]
    return any(d in url for d in short_domains)


def extract_douyin_aweme_id(url: str) -> Optional[str]:
    """Extract aweme_id from a Douyin URL."""
    patterns = [
        re.compile(r"/video/(\d+)"),
        re.compile(r"/note/(\d+)"),
        re.compile(r"modal_id=(\d+)"),
    ]
    for pattern in patterns:
        match = pattern.search(url)
        if match:
            return match.group(1)
    return None


def extract_xhs_note_id(url: str) -> Optional[str]:
    """Extract note_id from a Xiaohongshu URL."""
    patterns = [
        re.compile(r"/explore/([a-f0-9]{24})"),
        re.compile(r"/discovery/item/([a-f0-9]{24})"),
        re.compile(r"source=note&noteId=([a-f0-9]{24})"),
    ]
    for pattern in patterns:
        match = pattern.search(url)
        if match:
            return match.group(1)
    return None
