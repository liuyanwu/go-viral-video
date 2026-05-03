"""
Douyin utilities for generating msToken, verify_fp, and s_v_web_id.
"""

import random
import string
import time


def generate_random_string(length: int) -> str:
    """Generate a random string of given length containing letters and digits."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def get_msToken(length: int = 107) -> str:
    """
    Generate a random msToken.
    This is often required by Douyin Web APIs alongside X-Bogus.
    
    Args:
        length: Length of the generated token.
        
    Returns:
        Random msToken string.
    """
    return generate_random_string(length)


def get_verify_fp() -> str:
    """
    Generate a verify_fp value.
    This is used for verification fingerprinting.
    
    Returns:
        verify_fp string.
    """
    charset = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    base36_time = ""
    t = int(time.time() * 1000)
    
    while t > 0:
        base36_time = charset[t % 36] + base36_time
        t //= 36
        
    random_str = "".join(random.choices(charset, k=36))
    return f"verify_{base36_time}_{random_str}"


def get_s_v_web_id() -> str:
    """
    Generate s_v_web_id.
    Similar pattern to verify_fp, used for web identification.
    
    Returns:
        s_v_web_id string.
    """
    return get_verify_fp()
