"""Combined tests for modules."""
import pytest, tempfile
from pathlib import Path

def test_text_cleaner_performance():
    from modules.text_cleaner import TextCleaner
    cleaner = TextCleaner()
    text = "测试文本" * 12500
    result = cleaner._clean_text(text)
    assert len(result) > 0

def test_chunk_processor_split():
    from modules.chunk_processor import ChunkProcessor
    cp = ChunkProcessor()
    text = "测试" * 50000
    chunks = cp.split_text_by_tokens(text, max_tokens=10000)
    assert len(chunks) > 1

def test_cache_put_get():
    from cache import ContentCache
    from models import AnalysisResult, VideoInfo, TranscriptResult, Platform, SubtitleSource
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ContentCache(Path(tmpdir), ttl_hours=1)
        result = AnalysisResult(video=VideoInfo(url="http://test.com", platform=Platform.UNKNOWN), transcript=TranscriptResult(source=SubtitleSource.MANUAL))
        cache.put("http://test.com", result)
        cached = cache.get("http://test.com")
        assert cached is not None
        assert cached.video.url == "http://test.com"

def test_cache_miss():
    from cache import ContentCache
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ContentCache(Path(tmpdir))
        assert cache.get("http://nonexistent.com") is None

def test_cache_clear():
    from cache import ContentCache
    from models import AnalysisResult, VideoInfo, TranscriptResult, Platform, SubtitleSource
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ContentCache(Path(tmpdir))
        result = AnalysisResult(video=VideoInfo(url="http://test.com", platform=Platform.UNKNOWN), transcript=TranscriptResult(source=SubtitleSource.MANUAL))
        cache.put("http://test.com", result)
        cache.clear()
        assert cache.stats()["count"] == 0

def test_cache_ttl_expiration():
    import time
    from cache import ContentCache
    from models import AnalysisResult, VideoInfo, TranscriptResult, Platform, SubtitleSource
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ContentCache(Path(tmpdir), ttl_hours=0)
        result = AnalysisResult(video=VideoInfo(url="http://test.com", platform=Platform.UNKNOWN), transcript=TranscriptResult(source=SubtitleSource.MANUAL))
        cache.put("http://test.com", result)
        time.sleep(1)
        assert cache.get("http://test.com") is None

def test_chunk_split_small():
    from modules.chunk_processor import ChunkProcessor
    cp = ChunkProcessor()
    chunks = cp.split_text_by_tokens("小文本", max_tokens=1000)
    assert len(chunks) == 1
    assert chunks[0] == "小文本"

def test_chunk_merge_text():
    from modules.chunk_processor import ChunkProcessor
    cp = ChunkProcessor()
    result = cp.merge_text(["chunk1", "chunk2"])
    assert "chunk1" in result and "chunk2" in result

def test_instagram_shortcode():
    from modules.instagram.web_crawler import InstagramWebCrawler
    c = InstagramWebCrawler()
    assert c.extract_shortcode("https://www.instagram.com/p/ABC123/") == "ABC123"
    assert c.extract_shortcode("https://www.instagram.com/reel/XYZ789/") == "XYZ789"
    assert c.extract_shortcode("https://www.instagram.com/nonexistent") is None

def test_instagram_metadata():
    from modules.instagram.web_crawler import InstagramWebCrawler
    c = InstagramWebCrawler()
    meta = c.extract_metadata({"shortcode": "ABC123", "caption": "Test", "media_type": "video", "like_count": 100})
    assert meta["shortcode"] == "ABC123"
    assert meta["like_count"] == 100

def test_twitter_shortcode():
    from modules.twitter.web_crawler import TwitterWebCrawler
    c = TwitterWebCrawler()
    assert c.extract_tweet_id("https://x.com/user/status/123456789") == "123456789"

def test_twitter_images():
    from modules.twitter.web_crawler import TwitterWebCrawler
    c = TwitterWebCrawler()
    images = c.extract_image_urls({"thumbnails": [{"url": "https://pbs.twimg.com/media/img1.jpg"}, {"url": "https://pbs.twimg.com/profile_images/avatar.jpg"}]})
    assert len(images) == 1

def test_instagram_video_url():
    from modules.instagram.web_crawler import InstagramWebCrawler
    c = InstagramWebCrawler()
    assert c.extract_image_urls({"html": 'src="https://scontent.cdninstagram.com/v/test.jpg"'}) == ["https://scontent.cdninstagram.com/v/test.jpg"]

def test_downloader_init():
    from modules.downloader import VideoDownloader
    d = VideoDownloader()
    assert d.output_dir.exists()

def test_asr_error():
    from exceptions import ASRError
    with pytest.raises(ASRError) as exc:
        raise ASRError("test", code=3001, context={"engine": "test"})
    assert exc.value.code == 3001
