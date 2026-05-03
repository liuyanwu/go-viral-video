"""
Multi-platform skill adapters for OpenClaw, Hermes, CladeCode, and other AI agents.
"""
import json
from typing import Any, Dict, List

# ──────── Hermes Function Calling ────────

def get_hermes_tool() -> Dict[str, Any]:
    """Hermes 2/3 function calling format (OpenAI-compatible)."""
    return {
        "type": "function",
        "function": {
            "name": "analyze_video",
            "description": "Analyze a video from URL. Downloads, transcribes, scores virality (5D 0-100), breaks down structure, and rewrites. Supports Douyin, Xiaohongshu, YouTube, TikTok, Bilibili, Instagram, Twitter/X.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Video URL or local file path"},
                    "mode": {"type": "string", "enum": ["full", "download", "transcript", "analyze"], "description": "full=complete analysis (default), download=download only, transcript=extract text only, analyze=analysis without rewrite"},
                    "rewrite_modes": {"type": "array", "items": {"type": "string", "enum": ["light", "viral"]}},
                    "rewrite_styles": {"type": "array", "items": {"type": "string", "enum": ["storytelling", "emotional", "educational", "promotional"]}},
                    "asr_engine": {"type": "string", "enum": ["funasr", "whisper"], "description": "funasr for Chinese (default), whisper for English"},
                    "language": {"type": "string", "enum": ["auto", "zh", "en"]},
                    "proxy": {"type": "string", "description": "HTTP proxy URL"}
                },
                "required": ["url"]
            }
        }
    }

def execute_hermes_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    from skill import run_skill
    return run_skill(arguments)

# ──────── OpenClaw OpenAPI Schema ────────

def get_openapi_schema() -> Dict[str, Any]:
    """OpenAPI 3.0 schema for OpenClaw integration."""
    return {
        "openapi": "3.0.0",
        "info": {"title": "Video Viral Analyzer", "version": "2.0.0"},
        "paths": {
            "/analyze": {
                "post": {
                    "operationId": "analyzeVideo",
                    "summary": "Analyze video for content creation insights",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {
                            "type": "object",
                            "properties": {
                                "url": {"type": "string"},
                                "mode": {"type": "string", "enum": ["full", "download", "transcript", "analyze"]},
                                "asr_engine": {"type": "string", "enum": ["funasr", "whisper"]}
                            },
                            "required": ["url"]
                        }}}
                    },
                    "responses": {"200": {"description": "Analysis result"}}
                }
            }
        }
    }

def execute_openapi_operation(operation_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    from skill import run_skill
    if operation_id == "analyzeVideo":
        return run_skill(params)
    return {"success": False, "error": f"Unknown operation: {operation_id}"}

# ──────── CladeCode Tool Description ────────

def get_cladecode_tool() -> Dict[str, Any]:
    """CladeCode/Claude Code tool description format."""
    return {
        "name": "video_analyzer",
        "description": "Analyzes videos for content creation. Downloads, transcribes via ASR, scores virality (hook/emotion/retention/CTA/social_currency 0-100), breaks down narrative structure, generates rewrite variants. Supports Douyin, Xiaohongshu, YouTube, TikTok, Bilibili, Instagram, Twitter/X.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Video URL or local file path"},
                "mode": {"type": "string", "description": "full | download | transcript | analyze"},
                "asr_engine": {"type": "string", "description": "funasr (Chinese) or whisper"}
            },
            "required": ["url"]
        }
    }

def execute_cladecode_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    from skill import run_skill
    if tool_name == "video_analyzer":
        return run_skill(arguments)
    return {"success": False, "error": f"Unknown tool: {tool_name}"}

# ──────── MCP (Model Context Protocol) ────────

def get_mcp_tool() -> Dict[str, Any]:
    """MCP tool definition for Claude Desktop and MCP-compatible tools."""
    return {
        "name": "analyze_video",
        "description": "Analyze a video for content creation. Downloads, transcribes, analyzes virality, generates rewrites.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Video URL or local file"},
                "mode": {"type": "string", "enum": ["full", "download", "transcript", "analyze"], "default": "full"}
            },
            "required": ["url"]
        }
    }

def execute_mcp_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    from skill import run_skill
    if name == "analyze_video":
        return run_skill(arguments)
    return {"success": False, "error": f"Unknown tool: {name}"}

# ──────── Adapter Registry ────────

ADAPTERS = {
    "hermes": {"get_tool": get_hermes_tool, "execute": execute_hermes_tool, "format": "function_calling", "platforms": ["Hermes 2", "Hermes 3", "OpenAI-compatible"]},
    "openclaw": {"get_tool": get_openapi_schema, "execute": execute_openapi_operation, "format": "openapi", "platforms": ["OpenClaw", "OpenAPI-compatible"]},
    "cladecode": {"get_tool": get_cladecode_tool, "execute": execute_cladecode_tool, "format": "tool_description", "platforms": ["CladeCode", "Claude Code"]},
    "mcp": {"get_tool": get_mcp_tool, "execute": execute_mcp_tool, "format": "mcp", "platforms": ["Claude Desktop", "MCP-compatible"]}
}

def get_adapter(platform: str) -> Dict[str, Any]:
    platform = platform.lower()
    if platform not in ADAPTERS:
        raise ValueError(f"Unknown platform: '{platform}'. Available: {', '.join(ADAPTERS.keys())}")
    return ADAPTERS[platform]

def list_adapters() -> List[Dict[str, str]]:
    return [{"platform": k, "format": v["format"], "platforms": v["platforms"]} for k, v in ADAPTERS.items()]

if __name__ == "__main__":
    print("Available adapters:")
    for a in list_adapters():
        print(f"  {a['platform']}: {a['format']} ({', '.join(a['platforms'])})")
