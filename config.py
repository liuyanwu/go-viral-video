"""
Configuration management for Video Viral Analyzer & Rewriter.
Loads settings from .env file and provides typed access.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv
from exceptions import ConfigurationError


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    max_tokens: int = 32768
    temperature: float = 0.7


@dataclass
class ASRConfig:
    """ASR engine configuration."""
    engine: str = "funasr"       # whisper | funasr
    mode: str = "fast"            # fast | accurate
    whisper_model_fast: str = "base"
    whisper_model_accurate: str = "large-v3"


@dataclass
class DouyinCookieConfig:
    """Douyin cookie configuration for API access."""
    ttwid: str = ""
    odin_tt: str = ""
    csrf_token: str = ""
    sessionid: str = ""

    @property
    def is_valid(self) -> bool:
        """Check if minimum cookies are set."""
        return bool(self.ttwid)

    def to_cookie_string(self) -> str:
        """Convert to HTTP cookie header string."""
        parts = []
        if self.ttwid:
            parts.append(f"ttwid={self.ttwid}")
        if self.odin_tt:
            parts.append(f"odin_tt={self.odin_tt}")
        if self.csrf_token:
            parts.append(f"passport_csrf_token={self.csrf_token}")
        if self.sessionid:
            parts.append(f"sessionid={self.sessionid}")
        return "; ".join(parts)

    def to_dict(self) -> dict:
        """Convert to cookie dict for httpx."""
        cookies = {}
        if self.ttwid:
            cookies["ttwid"] = self.ttwid
        if self.odin_tt:
            cookies["odin_tt"] = self.odin_tt
        if self.csrf_token:
            cookies["passport_csrf_token"] = self.csrf_token
        if self.sessionid:
            cookies["sessionid"] = self.sessionid
        return cookies

    def mask_sensitive(self) -> dict:
        """Return cookie dict with masked values for logging."""
        masked = {}
        for k, v in self.to_dict().items():
            if len(v) > 8:
                masked[k] = v[:4] + "****" + v[-4:]
            else:
                masked[k] = "****"
        return masked


@dataclass
class NetworkConfig:
    """Network configuration."""
    proxy: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    rate_limit: float = 2.0    # requests per second


@dataclass
class AppConfig:
    """Top-level application configuration."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    asr: ASRConfig = field(default_factory=ASRConfig)
    douyin_cookies: DouyinCookieConfig = field(default_factory=DouyinCookieConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    output_dir: Path = Path("./output")
    default_language: str = "auto"
    max_transcript_chars: int = 500000
    enable_asr_correction: bool = True
    confirm_cookie_extract: bool = False

    def __post_init__(self):
        try:
            self.output_dir = Path(self.output_dir).resolve()
            if not self.output_dir.is_relative_to(Path.cwd().resolve()):
                raise ConfigurationError(
                    message=f"Output directory must be within current working directory: {self.output_dir}",
                    code=1002,
                    context={"output_dir": str(self.output_dir), "cwd": str(Path.cwd())}
                )
        except (OSError, ValueError) as e:
            raise ConfigurationError(
                message=f"Invalid output directory path: {self.output_dir}",
                code=1002,
                context={"output_dir": str(self.output_dir), "error": str(e)}
            )
        self.output_dir.mkdir(parents=True, exist_ok=True)


def load_config(
    env_path: Optional[str] = None,
    overrides: Optional[dict] = None,
) -> AppConfig:
    """
    Load configuration from .env file and environment variables.

    Priority: explicit override > environment variable > .env file > default value

    Args:
        env_path: Optional path to .env file.
        overrides: Optional dict of explicit overrides (e.g. from CLI args).
    """
    if env_path:
        load_dotenv(env_path)
    else:
        for candidate in [Path(__file__).parent / ".env", Path(".env")]:
            if candidate.exists():
                load_dotenv(candidate)
                break

    dy_ttwid = os.getenv("DOUYIN_COOKIE_TTWID", "")
    dy_odin = os.getenv("DOUYIN_COOKIE_ODIN_TT", "")
    dy_csrf = os.getenv("DOUYIN_COOKIE_CSRF_TOKEN", "")
    dy_session = os.getenv("DOUYIN_COOKIE_SESSIONID", "")

    def _get(key: str, default: str) -> str:
        if overrides and key in overrides:
            return str(overrides[key])
        return os.getenv(key, default)

    def _get_bool(key: str, default: bool) -> bool:
        val = _get(key, str(default)).lower()
        return val not in ("false", "0", "no", "off")

    confirm_cookie = os.getenv("CONFIRM_COOKIE_EXTRACT", "").lower() not in ("false", "0", "no", "off", "")

    if not dy_ttwid and confirm_cookie:
        try:
            from utils.cookie_extractor import get_douyin_cookies_auto
            auto_dy = get_douyin_cookies_auto()
            dy_ttwid = auto_dy.get("ttwid", "")
            dy_odin = auto_dy.get("odin_tt", "")
            dy_csrf = auto_dy.get("passport_csrf_token", "")
            dy_session = auto_dy.get("sessionid", "")
        except Exception:
            pass

    config = AppConfig(
        llm=LLMConfig(
            api_key=_get("LLM_API_KEY", ""),
            base_url=_get("LLM_BASE_URL", "https://api.openai.com/v1"),
            model=_get("LLM_MODEL", "gpt-4o-mini"),
        ),
        asr=ASRConfig(
            engine=_get("ASR_ENGINE", "funasr"),
            mode=_get("ASR_MODE", "fast"),
        ),
        douyin_cookies=DouyinCookieConfig(
            ttwid=dy_ttwid,
            odin_tt=dy_odin,
            csrf_token=dy_csrf,
            sessionid=dy_session,
        ),
        network=NetworkConfig(
            proxy=_get("HTTP_PROXY", "") or None,
        ),
        output_dir=Path(_get("OUTPUT_DIR", "./output")),
        default_language=_get("DEFAULT_LANGUAGE", "auto"),
        enable_asr_correction=_get_bool("ENABLE_ASR_CORRECTION", True),
        confirm_cookie_extract=confirm_cookie,
    )

    # Validate required settings
    if not config.llm.api_key:
        # Don't fail hard — just warn. Some modes (download-only, transcript-only) don't need LLM.
        import warnings
        warnings.warn(
            "LLM_API_KEY is not set. LLM analysis stages (summary, virality, structure, rewrite) "
            "will fail. Set LLM_API_KEY in .env or environment variable. "
            "See .env.example for all configuration options.",
            UserWarning,
            stacklevel=2,
        )

    return config


# Global singleton
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get or create the global config singleton."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reset_config():
    """Reset config singleton (useful for testing)."""
    global _config
    _config = None


class ServiceContainer:
    """Dependency injection container for application services."""

    def __init__(self, config: AppConfig):
        self.config = config
        self._llm_client = None
        self._cache = None

    @property
    def llm_client(self):
        if self._llm_client is None:
            from utils.llm_client import LLMClient
            self._llm_client = LLMClient(self.config.llm)
        return self._llm_client

    @property
    def cache(self):
        if self._cache is None:
            from cache import ContentCache
            cache_dir = self.config.output_dir / ".cache"
            self._cache = ContentCache(cache_dir)
        return self._cache
