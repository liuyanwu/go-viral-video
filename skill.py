"""
Video Viral Analyzer & Rewriter — Skill API Entry Point.
"""
import json
import re
import time
from typing import Any, Dict, List, Optional
from models import AnalysisResult
from exceptions import ConfigurationError

def _sanitize_error(error: Exception) -> str:
    """Sanitize error message to avoid leaking internal details."""
    error_type = type(error).__name__
    error_msg = str(error)
    
    # Strip file paths (Windows and Unix)
    error_msg = re.sub(r'[A-Za-z]:\\[^\s]*', '[path]', error_msg)
    error_msg = re.sub(r'/[^\s]*/', '[path]', error_msg)
    
    # Strip potential API keys
    error_msg = re.sub(r'sk-[a-zA-Z0-9]{20,}', '[REDACTED]', error_msg)
    error_msg = re.sub(r'api[_-]?key[=:]\s*\S+', 'api_key=[REDACTED]', error_msg, flags=re.IGNORECASE)
    
    # Keep user-actionable messages, truncate long messages
    if len(error_msg) > 200:
        error_msg = error_msg[:200] + "..."
    
    return f"{error_type}: {error_msg}"

def run_skill(input_data: Dict[str, Any]) -> Dict[str, Any]:
    start_time = time.time()
    try:
        url = input_data.get("url", "").strip()
        if not url:
            return _error_response("Missing required field: 'url'")
        mode = input_data.get("mode", "full").strip().lower()
        if mode not in ("full", "download", "transcript", "analyze"):
            return _error_response(f"Invalid mode: '{mode}'. Use: full, download, transcript, analyze")
        from config import load_config, reset_config
        from pipeline import Pipeline
        reset_config()
        load_config(overrides=_build_config_overrides(input_data))
        pipeline = Pipeline()
        skip_analysis = mode in ("download", "transcript")
        rewrite_modes = input_data.get("rewrite_modes", ["light", "viral"]) if mode == "full" else None
        rewrite_styles = input_data.get("rewrite_styles", ["storytelling", "abstract"]) if mode == "full" else None
        result = pipeline.run(url_or_path=url, skip_analysis=skip_analysis, rewrite_modes=rewrite_modes, rewrite_styles=rewrite_styles)
        if mode == "download":
            return _build_download_response(result)
        elif mode == "transcript":
            return _build_transcript_response(result)
        else:
            return _build_full_response(result, mode)
    except ConfigurationError as e:
        return _error_response(_sanitize_error(e), code=e.code)
    except Exception as e:
        return _error_response(_sanitize_error(e))

def validate_config(input_data=None):
    from config import load_config, reset_config, get_config
    reset_config()
    if input_data:
        load_config(overrides=_build_config_overrides(input_data))
    else:
        load_config()
    config = get_config()
    issues = []
    if not config.llm.api_key:
        issues.append({"field": "LLM_API_KEY", "severity": "warning", "message": "LLM analysis will fail"})
    if config.asr.engine not in ("whisper", "funasr"):
        issues.append({"field": "ASR_ENGINE", "severity": "error", "message": f"Invalid engine: {config.asr.engine}"})
    return {"valid": len([i for i in issues if i["severity"] == "error"]) == 0, "issues": issues, "config": {"llm_model": config.llm.model, "asr_engine": config.asr.engine}}

def analyze_video(url, rewrite_modes=None, rewrite_styles=None, **kwargs):
    return run_skill({"url": url, "mode": "full", "rewrite_modes": rewrite_modes or ["light", "viral"], "rewrite_styles": rewrite_styles or ["storytelling", "abstract"], **kwargs})

def download_video(url, **kwargs):
    return run_skill({"url": url, "mode": "download", **kwargs})

def extract_transcript(url, **kwargs):
    return run_skill({"url": url, "mode": "transcript", **kwargs})

def score_virality(url, **kwargs):
    result = run_skill({"url": url, "mode": "analyze", **kwargs})
    if result["success"] and result.get("data", {}).get("virality"):
        v = result["data"]["virality"]
        return {"success": True, "scores": v["scores"], "hook_type": v.get("hook_type"), "viral_potential": v.get("viral_potential"), "explanation": v.get("explanation")}
    return result

def _build_config_overrides(input_data):
    overrides = {}
    mapping = {"output_dir": "OUTPUT_DIR", "asr_engine": "ASR_ENGINE", "asr_mode": "ASR_MODE", "language": "DEFAULT_LANGUAGE", "proxy": "HTTP_PROXY"}
    for key, env_var in mapping.items():
        value = input_data.get(key)
        if value:
            overrides[env_var] = str(value)
    return overrides

def _error_response(message, code=0):
    hints = []
    if "LLM_API_KEY" in message or "api_key" in message.lower():
        hints.append("Set LLM_API_KEY in .env file")
    if "ffmpeg" in message.lower():
        hints.append("Install FFmpeg: https://ffmpeg.org/download.html")
    if "yt-dlp" in message.lower():
        hints.append("Update yt-dlp: pip install -U yt-dlp")
    return {"success": False, "mode": "error", "data": {}, "errors": [message], "hints": hints, "message": f"Error: {message}"}

def _build_download_response(result):
    return {"success": not result.errors, "mode": "download", "data": {"platform": result.video.platform.value, "video_id": result.video.video_id, "title": result.video.title, "author": result.video.author, "duration_seconds": result.video.duration_seconds, "local_path": result.video.local_path, "download_method": result.video.download_method}, "errors": result.errors, "message": f"Downloaded: {result.video.title or result.video.video_id}"}

def _build_transcript_response(result):
    text = result.transcript.cleaned_text or result.transcript.raw_text
    return {"success": not result.errors, "mode": "transcript", "data": {"video": {"platform": result.video.platform.value, "title": result.video.title}, "transcript": {"source": result.transcript.source.value, "language": result.transcript.language, "text": text, "word_count": len(text)}}, "errors": result.errors, "message": f"Transcribed {len(text)} chars"}

def _build_full_response(result, mode):
    result_dict = json.loads(result.model_dump_json(exclude_none=True))
    parts = []
    if result.video.title:
        parts.append(f"Video: {result.video.title[:40]}")
    if result.virality:
        parts.append(f"Virality: {result.virality.scores.overall}/100")
    if result.rewrites:
        count = sum([1 if result.rewrites.light else 0, 1 if result.rewrites.viral else 0, len(result.rewrites.style_variants)])
        parts.append(f"Rewrites: {count} variants")
    return {"success": not result.errors, "mode": mode, "data": result_dict, "errors": result.errors, "message": " | ".join(parts) if parts else "Analysis complete"}

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(json.dumps(analyze_video(sys.argv[1]), indent=2, ensure_ascii=False))
    else:
        print("Usage: python skill.py <URL>")
