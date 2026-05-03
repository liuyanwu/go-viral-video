"""
Playwright-based Douyin browser fallback and cookie manager.
Used as T4 download method and for auto-refreshing cookies.
"""

import asyncio
import os
import json
from pathlib import Path
from typing import Dict, Optional
from utils.logger import setup_logger

logger = setup_logger("DouyinBrowser")

class BrowserManager:
    """Manages Playwright browser instances for Douyin fallback."""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        
    async def fetch_cookies(self, url: str = "https://www.douyin.com") -> Dict[str, str]:
        """
        Launch browser, visit Douyin, and extract necessary cookies.
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright && playwright install")
            return {}

        logger.info(f"Launching Playwright to fetch cookies from {url}...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until="domcontentloaded")
                # Wait a bit for async cookies (like ttwid) to be set
                await page.wait_for_timeout(3000)
                
                playwright_cookies = await context.cookies()
                cookies = {c["name"]: c["value"] for c in playwright_cookies}
                
                logger.info(f"Successfully fetched {len(cookies)} cookies.")
                return cookies
            except Exception as e:
                logger.error(f"Error fetching cookies: {e}")
                return {}
            finally:
                await browser.close()
                
    async def download_video(self, url: str, output_path: str) -> bool:
        """
        T4 Fallback: Use Playwright to intercept video requests directly from the page.
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("Playwright not installed.")
            return False

        logger.info(f"[T4] Launching Playwright to intercept video for {url}...")
        
        video_url = None
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context()
            page = await context.new_page()
            
            async def handle_response(response):
                nonlocal video_url
                res_type = response.request.resource_type
                url_str = response.url
                if (res_type == "media" or "video" in url_str) and ("v26" in url_str or "v3" in url_str or ".mp4" in url_str):
                    video_url = url_str
            
            page.on("response", handle_response)
            
            try:
                await page.goto(url, wait_until="domcontentloaded")
                await page.wait_for_timeout(8000) # Give it time to load video
                
                if video_url:
                    logger.info(f"[T4] Intercepted video URL via Playwright.")
                    # Download it using httpx
                    import httpx
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(video_url, headers={"Referer": "https://www.douyin.com/"}, timeout=httpx.Timeout(120.0))
                        resp.raise_for_status()
                        with open(output_path, "wb") as f:
                            async for chunk in resp.aiter_bytes(chunk_size=65536):
                                f.write(chunk)
                    return True
                else:
                    logger.warning("[T4] Could not intercept video URL.")
                    return False
            except Exception as e:
                logger.error(f"[T4] Playwright error: {e}")
                return False
            finally:
                await browser.close()

def _get_event_loop():
    """Get or create an event loop safely."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    return loop


def _run_async(coro):
    """Run async code in a way that works both in and outside event loops."""
    loop = _get_event_loop()
    if loop is not None:
        import nest_asyncio
        try:
            nest_asyncio.apply(loop)
        except ImportError:
            pass
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    return asyncio.run(coro)


def sync_fetch_cookies() -> Dict[str, str]:
    """Synchronous wrapper for fetch_cookies."""
    manager = BrowserManager()
    return _run_async(manager.fetch_cookies())

def sync_download_video(url: str, output_path: str) -> bool:
    """Synchronous wrapper for download_video."""
    manager = BrowserManager()
    return _run_async(manager.download_video(url, output_path))
