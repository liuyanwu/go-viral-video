"""
Browser fingerprint generator for Douyin anti-detection.
Generates randomized but realistic browser fingerprint strings.
"""

import random
from typing import Dict, Callable


class BrowserFingerprint:
    """Generate realistic browser fingerprints to avoid detection."""

    @classmethod
    def generate(cls, browser_type: str = "Chrome") -> str:
        """
        Generate a browser fingerprint string.

        Args:
            browser_type: One of 'Chrome', 'Firefox', 'Safari', 'Edge'.

        Returns:
            Fingerprint string in Douyin's expected format.
        """
        browsers: Dict[str, Callable[[], str]] = {
            "Chrome": cls._chrome,
            "Firefox": cls._firefox,
            "Safari": cls._safari,
            "Edge": cls._edge,
        }
        return browsers.get(browser_type, cls._chrome)()

    @classmethod
    def _chrome(cls) -> str:
        return cls._build(platform="Win32")

    @classmethod
    def _firefox(cls) -> str:
        return cls._build(platform="Win32")

    @classmethod
    def _safari(cls) -> str:
        return cls._build(platform="MacIntel")

    @classmethod
    def _edge(cls) -> str:
        return cls._build(platform="Win32")

    @staticmethod
    def _build(platform: str) -> str:
        """Build a fingerprint string with randomized dimensions."""
        inner_w = random.randint(1024, 1920)
        inner_h = random.randint(768, 1080)
        outer_w = inner_w + random.randint(24, 32)
        outer_h = inner_h + random.randint(75, 90)
        screen_x = 0
        screen_y = random.choice([0, 30])
        size_w = random.randint(1024, 1920)
        size_h = random.randint(768, 1080)
        avail_w = random.randint(1280, 1920)
        avail_h = random.randint(800, 1080)

        return (
            f"{inner_w}|{inner_h}|{outer_w}|{outer_h}|"
            f"{screen_x}|{screen_y}|0|0|{size_w}|{size_h}|"
            f"{avail_w}|{avail_h}|{inner_w}|{inner_h}|24|24|{platform}"
        )


# Common User-Agent strings for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
]


def get_random_user_agent() -> str:
    """Get a random User-Agent string."""
    return random.choice(USER_AGENTS)
