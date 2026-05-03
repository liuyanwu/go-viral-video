---
name: Video Viral Analyzer & Rewriter
description: A multi-platform video and image/text note analysis pipeline supporting Douyin, Xiaohongshu (video + image/text notes), Twitter/X (video + image/text notes), YouTube, TikTok, Bilibili, and Instagram. Downloads videos with anti-scraping measures, extracts transcripts, scores virality (5D 0-100), breaks down narrative structure, and rewrites scripts in multiple styles. Supports vision-capable LLM for image understanding. Supports both Skill API and CLI tool modes.
version: 2.0.0
author: GoViralVideo Team
license: Apache-2.0
skill_entry: skill.py
skill_function: run_skill
tags:
  - video
  - analysis
  - rewrite
  - douyin
  - xiaohongshu
  - youtube
  - tiktok
  - bilibili
  - summarization
  - virality
  - image-analysis
---

# Video Viral Analyzer & Rewriter

> **Dual-mode**: Works as both an **AI Skill** (called by agents) and a **CLI Tool** (used by humans).

## 🔌 Mode 1: AI Skill (Agent Integration)

AI agents call `run_skill()` from `skill.py` with a single input dict.

### Skill Entry Point

```python
from skill import run_skill

result = run_skill({
    "url": "https://v.douyin.com/xxxxx",
    "mode": "full",                        # full | download | transcript | analyze
    "rewrite_modes": ["light", "viral"],
    "rewrite_styles": ["storytelling"],
})
```

### Input Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | ✅ | Video URL, image/text note URL, or local file path |
| `mode` | string | ❌ | `full` (default), `download`, `transcript`, `analyze` |
| `output_dir` | string | ❌ | Output directory (default: `./output`) |
| `asr_engine` | string | ❌ | `funasr` (default) or `whisper` |
| `asr_mode` | string | ❌ | `fast` (default) or `accurate` |
| `language` | string | ❌ | `auto` (default), `zh`, `en` |
| `proxy` | string | ❌ | HTTP proxy URL |
| `rewrite_modes` | list | ❌ | `["light", "viral"]` |
| `rewrite_styles` | list | ❌ | `["storytelling", "emotional", "educational", "promotional"]` |
| `douyin_cookies` | dict | ❌ | `{ttwid, odin_tt, csrf_token, sessionid}` |

### 🖼️ Image/Text Note Support (Xiaohongshu)

The pipeline fully supports Xiaohongshu image+text notes (图文笔记):

1. **Text Extraction**: Extracts title, description, and hashtags
2. **Image Analysis**: Uses vision-capable LLM to analyze images
3. **Combined Output**: Merges text and image analysis

**Requirements for Image Analysis:**
- Use a vision-capable LLM model in `.env`:
  ```ini
  LLM_MODEL=qwen3.6-plus
  LLM_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
  ```
- Supported models: `qwen3.6-plus`, `qwen-vl-max`, `gpt-4o`, `kimi-k2`, etc.

**Example Usage:**
```python
# Analyze a Xiaohongshu image/text note
result = run_skill({
    "url": "https://www.xiaohongshu.com/explore/69da4d99000000001d01ab9c",
    "mode": "full",
})
# Output includes image analysis in transcript.corrected_text
```

### Output Schema

```json
{
    "success": true,
    "mode": "full",
    "data": {
        "video": { "platform": "douyin", "title": "...", "author": "...", "duration_seconds": 30 },
        "transcript": { "source": "asr", "language": "zh", "cleaned_text": "...", "word_count": 500 },
        "summary": { "one_sentence": "...", "key_points": ["...", "..."] },
        "virality": {
            "scores": { "hook": 85, "emotion": 70, "retention": 75, "cta": 60, "social_currency": 80, "overall": 75 },
            "hook_type": "curiosity",
            "viral_potential": "high"
        },
        "structure": { "hook": {...}, "setup": {...}, "conflict": {...}, "climax": {...}, "cta": {...} },
        "rewrites": { "light": {...}, "viral": {...}, "style_variants": [...] }
    },
    "errors": [],
    "message": "Video: xxx | Virality: 75/100 (high) | Rewrites: 3 variants"
}
```

### Execution Modes

| Mode | Download | Transcript | LLM Analysis | Rewrite | Use Case |
|------|----------|-----------|--------------|---------|----------|
| `full` | ✅ | ✅ | ✅ | ✅ | Complete analysis pipeline |
| `analyze` | ✅ | ✅ | ✅ | ❌ | Analysis without rewriting |
| `transcript` | ✅ | ✅ | ❌ | ❌ | Just get the video text |
| `download` | ✅ | ❌ | ❌ | ❌ | Just download the video |

### Convenience Functions

```python
from skill import analyze_video, download_video, extract_transcript, score_virality

# Full analysis
result = analyze_video("https://v.douyin.com/xxxxx")

# Download only
result = download_video("https://www.youtube.com/watch?v=xxx")

# Transcript only
result = extract_transcript("https://xhslink.com/xxxxx")

# Virality score only
result = score_virality("https://www.bilibili.com/video/BVxxx")
```

---

## 🛠️ Mode 2: CLI Tool (Human Use)

Humans run `main.py` from the command line.

### Basic Usage

```bash
# Full analysis
python main.py "https://v.douyin.com/xxxxx"

# Download + transcript only
python main.py "https://v.douyin.com/xxxxx" --skip-analysis

# Custom output directory
python main.py "https://www.youtube.com/watch?v=xxx" -o ./results

# Accurate ASR model
python main.py video.mp4 --asr-mode accurate

# Use proxy
python main.py "https://xhslink.com/xxx" --proxy http://127.0.0.1:7890

# Specify rewrite styles
python main.py "https://b23.tv/xxx" --rewrite-styles storytelling emotional
```

### CLI Options

| Flag | Description | Default |
|------|-------------|---------|
| `input` | Video URL or local file path | (required) |
| `--output-dir, -o` | Output directory | `./output` |
| `--asr-mode` | `fast` or `accurate` | `fast` |
| `--asr-engine` | `whisper` or `funasr` | `whisper` |
| `--language, -l` | `auto`, `zh`, `en` | `auto` |
| `--skip-analysis` | Skip LLM analysis stages | `false` |
| `--rewrite-modes` | Space-separated: `light viral` | `light viral` |
| `--rewrite-styles` | Space-separated: `storytelling emotional` | `storytelling` |
| `--proxy` | HTTP proxy URL | (none) |
| `--verbose, -v` | Enable debug logging | `false` |

### Output Files

- `analysis_result.json` — Machine-readable structured JSON
- `analysis_report.md` — Human-readable Markdown report

---

## 🌐 Supported Platforms

| Platform | Download | Anti-Scraping | Notes |
|----------|----------|---------------|-------|
| 抖音 Douyin | API + yt-dlp + Playwright | XBogus, ABogus, Cookies | Video only |
| 小红书 Xiaohongshu | Page Parse + yt-dlp | `__INITIAL_STATE__` | **Video + Image/Text notes** |
| YouTube | yt-dlp Enhanced | Auto-subs, Chapters, h264 | Video only |
| TikTok | Crawler + yt-dlp | XBogus | Video only |
| Bilibili | Crawler + yt-dlp | W-RID | Video only |
| Instagram | yt-dlp + Page Parse | — | **Video + Image/Text notes** |
| Twitter/X | yt-dlp + Page Parse | — | **Video + Image/Text notes** |

### Xiaohongshu Image/Text Notes

For Xiaohongshu image+text notes (图文笔记):
- Automatically detects note type (video vs image/text)
- Extracts text content (title, description, hashtags)
- Uses vision-capable LLM to analyze images
- Combines text and image analysis for complete understanding
- Full pipeline support: summary, virality analysis, structure, rewrite

### Twitter/X Image/Text Notes

For Twitter/X tweets with images (图文推文):
- Uses yt-dlp `--dump-json` to fetch tweet metadata (no download for text/image tweets)
- Extracts tweet body text from metadata
- Uses vision-capable LLM to analyze attached images
- For video tweets: downloads the video and proceeds with ASR/subtitle extraction
- Full pipeline support: summary, virality analysis, structure, rewrite

## ⚙️ Configuration

Environment variables (`.env`):
- `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`
- `ASR_ENGINE` (funasr/whisper), `ASR_MODE` (fast/accurate)
- `DOUYIN_COOKIE_*` (ttwid, odin_tt, csrf_token, sessionid)
- `HTTP_PROXY`

### Vision LLM Configuration (for Image Analysis)

To enable image understanding for Xiaohongshu and Twitter/X image/text notes:

```ini
# Use a vision-capable model
LLM_MODEL=qwen3.6-plus
LLM_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
```

**Supported Vision Models:**
| Model | Provider | Base URL |
|-------|----------|----------|
| `qwen3.6-plus` | Alibaba DashScope | `https://coding.dashscope.aliyuncs.com/v1` |
| `qwen-vl-max` | Alibaba DashScope | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `gpt-4o` | OpenAI | `https://api.openai.com/v1` |
| `kimi-k2` | Moonshot | `https://api.moonshot.cn/v1` |
