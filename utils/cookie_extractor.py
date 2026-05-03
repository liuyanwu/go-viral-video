"""
Automatic Browser Cookie Extractor.

Extracts cookies directly from the user's local web browsers (Chrome, Edge, Firefox, etc.)
so they don't have to manually configure them in the .env file.
"""

from typing import Dict, Optional
from utils.logger import setup_logger

logger = setup_logger("CookieExtractor")


def get_local_browser_cookies(domain: str) -> Dict[str, str]:
    """
    Attempt to load cookies for a specific domain from local browsers.
    Requires `browser_cookie3` package.
    
    Args:
        domain: Domain to extract cookies for (e.g. '.douyin.com')
        
    Returns:
        Dict of cookie name to value.
    """
    cookies_dict = {}
    
    try:
        import browser_cookie3
    except ImportError:
        logger.debug("browser_cookie3 not installed. Skipping auto cookie extraction.")
        return cookies_dict
        
    logger.info(f"Attempting to auto-extract cookies for {domain} from local browsers...")
    
    # Try browsers in order of popularity
    browsers = [
        ("Chrome", browser_cookie3.chrome),
        ("Edge", browser_cookie3.edge),
        ("Firefox", browser_cookie3.firefox),
        ("Safari", browser_cookie3.safari),
        ("Opera", browser_cookie3.opera),
        ("Brave", browser_cookie3.brave),
    ]
    
    for browser_name, fetcher in browsers:
        try:
            cj = fetcher(domain_name=domain)
            for cookie in cj:
                cookies_dict[cookie.name] = cookie.value
                
            if cookies_dict:
                logger.info(f"✅ Successfully extracted {len(cookies_dict)} cookies from {browser_name}")
                break
        except Exception as e:
            logger.debug(f"Could not get cookies from {browser_name}: {e}")
            
    return cookies_dict


def get_douyin_cookies_auto() -> Dict[str, str]:
    """
    Auto-extract Douyin cookies and filter for the essential ones needed for anti-scraping.
    """
    all_cookies = get_local_browser_cookies(".douyin.com")
    
    essential_keys = ["ttwid", "odin_tt", "passport_csrf_token", "sessionid", "msToken"]
    filtered = {}
    
    for k in essential_keys:
        if k in all_cookies:
            filtered[k] = all_cookies[k]
            
    # Also get alternative names
    if "passport_csrf_token" not in filtered and "csrf_session_id" in all_cookies:
        filtered["passport_csrf_token"] = all_cookies["csrf_session_id"]
        
    return filtered


def get_xiaohongshu_cookies_auto() -> Dict[str, str]:
    """
    Auto-extract Xiaohongshu cookies.
    Essential keys: a1, web_session
    """
    all_cookies = get_local_browser_cookies(".xiaohongshu.com")
    
    essential_keys = ["a1", "web_session", "webId", "web_session"]
    filtered = {}
    
    for k in essential_keys:
        if k in all_cookies:
            filtered[k] = all_cookies[k]
            
    return filtered
