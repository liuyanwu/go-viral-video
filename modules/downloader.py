"""
Universal video downloader orchestrator.
Routes downloads to platform-specific handlers with multi-tier fallback.

Supported platforms:
- Douyin (4-tier: API → Hybrid → yt-dlp → Playwright)
- Xiaohongshu (API → yt-dlp)
- YouTube (yt-dlp with subtitle auto-download)
- TikTok, Bilibili, Instagram, Twitter/X (yt-dlp)
- Local files (passthrough)
"""

import subprocess
import shutil
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

from config import get_config
from models import VideoInfo, Platform
from exceptions import DownloadError
from utils.platform_detector import detect_platform
from utils.logger import setup_logger

logger = setup_logger("Downloader")


class VideoDownloader:
    """
    Multi-platform video downloader with fallback chains.

    For Douyin: API Direct → yt-dlp → Page Parse
    For Xiaohongshu: API Page Parse → yt-dlp
    For YouTube: yt-dlp with subtitle + chapters
    For others: yt-dlp
    For local: validate and copy
    """

    def __init__(self):
        self.config = get_config()
        self.output_dir = self.config.output_dir / "downloads"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _analyze_images_for_note(self, image_urls: list, text_content: str) -> str:
        """Analyze images for image/text notes and combine with text."""
        if not image_urls:
            return text_content
        try:
            from modules.image_analyzer import ImageAnalyzer
            with ImageAnalyzer() as analyzer:
                image_desc = analyzer.analyze_images(image_urls, text_content)
            if image_desc:
                return f"{text_content}\n\n[图片内容分析]\n{image_desc}"
        except Exception as e:
            logger.warning(f"Image analysis failed: {e}")
        return text_content

    def download(self, url_or_path: str) -> VideoInfo:
        """
        Download a video from URL or validate a local file.

        Args:
            url_or_path: URL string or local file path.

        Returns:
            VideoInfo with download results.
        """
        platform, metadata = detect_platform(url_or_path)
        video_info = VideoInfo(url=url_or_path, platform=platform)

        logger.info(f"Platform detected: [bold]{platform.value}[/bold]")

        if platform == Platform.LOCAL:
            return self._handle_local(url_or_path, video_info)
        elif platform == Platform.DOUYIN:
            return self._download_douyin(url_or_path, video_info, metadata)
        elif platform == Platform.XIAOHONGSHU:
            return self._download_xiaohongshu(url_or_path, video_info, metadata)
        elif platform == Platform.TWITTER:
            return self._download_twitter(url_or_path, video_info, metadata)
        elif platform == Platform.INSTAGRAM:
            return self._download_instagram(url_or_path, video_info, metadata)
        elif platform == Platform.YOUTUBE:
            return self._download_youtube(url_or_path, video_info, metadata)
        elif platform == Platform.UNKNOWN:
            logger.warning("Unknown platform, attempting yt-dlp...")
            return self._download_ytdlp(url_or_path, video_info)
        else:
            return self._download_ytdlp(url_or_path, video_info)

    # ──────── Local File ────────

    def _handle_local(self, path: str, info: VideoInfo) -> VideoInfo:
        """Handle local file input."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Local file not found: {path}")
        if not p.suffix.lower() in (".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv"):
            raise ValueError(f"Unsupported video format: {p.suffix}")

        info.local_path = str(p.resolve())
        info.title = p.stem
        info.download_method = "local"
        info.video_id = p.stem

        # Get duration via ffprobe
        duration = self._get_duration(str(p))
        if duration:
            info.duration_seconds = duration

        logger.info(f"Local file validated: {p.name}")
        return info

    # ──────── Douyin 4-Tier ────────

    def _download_douyin(
        self, url: str, info: VideoInfo, metadata: dict
    ) -> VideoInfo:
        """
        Download Douyin video with multi-tier fallback.

        T1: Douyin API Direct (XBogus signed)
        T2: yt-dlp with cookies
        T3: Playwright browser fallback
        """
        output_path = str(self.output_dir / f"douyin_{int(time.time())}.mp4")

        # T1: API Direct
        logger.info("[T1] Trying Douyin API Direct...")
        try:
            from modules.douyin.web_crawler import download_douyin_video

            cookies = self.config.douyin_cookies.to_dict()
            masked = self.config.douyin_cookies.mask_sensitive()
            logger.debug(f"Using cookies: {masked}")
            result = download_douyin_video(
                url=url,
                output_path=output_path,
                cookies=cookies if self.config.douyin_cookies.is_valid else None,
                proxy=self.config.network.proxy,
            )
            if result and Path(result).exists():
                info.local_path = result
                info.download_method = "douyin_api"
                self._fill_douyin_metadata(url, info)
                logger.info("[T1] ✅ Douyin API Direct succeeded")
                return info
        except Exception as e:
            logger.warning(f"[T1] Douyin API failed: {e}")

        # T2: yt-dlp
        logger.info("[T2] Trying yt-dlp...")
        try:
            info = self._download_ytdlp(url, info)
            if info.local_path:
                info.download_method = "douyin_ytdlp"
                logger.info("[T2] ✅ yt-dlp succeeded")
                return info
        except Exception as e:
            logger.warning(f"[T2] yt-dlp failed: {e}")

        # T3: Playwright browser fallback
        logger.info("[T3] Trying Playwright browser fallback...")
        try:
            from modules.douyin.browser_fallback import sync_download_video
            result = sync_download_video(url, output_path)
            if result and Path(output_path).exists():
                info.local_path = output_path
                info.download_method = "douyin_playwright"
                self._fill_douyin_metadata(url, info)
                logger.info("[T3] ✅ Playwright succeeded")
                return info
        except Exception as e:
            logger.warning(f"[T3] Playwright failed: {e}")

        raise DownloadError(
            f"All Douyin download methods failed for: {url}\n"
            f"Troubleshooting:\n"
            f"  1. Check if the URL is valid and accessible\n"
            f"  2. Configure DOUYIN_COOKIE_* in .env for API access\n"
            f"  3. Try using a proxy: --proxy http://127.0.0.1:7890\n"
            f"  4. Ensure yt-dlp is up-to-date: pip install -U yt-dlp",
            code=2001,
        )

    def _fill_douyin_metadata(self, url: str, info: VideoInfo):
        """Fill in Douyin video metadata from API."""
        try:
            from modules.douyin.web_crawler import DouyinWebCrawler
            cookies = self.config.douyin_cookies.to_dict()
            masked = self.config.douyin_cookies.mask_sensitive()
            logger.debug(f"Using cookies for metadata: {masked}")
            with DouyinWebCrawler(
                cookies=cookies if self.config.douyin_cookies.is_valid else None,
                proxy=self.config.network.proxy,
            ) as crawler:
                aweme_id = crawler.extract_aweme_id(url)
                if aweme_id:
                    info.video_id = aweme_id
                    detail = crawler.fetch_video_detail(aweme_id)
                    if detail:
                        meta = crawler.extract_video_metadata(detail)
                        info.title = meta.get("title", "")
                        info.author = meta.get("author", "")
                        info.duration_seconds = meta.get("duration", 0)
        except Exception:
            pass  # Metadata is optional

    # ──────── Xiaohongshu ────────

    def _download_xiaohongshu(
        self, url: str, info: VideoInfo, metadata: dict
    ) -> VideoInfo:
        """
        Download Xiaohongshu video or extract image/text note.

        Xiaohongshu notes can be video or image+text.
        For image notes, we extract text content and analyze images.
        """
        output_path = str(self.output_dir / f"xhs_{int(time.time())}.mp4")

        # T1: Xiaohongshu page parsing (primary method)
        logger.info("[T1] Trying Xiaohongshu page parsing...")
        try:
            from modules.xiaohongshu.web_crawler import (
                XiaohongshuWebCrawler, download_xhs_video,
            )

            # First try download
            result = download_xhs_video(
                url=url,
                output_path=output_path,
                proxy=self.config.network.proxy,
            )
            if result and Path(result).exists():
                info.local_path = result
                info.download_method = "xhs_api"
                self._fill_xhs_metadata(url, info)
                logger.info("[T1] ✅ XHS page parsing succeeded")
                return info
            else:
                # Might be a text/image note — try extracting text and images
                logger.info("[T1] Not a video note, extracting text/image content...")
                with XiaohongshuWebCrawler(proxy=self.config.network.proxy) as crawler:
                    note_data = crawler.fetch_note_data(url)
                    if note_data:
                        meta = crawler.extract_metadata(note_data)
                        info.title = meta.get("title", "")
                        info.author = meta.get("author", "")
                        info.video_id = meta.get("note_id", "")

                        # Extract text content
                        text_content = crawler.extract_text_content(note_data)

                        # Extract and analyze images
                        image_urls = crawler.extract_image_urls(note_data)
                        text_content = self._analyze_images_for_note(image_urls, text_content)

                        if text_content:
                            # Save text content for the pipeline
                            text_path = self.output_dir / f"xhs_{int(time.time())}_content.txt"
                            text_path.write_text(text_content, encoding="utf-8")
                            info.local_path = str(text_path)
                            info.download_method = "xhs_image_text_note"
                            info.duration_seconds = 0
                            logger.info(f"[T1] ✅ XHS image/text note extracted: {len(text_content)} chars")
                            return info
        except Exception as e:
            logger.warning(f"[T1] XHS page parsing failed: {e}")

        # T2: yt-dlp fallback
        logger.info("[T2] Trying yt-dlp for Xiaohongshu...")
        try:
            info = self._download_ytdlp(url, info)
            if info.local_path:
                info.download_method = "xhs_ytdlp"
                logger.info("[T2] ✅ yt-dlp succeeded for XHS")
                return info
        except Exception as e:
            logger.warning(f"[T2] yt-dlp failed for XHS: {e}")

        raise DownloadError(f"All Xiaohongshu download methods failed for: {url}")

    def _fill_xhs_metadata(self, url: str, info: VideoInfo):
        """Fill in Xiaohongshu video metadata."""
        try:
            from modules.xiaohongshu.web_crawler import XiaohongshuWebCrawler
            with XiaohongshuWebCrawler(proxy=self.config.network.proxy) as crawler:
                note_data = crawler.fetch_note_data(url)
                if note_data:
                    meta = crawler.extract_metadata(note_data)
                    info.title = meta.get("title", "") or meta.get("desc", "")[:50]
                    info.author = meta.get("author", "")
                    info.video_id = meta.get("note_id", "")
                    duration = meta.get("duration", 0)
                    if duration:
                        info.duration_seconds = duration / 1000  # ms to seconds
        except Exception:
            pass

    # ──────── Twitter/X ────────

    def _download_twitter(
        self, url: str, info: VideoInfo, metadata: dict
    ) -> VideoInfo:
        """
        Handle Twitter/X tweets (video, text, or image/text).

        For video tweets: download via yt-dlp.
        For image/text tweets: extract text content and analyze images.
        """
        output_path = str(self.output_dir / f"twitter_{int(time.time())}.mp4")

        # T1: yt-dlp --dump-json to get metadata
        logger.info("[T1] Fetching Twitter/X tweet metadata...")
        try:
            from modules.twitter.web_crawler import TwitterWebCrawler

            with TwitterWebCrawler(proxy=self.config.network.proxy) as crawler:
                tweet_data = crawler.fetch_tweet_data(url)
                if not tweet_data:
                    raise DownloadError(f"Failed to fetch tweet data for: {url}")

                meta = crawler.extract_metadata(tweet_data)
                info.title = meta.get("desc", "")[:200] or meta.get("title", "")[:200]
                info.author = meta.get("author", "")
                info.video_id = meta.get("tweet_id", "")
                info.duration_seconds = meta.get("duration", 0)

                # Check if it's a video tweet
                if crawler.has_video(tweet_data):
                    logger.info("[T1] Video tweet detected, downloading via yt-dlp...")
                    info = self._download_ytdlp(url, info)
                    if info.local_path:
                        info.download_method = "twitter_ytdlp"
                        logger.info("[T1] ✅ Twitter video downloaded")
                        return info

                # Image/text tweet
                text_content = crawler.extract_text_content(tweet_data)

                # Extract and analyze images
                image_urls = crawler.extract_image_urls(tweet_data)
                text_content = self._analyze_images_for_note(image_urls, text_content)

                if text_content:
                    text_path = self.output_dir / f"twitter_{int(time.time())}_content.txt"
                    text_path.write_text(text_content, encoding="utf-8")
                    info.local_path = str(text_path)
                    info.download_method = "twitter_image_text_note"
                    info.duration_seconds = 0
                    logger.info(f"[T1] Twitter tweet extracted: {len(text_content)} chars")
                    return info

                raise DownloadError(f"No content extracted from tweet: {url}")

        except Exception as e:
            logger.warning(f"[T1] Twitter metadata extraction failed: {e}")

        # T2: yt-dlp fallback for video
        logger.info("[T2] Trying yt-dlp direct download...")
        try:
            info = self._download_ytdlp(url, info)
            if info.local_path:
                info.download_method = "twitter_ytdlp"
                logger.info("[T2] ✅ yt-dlp succeeded for Twitter")
                return info
        except Exception as e:
            logger.warning(f"[T2] yt-dlp failed for Twitter: {e}")

        raise DownloadError(f"All Twitter download methods failed for: {url}")

    # ──────── Instagram ────────

    def _download_instagram(
        self, url: str, info: VideoInfo, metadata: dict
    ) -> VideoInfo:
        """
        Handle Instagram posts (Reels, image posts, Stories).

        For video posts: download via yt-dlp.
        For image posts: extract text content and analyze images.
        """
        logger.info("[T1] Fetching Instagram post metadata...")
        try:
            from modules.instagram.web_crawler import InstagramWebCrawler

            with InstagramWebCrawler(proxy=self.config.network.proxy) as crawler:
                shortcode = crawler.extract_shortcode(url)
                if not shortcode:
                    raise DownloadError(f"Cannot extract shortcode from: {url}", code=2002)

                media_data = crawler.fetch_media_data(shortcode)
                if media_data:
                    meta = crawler.extract_metadata(media_data)
                    info.title = meta.get("caption", "")[:200]
                    info.video_id = meta.get("shortcode", "")

                    # Check for video
                    video_url = crawler.extract_video_url(media_data)
                    if video_url:
                        logger.info("[T1] Video post detected, downloading via yt-dlp...")
                        info = self._download_ytdlp(url, info)
                        if info.local_path:
                            info.download_method = "instagram_ytdlp"
                            logger.info("[T1] Instagram video downloaded")
                            return info

                    # Image/text post
                    text_content = crawler.extract_text_content(media_data)
                    image_urls = crawler.extract_image_urls(media_data)
                    text_content = self._analyze_images_for_note(image_urls, text_content)

                    if text_content:
                        text_path = self.output_dir / f"instagram_{int(time.time())}_content.txt"
                        text_path.write_text(text_content, encoding="utf-8")
                        info.local_path = str(text_path)
                        info.download_method = "instagram_image_text_note"
                        info.duration_seconds = 0
                        logger.info(f"[T1] Instagram post extracted: {len(text_content)} chars")
                        return info

        except Exception as e:
            logger.warning(f"[T1] Instagram metadata extraction failed: {e}")

        # Fallback to yt-dlp
        logger.info("[T2] Trying yt-dlp direct download...")
        try:
            info = self._download_ytdlp(url, info)
            if info.local_path:
                info.download_method = "instagram_ytdlp"
                return info
        except Exception as e:
            logger.warning(f"[T2] yt-dlp failed for Instagram: {e}")

        raise DownloadError(
            f"All Instagram download methods failed for: {url}\n"
            f"Troubleshooting:\n"
            f"  1. Check if the URL is valid and accessible\n"
            f"  2. For private posts: configure Instagram cookies\n"
            f"  3. Try using a proxy: --proxy http://127.0.0.1:7890\n"
            f"  4. Ensure yt-dlp is up-to-date: pip install -U yt-dlp",
            code=2003,
        )

    # ──────── YouTube (Enhanced) ────────

    def _download_youtube(
        self, url: str, info: VideoInfo, metadata: dict
    ) -> VideoInfo:
        """
        Download YouTube video with enhanced options.

        Enhancements over generic yt-dlp:
        - Auto-download subtitles (zh, en, auto-generated)
        - Download chapters metadata
        - SponsorBlock skip markers
        - Prefer h264 for maximum compatibility
        """
        if not self._check_ytdlp():
            raise DownloadError("yt-dlp is not installed. Run: pip install yt-dlp")

        output_template = str(self.output_dir / "%(id)s.%(ext)s")

        ytdlp_cmd = self._get_ytdlp_cmd()
        cmd = ytdlp_cmd + [
            "--no-warnings",
            # Video format: prefer h264 for compatibility, max 1080p
            "-f", "bestvideo[vcodec^=avc1][height<=1080]+bestaudio[acodec^=mp4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
            "--merge-output-format", "mp4",
            "-o", output_template,
            "--write-info-json",
            "--no-playlist",
            # YouTube-specific: subtitles
            "--write-sub",
            "--write-auto-sub",
            "--sub-lang", "zh-Hans,zh,en,ja,ko",
            "--sub-format", "srt/vtt/best",
            "--convert-subs", "srt",
            # YouTube-specific: chapters
            "--embed-chapters",
            # YouTube-specific: thumbnail
            "--write-thumbnail",
        ]

        # Add proxy if configured
        if self.config.network.proxy:
            cmd.extend(["--proxy", self.config.network.proxy])

        cmd.append(url)

        logger.info("Running yt-dlp (YouTube enhanced)...")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # YouTube can be larger, give more time
                encoding="utf-8",
                errors="replace",
            )

            if result.returncode != 0:
                logger.error(f"yt-dlp error: {result.stderr[:500]}")
                raise DownloadError(
                    f"yt-dlp failed for YouTube: {result.stderr[:200]}\n"
                    f"Troubleshooting:\n"
                    f"  1. Check if the URL is valid and accessible\n"
                    f"  2. Try using a proxy: --proxy http://127.0.0.1:7890\n"
                    f"  3. YouTube may require cookies: --cookies-from-browser chrome\n"
                    f"  4. Ensure yt-dlp is up-to-date: pip install -U yt-dlp"
                )

            downloaded = self._find_latest_download()
            if downloaded:
                info.local_path = str(downloaded)
                info.download_method = "youtube_ytdlp"
                info.video_id = metadata.get("video_id", downloaded.stem)

                # Parse info.json for rich metadata
                info_json = downloaded.with_suffix(".info.json")
                if info_json.exists():
                    import json
                    with open(info_json, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    info.title = meta.get("title", "")
                    info.author = meta.get("uploader", meta.get("channel", ""))
                    info.duration_seconds = meta.get("duration", 0)
                    info.video_id = meta.get("id", downloaded.stem)

                if not info.duration_seconds:
                    duration = self._get_duration(info.local_path)
                    if duration:
                        info.duration_seconds = duration

                logger.info(f"✅ YouTube download complete: {info.title[:50]}...")
                return info
            else:
                raise DownloadError("yt-dlp completed but no file found")

        except subprocess.TimeoutExpired:
            raise DownloadError("YouTube download timed out (600s)")

    # ──────── yt-dlp (Universal) ────────

    def _download_ytdlp(self, url: str, info: VideoInfo) -> VideoInfo:
        """
        Download video using yt-dlp (universal fallback).

        Args:
            url: Video URL.
            info: VideoInfo to update.

        Returns:
            Updated VideoInfo.
        """
        if not self._check_ytdlp():
            raise DownloadError("yt-dlp is not installed. Run: pip install yt-dlp")

        output_template = str(self.output_dir / "%(id)s.%(ext)s")

        ytdlp_cmd = self._get_ytdlp_cmd()
        cmd = ytdlp_cmd + [
            "--no-warnings",
            "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
            "--merge-output-format", "mp4",
            "-o", output_template,
            "--write-info-json",
            "--no-playlist",
        ]

        # Add proxy if configured
        if self.config.network.proxy:
            cmd.extend(["--proxy", self.config.network.proxy])

        # Add cookies for Douyin
        if info.platform == Platform.DOUYIN and self.config.douyin_cookies.is_valid:
            cookie_str = self.config.douyin_cookies.to_cookie_string()
            cmd.extend(["--add-header", f"Cookie: {cookie_str}"])

        cmd.append(url)

        logger.info(f"Running yt-dlp...")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                encoding="utf-8",
                errors="replace",
            )

            if result.returncode != 0:
                logger.error(f"yt-dlp error: {result.stderr[:500]}")
                raise DownloadError(
                    f"yt-dlp failed: {result.stderr[:200]}\n"
                    f"Troubleshooting:\n"
                    f"  1. Check if the URL is valid and accessible\n"
                    f"  2. Try using a proxy: --proxy http://127.0.0.1:7890\n"
                    f"  3. Ensure yt-dlp is up-to-date: pip install -U yt-dlp"
                )

            # Find the downloaded file
            downloaded = self._find_latest_download()
            if downloaded:
                info.local_path = str(downloaded)
                info.download_method = "yt-dlp"
                info.video_id = downloaded.stem

                # Try to get metadata from info.json
                info_json = downloaded.with_suffix(".info.json")
                if info_json.exists():
                    import json
                    with open(info_json, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    info.title = meta.get("title", "")
                    info.author = meta.get("uploader", meta.get("channel", ""))
                    info.duration_seconds = meta.get("duration", 0)
                    info.video_id = meta.get("id", downloaded.stem)

                # Get duration via ffprobe if not set
                if not info.duration_seconds:
                    duration = self._get_duration(info.local_path)
                    if duration:
                        info.duration_seconds = duration

                return info
            else:
                raise DownloadError("yt-dlp completed but no file found")

        except subprocess.TimeoutExpired:
            raise DownloadError("yt-dlp download timed out (300s)")

    # ──────── Helpers ────────

    def _check_ytdlp(self) -> bool:
        """Check if yt-dlp is available (CLI or Python module)."""
        if shutil.which("yt-dlp"):
            return True
        try:
            result = subprocess.run(
                [sys.executable, "-m", "yt_dlp", "--version"],
                capture_output=True, timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _get_ytdlp_cmd(self) -> list:
        """Get yt-dlp command (CLI or Python module fallback)."""
        if shutil.which("yt-dlp"):
            return ["yt-dlp"]
        return [sys.executable, "-m", "yt_dlp"]

    def _check_ffmpeg(self) -> bool:
        """Check if ffmpeg is available."""
        return shutil.which("ffmpeg") is not None

    def _get_duration(self, video_path: str) -> Optional[float]:
        """Get video duration using ffprobe."""
        if not shutil.which("ffprobe"):
            return None
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries",
                 "format=duration", "-of", "csv=p=0", video_path],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except Exception:
            pass
        return None

    def _find_latest_download(self) -> Optional[Path]:
        """Find the most recently created video file in output dir."""
        video_exts = {".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv"}
        files = [
            f for f in self.output_dir.iterdir()
            if f.is_file() and f.suffix.lower() in video_exts
        ]
        if not files:
            return None
        return max(files, key=lambda f: f.stat().st_mtime)
