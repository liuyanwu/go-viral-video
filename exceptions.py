"""
Custom exception hierarchy for GoViralVideo.
"""

from typing import Optional


class GoViralVideoError(Exception):
    def __init__(self, message: str, code: int = 0, context: Optional[dict] = None):
        self.message = message
        self.code = code
        self.context = context or {}
        super().__init__(f"{message} [code={code}]")

    def __str__(self):
        ctx = f", context={self.context}" if self.context else ""
        return f"{self.message} [code={self.code}]{ctx}"


class DownloadError(GoViralVideoError):
    pass


class PlatformDetectionError(GoViralVideoError):
    pass


class ASRError(GoViralVideoError):
    pass


class SubtitleExtractionError(GoViralVideoError):
    pass


class LLMError(GoViralVideoError):
    pass


class TextProcessingError(GoViralVideoError):
    pass


class AnalysisError(GoViralVideoError):
    pass


class RewriteError(GoViralVideoError):
    pass


class ConfigurationError(GoViralVideoError):
    pass


class CacheError(GoViralVideoError):
    pass
