"""
Test suite for platform detection.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Platform
from utils.platform_detector import (
    detect_platform, is_short_url,
    extract_douyin_aweme_id, extract_xhs_note_id,
    is_xiaohongshu_url,
)


def test_douyin_detection():
    # Long URLs
    p1, m1 = detect_platform("https://www.douyin.com/video/7339796030991879461")
    assert p1 == Platform.DOUYIN
    assert m1.get("video_id") == "7339796030991879461"

    p2, m2 = detect_platform("https://www.douyin.com/note/7339796030991879461")
    assert p2 == Platform.DOUYIN
    assert m2.get("video_id") == "7339796030991879461"

    # Short URLs
    p3, m3 = detect_platform("https://v.douyin.com/iNpQk7w/")
    assert p3 == Platform.DOUYIN
    assert is_short_url("https://v.douyin.com/iNpQk7w/")


def test_tiktok_detection():
    p1, m1 = detect_platform("https://www.tiktok.com/@user/video/71234567890")
    assert p1 == Platform.TIKTOK
    assert m1.get("video_id") == "71234567890"

    p2, m2 = detect_platform("https://vm.tiktok.com/ZMec1234/")
    assert p2 == Platform.TIKTOK
    assert is_short_url("https://vm.tiktok.com/ZMec1234/")


def test_bilibili_detection():
    p1, m1 = detect_platform("https://www.bilibili.com/video/BV1xx411c7mD")
    assert p1 == Platform.BILIBILI
    assert m1.get("bv_id") == "BV1xx411c7mD"

    p2, m2 = detect_platform("https://b23.tv/abcd123")
    assert p2 == Platform.BILIBILI
    assert is_short_url("https://b23.tv/abcd123")


def test_youtube_detection():
    # Standard watch URL
    p1, m1 = detect_platform("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert p1 == Platform.YOUTUBE
    assert m1.get("video_id") == "dQw4w9WgXcQ"

    # Short URL
    p2, m2 = detect_platform("https://youtu.be/dQw4w9WgXcQ")
    assert p2 == Platform.YOUTUBE
    assert m2.get("video_id") == "dQw4w9WgXcQ"

    # Shorts
    p3, m3 = detect_platform("https://www.youtube.com/shorts/dQw4w9WgXcQ")
    assert p3 == Platform.YOUTUBE
    assert m3.get("video_id") == "dQw4w9WgXcQ"

    # Embed
    p4, m4 = detect_platform("https://www.youtube.com/embed/dQw4w9WgXcQ")
    assert p4 == Platform.YOUTUBE
    assert m4.get("video_id") == "dQw4w9WgXcQ"

    # Live
    p5, m5 = detect_platform("https://www.youtube.com/live/dQw4w9WgXcQ")
    assert p5 == Platform.YOUTUBE
    assert m5.get("video_id") == "dQw4w9WgXcQ"


def test_xiaohongshu_detection():
    # Explore URL
    p1, m1 = detect_platform("https://www.xiaohongshu.com/explore/6543210fedcba9876543210f")
    assert p1 == Platform.XIAOHONGSHU
    assert m1.get("note_id") == "6543210fedcba9876543210f"

    # Discovery URL
    p2, m2 = detect_platform("https://www.xiaohongshu.com/discovery/item/6543210fedcba9876543210f")
    assert p2 == Platform.XIAOHONGSHU
    assert m2.get("note_id") == "6543210fedcba9876543210f"

    # Short URL
    p3, m3 = detect_platform("https://xhslink.com/abc123")
    assert p3 == Platform.XIAOHONGSHU
    assert is_short_url("https://xhslink.com/abc123")

    # Helper function
    assert is_xiaohongshu_url("https://www.xiaohongshu.com/explore/123456")


def test_xiaohongshu_note_id_extraction():
    assert extract_xhs_note_id("https://www.xiaohongshu.com/explore/6543210fedcba9876543210f") == "6543210fedcba9876543210f"
    assert extract_xhs_note_id("https://www.xiaohongshu.com/discovery/item/6543210fedcba9876543210f") == "6543210fedcba9876543210f"
    assert extract_xhs_note_id("https://xhslink.com/abc123") is None  # Needs resolution


def test_local_file_detection():
    # We create a dummy file to test
    dummy_file = Path("test_dummy.mp4")
    dummy_file.touch()

    try:
        p1, m1 = detect_platform("test_dummy.mp4")
        assert p1 == Platform.LOCAL
        assert m1.get("local_path") == "test_dummy.mp4"
    finally:
        dummy_file.unlink()


def test_extract_douyin_aweme_id():
    assert extract_douyin_aweme_id("https://www.douyin.com/video/12345") == "12345"
    assert extract_douyin_aweme_id("https://www.douyin.com/note/67890") == "67890"
    assert extract_douyin_aweme_id("https://www.douyin.com/user/xyz?modal_id=111222") == "111222"
    assert extract_douyin_aweme_id("https://v.douyin.com/iNpQk7w/") is None  # Needs resolution


def test_instagram_detection():
    p1, m1 = detect_platform("https://www.instagram.com/reel/Cxyz123456/")
    assert p1 == Platform.INSTAGRAM
    assert m1.get("post_id") == "Cxyz123456"


def test_twitter_detection():
    p1, m1 = detect_platform("https://x.com/user/status/1234567890123456789")
    assert p1 == Platform.TWITTER
    assert m1.get("tweet_id") == "1234567890123456789"

    p2, m2 = detect_platform("https://twitter.com/user/status/9876543210")
    assert p2 == Platform.TWITTER
