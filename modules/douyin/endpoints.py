"""
Douyin API endpoint definitions and request construction.
"""

# Base domains
DOUYIN_DOMAIN = "https://www.douyin.com"
DOUYIN_API_DOMAIN = "https://www.douyin.com"

# API Endpoints
ENDPOINTS = {
    # Single video detail
    "video_detail": "/aweme/v1/web/aweme/detail/",

    # User profile
    "user_info": "/aweme/v1/web/user/profile/other/",
    "user_post": "/aweme/v1/web/aweme/post/",
    "user_like": "/aweme/v1/web/aweme/favoriting/",

    # Mix/Collection
    "mix_detail": "/aweme/v1/web/mix/listcollection/",

    # Short URL redirect
    "short_url": "https://www.iesdouyin.com/share/video/",

    # msToken generation
    "mstoken": "/ttwid/union/register/",
}

# Default request headers for Douyin web API
DEFAULT_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Referer": "https://www.douyin.com/",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="130", "Google Chrome";v="130"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

# Default query parameters for video detail API
DEFAULT_VIDEO_PARAMS = {
    "device_platform": "webapp",
    "aid": "6383",
    "channel": "channel_pc_web",
    "pc_client_type": "1",
    "version_code": "170400",
    "version_name": "17.4.0",
    "cookie_enabled": "true",
    "screen_width": "1920",
    "screen_height": "1080",
    "browser_language": "zh-CN",
    "browser_platform": "Win32",
    "browser_name": "Chrome",
    "browser_version": "130.0.0.0",
    "browser_online": "true",
    "engine_name": "Blink",
    "engine_version": "130.0.0.0",
    "os_name": "Windows",
    "os_version": "10",
    "cpu_core_num": "16",
    "device_memory": "8",
    "platform": "PC",
    "downlink": "10",
    "effective_type": "4g",
    "round_trip_time": "50",
}

def build_video_detail_params(aweme_id: str) -> dict:
    """
    Build query parameters for video detail API.
    """
    params = DEFAULT_VIDEO_PARAMS.copy()
    params["aweme_id"] = aweme_id
    return params

def build_video_detail_url(aweme_id: str) -> str:
    """
    Build the full URL for video detail API request.
    """
    params = build_video_detail_params(aweme_id)
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{DOUYIN_API_DOMAIN}{ENDPOINTS['video_detail']}?{query}"
