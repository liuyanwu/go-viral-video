# 🎬 Go Viral Video — 视频爆款分析与改写神器

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

<div align="center">

[🇺🇸 English Version](README.md)

</div>

---

一个强大的跨平台视频分析与改写流水线工具。自动下载视频、提取文案、多维度评估爆款潜力、拆解叙事结构，并一键将内容改写为多种爆款风格。

> **双模式兼容**：既可作为 **AI Skill**（被 AI Agent 调用），也可作为 **CLI 命令行工具**（人工使用）。

## ⚡ 快速上手

### AI Agent 调用

```python
from skill import run_skill

result = run_skill({
    "url": "https://v.douyin.com/xxxxx",
    "mode": "full",                        # full | download | transcript | analyze
    "rewrite_modes": ["light", "viral"],
    "rewrite_styles": ["storytelling"],
})
```

### 四个便捷函数

```python
from skill import analyze_video, download_video, extract_transcript, score_virality

result = analyze_video("https://v.douyin.com/xxxxx")      # 全流程分析
result = download_video("https://youtube.com/watch?v=xxx") # 仅下载视频
result = extract_transcript("https://xhslink.com/xxxxx")   # 仅提取文案
result = score_virality("https://b23.tv/xxx")              # 仅评估爆款指数
```

### 输入输出 Schema

**输入参数:**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `url` | string | ✅ | 视频链接、图文笔记链接或本地文件路径 |
| `mode` | string | ❌ | `full`（默认）, `download`, `transcript`, `analyze` |
| `output_dir` | string | ❌ | 输出目录（默认：`./output`） |
| `asr_engine` | string | ❌ | `funasr`（默认）或 `whisper` |
| `rewrite_modes` | list | ❌ | `["light", "viral", "storytelling", "emotional", "educational", "promotional", "abstract", "prep", "scqa"]` |
| `rewrite_styles` | list | ❌ | `["storytelling", "emotional", "educational", "promotional", "prep", "scqa"]` |

**输出结构:**

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
    "message": "Video: xxx | Virality: 75/100 (high) | Rewrites: 3 variants"
}
```

### 完整示例

```python
from skill import run_skill

result = run_skill({
    "url": "https://v.douyin.com/iQs8eXqJLkP/",
    "mode": "full",
    "rewrite_modes": ["viral"],
    "rewrite_styles": ["storytelling"],
})

if result["success"]:
    data = result["data"]
    print(f"平台: {data['video']['platform']}")
    print(f"标题: {data['video']['title']}")
    print(f"爆款指数: {data['virality']['scores']['overall']}/100")
    print(f"爆款潜力: {data['virality']['viral_potential']}")
    print(f"钩子类型: {data['virality']['hook_type']}")
    print(f"文案字数: {data['transcript']['word_count']}")
    print(f"改写版本: {len(data['rewrites'])} 个")
```

**预期输出:**
```
平台: douyin
标题: 3个让你效率翻倍的AI工具
爆款指数: 78/100
爆款潜力: high
钩子类型: curiosity
文案字数: 485
改写版本: 2 个
```

---

## 🌟 核心亮点

- **🛡️ 多平台下载 + 反检测**：抖音三级降级策略（API → yt-dlp → Playwright），小红书 `__INITIAL_STATE__` 解析，YouTube 增强 yt-dlp
- **🌐 7 大平台支持**：抖音、小红书、YouTube、TikTok、B站、Instagram、Twitter/X
- **📊 5D 爆款评分 + 叙事结构拆解**：钩子、情绪、留存、CTA、社交货币五维评分，附带爆款建议
- **✍️ 多模式改写**：轻量、爆款、故事化、情绪化、教育型、推广型、抽象型、PREP（观点-原因-案例-观点）、SCQA（场景-冲突-问题-回答）— 9 种改写风格
- **🖼️ Vision LLM 图片分析**：支持小红书图文笔记、Twitter/X 图文推文的图片内容理解
- **🎤 FunASR 中文语音识别**：阿里 FunASR 中文优化，内置领域词表，支持 VAD 和标点恢复
- **🔌 双模式运行**：AI Skill + CLI 工具，一套代码两种用法

## 🏗️ 架构

```mermaid
graph TD
    A["输入链接 / 本地文件"] --> B["平台检测器"]
    
    B -->|抖音| C["抖音三级下载器"]
    B -->|小红书| X["小红书页面解析器"]
    B -->|YouTube| Y["YouTube 增强 yt-dlp"]
    B -->|TikTok/B站| T["专用爬虫"]
    B -->|其他| D["yt-dlp 通用下载"]
    
    C --> C1["T1: API 直连 (X-Bogus)"]
    C1 -->|失败| C2["T2: yt-dlp + Cookies"]
    C2 -->|失败| C3["T3: Playwright 浏览器"]
    
    X --> X1["T1: __INITIAL_STATE__ 解析"]
    X1 -->|失败| X2["T2: yt-dlp"]
    
    C1 & C2 & C3 & X1 & X2 & Y & T & D --> F["视频文件"]
    F --> G["字幕提取"]
    G -->|失败| H["ASR (Whisper/FunASR)"]
    G & H --> I["文本清洗"]
    I --> J["LLM 分析引擎"]
    
    J --> K["摘要"] & L["爆款评分 (0-100)"] & M["叙事结构"] & N["改写"]
    K & L & M & N --> O["结构化 JSON + Markdown"]
```

## 🌐 平台支持

| 平台 | 下载方式 | 反爬策略 | 字幕 | 特殊支持 |
|---|---|---|---|---|
| **抖音** | API → yt-dlp → Playwright | XBogus, ABogus, Cookies | ASR | 三级降级策略 |
| **小红书** | 页面解析 → yt-dlp | `__INITIAL_STATE__` | ASR / 笔记文字 | **图文笔记** |
| **YouTube** | 增强 yt-dlp | — | 自动字幕(中/英/日/韩) + 章节 | 优先 h264 |
| **TikTok** | 爬虫 + yt-dlp | XBogus | yt-dlp 自动字幕 / ASR | 短链解析 |
| **B站** | 爬虫 + yt-dlp | W-RID 签名 | API 字幕 / yt-dlp | — |
| **Instagram** | yt-dlp + 页面解析 | — | ASR | **图文帖子** |
| **Twitter/X** | yt-dlp + 页面解析 | — | ASR / **图文推文** | Vision LLM 图片分析 |

## 🚀 安装

```bash
git clone https://github.com/your-org/go-viral-video.git
cd go-viral-video
pip install -r requirements.txt

# 可选依赖
pip install openai-whisper           # ASR（英文/多语言）
pip install funasr modelscope        # ASR（中文优化，推荐）
pip install playwright && playwright install chromium  # 抖音降级方案
pip install browser-cookie3          # 自动读取浏览器 Cookie

cp .env.example .env                 # 编辑填入 LLM API Key
```

**系统要求**: FFmpeg 必须安装并加入 PATH。

## 💻 使用方法

### 模式一：CLI 命令行工具（人工使用）

```bash
# 全流程分析
python main.py https://www.youtube.com/watch?v=dQw4w9WgXcQ

# 分析抖音视频
python main.py https://v.douyin.com/xxxxx

# 分析小红书笔记
python main.py https://xhslink.com/xxxxx

# 分析 B站视频
python main.py https://b23.tv/xxx -o ./results --verbose

# 仅下载和转写
python main.py video.mp4 --asr-mode accurate --skip-analysis

# 指定改写风格
python main.py https://b23.tv/xxx --rewrite-styles storytelling emotional
```

### 模式二：AI Skill（Agent 调用）

```python
from skill import run_skill

# 全流程分析
result = run_skill({
    "url": "https://v.douyin.com/xxxxx",
    "mode": "full",   # full | download | transcript | analyze
})

# result["success"]  -> True/False
# result["data"]     -> 完整分析结果字典
# result["message"]  -> 可读摘要
```

### 模式 2b：Python 库函数

```python
from skill import analyze_video, download_video, extract_transcript, score_virality

result = analyze_video("https://www.youtube.com/watch?v=xxx")
result = download_video("https://v.douyin.com/xxxxx")
result = extract_transcript("https://xhslink.com/xxxxx")
result = score_virality("https://b23.tv/xxx")
```

### 四种执行模式

| 模式 | 下载 | 转写 | LLM 分析 | 改写 | 适用场景 |
|---|---|---|---|---|---|
| `full` | ✅ | ✅ | ✅ | ✅ | 完整分析流水线 |
| `analyze` | ✅ | ✅ | ✅ | ❌ | 只分析不改写 |
| `transcript` | ✅ | ✅ | ❌ | ❌ | 只需要文案文本 |
| `download` | ✅ | ❌ | ❌ | ❌ | 只需要下载视频 |

### 改写风格详解

| 风格 | 说明 | 适用场景 |
|---|---|---|
| `light` | 轻量微调，保留原文案结构 | 质量不错的原文，只需小幅优化 |
| `viral` | 爆款强化，放大钩子和情绪张力 | 追求传播量的爆款文案 |
| `storytelling` | 故事化叙事，用情节带动观众 | 知识分享、个人IP类内容 |
| `emotional` | 情绪驱动，引发共鸣 | 情感类、励志类内容 |
| `educational` | 教育型输出，清晰有逻辑 | 教程、干货类内容 |
| `promotional` | 推广型文案，突出卖点和CTA | 产品推广、带货类内容 |
| `abstract` | 抽象提炼，高阶概括 | 品牌理念、观点输出 |
| `prep` | **PREP 框架**：观点 → 原因 → 案例 → 观点循环，通过逻辑闭环建立说服力 | 需要建立信任感的说服类内容 |
| `scqa` | **SCQA 框架**：场景 → 冲突 → 问题 → 回答，以冲突驱动叙事 | 需要解决问题但避免说教的冲突类内容 |

## 🎤 ASR 设置

项目支持两种语音识别引擎。**中文内容推荐使用 FunASR。**

### 选项 A：FunASR（中文推荐）

FunASR 是阿里的开源语音识别工具，针对中文优化，内置 VAD 和标点恢复。

```bash
pip install funasr modelscope torchaudio

# 首次运行自动下载模型（约 2GB）:
# - paraformer-zh (ASR 模型)
# - fsmn-vad (语音活动检测)
# - ct-punc (标点恢复)
```

**使用:**
```bash
# 默认即为 FunASR
python main.py https://v.douyin.com/xxxxx

# 显式指定 FunASR
python main.py https://v.douyin.com/xxxxx --asr-engine funasr
```

**性能**: 2 分钟视频约 8-10 秒，RTF ~0.07，内存 ~2-3GB。

### 选项 B：Whisper（多语言）

```bash
pip install openai-whisper

# 使用
python main.py https://www.youtube.com/watch?v=xxx --asr-engine whisper
python main.py https://v.douyin.com/xxxxx --asr-engine whisper --asr-mode accurate
```

**模式:**
- `fast`: Whisper base 模型 (~139MB, 快速, 精度较低)
- `accurate`: Whisper large-v3 (~3GB, 较慢, 精度更高)

### ASR 配置

在 `.env` 中添加:
```ini
ASR_ENGINE=funasr        # funasr（推荐）或 whisper
ASR_MODE=fast            # fast 或 accurate（仅 whisper）
```

## 🍪 Cookie 配置

抖音有严格的反爬机制。配置浏览器 Cookie 可确保最高下载成功率（使用 T1/T2 接口直接下载无水印原画）。

### 方法一：自动读取（推荐）

```bash
pip install browser-cookie3
```

安装后，程序会自动安全读取本地 Chrome/Edge 浏览器的抖音 Cookie，无需手动配置。

### 方法二：手动配置（.env 文件）

如果在服务器上运行，需手动提供 Cookie。

1. 打开 Chrome/Edge，访问 `https://www.douyin.com`
2. 登录账号（强烈建议）
3. 按 `F12` 打开开发者工具 → **Application**（或 **Storage**）标签
4. 左侧展开 **Cookies** → 点击 `https://www.douyin.com`
5. 找到以下键的值并复制到 `.env`:
   - `ttwid` → `DOUYIN_COOKIE_TTWID`
   - `odin_tt` → `DOUYIN_COOKIE_ODIN_TT`
   - `passport_csrf_token` → `DOUYIN_COOKIE_CSRF_TOKEN`
   - `sessionid` → `DOUYIN_COOKIE_SESSIONID`（登录后才有）

```ini
DOUYIN_COOKIE_TTWID=1%7Cxxxxxx
DOUYIN_COOKIE_ODIN_TT=xxxxxx
DOUYIN_COOKIE_CSRF_TOKEN=xxxxxx
DOUYIN_COOKIE_SESSIONID=xxxxxx
```

## 📋 输出示例

### JSON 输出 (`analysis_result.json`)

```json
{
  "video": {
    "platform": "douyin",
    "title": "3个让你效率翻倍的AI工具",
    "author": "@AI达人",
    "duration_seconds": 45
  },
  "transcript": {
    "source": "asr",
    "language": "zh",
    "cleaned_text": "今天给大家分享三个超好用的AI工具...",
    "word_count": 485
  },
  "summary": {
    "one_sentence": "介绍三款提升工作效率的AI工具及其核心功能",
    "key_points": ["工具一：智能写作助手", "工具二：自动PPT生成", "工具三：会议纪要AI"]
  },
  "virality": {
    "scores": {
      "hook": 85,
      "emotion": 70,
      "retention": 75,
      "cta": 60,
      "social_currency": 80,
      "overall": 75
    },
    "hook_type": "curiosity",
    "viral_potential": "high",
    "go_viral_advice": "开头钩子很强，建议在30秒处增加互动提问提升留存"
  },
  "structure": {
    "hook": { "text": "今天给大家分享...", "timestamp": "0:00-0:05", "technique": "curiosity_gap" },
    "setup": { "text": "第一个工具是...", "timestamp": "0:05-0:15" },
    "conflict": { "text": "很多人不知道的是...", "timestamp": "0:15-0:25" },
    "climax": { "text": "最厉害的功能是...", "timestamp": "0:25-0:35" },
    "cta": { "text": "点赞收藏，下期继续分享", "timestamp": "0:40-0:45" }
  },
  "rewrites": {
    "light": { "title": "...", "script": "..." },
    "viral": { "title": "...", "script": "..." },
    "style_variants": [
      { "style": "storytelling", "title": "...", "script": "..." },
      { "style": "emotional", "title": "...", "script": "..." }
    ]
  }
}
```

### Markdown 报告 (`analysis_report.md`)

```markdown
# 📊 视频分析报告

## 基本信息
- **平台**: 抖音
- **标题**: 3个让你效率翻倍的AI工具
- **作者**: @AI达人
- **时长**: 45秒

## 📈 爆款评分: 75/100 (高)

| 维度 | 分数 |
|---|---|
| 钩子 | 85 |
| 情绪 | 70 |
| 留存 | 75 |
| CTA | 60 |
| 社交货币 | 80 |

## 💡 爆款建议
开头钩子很强，建议在30秒处增加互动提问提升留存。

## ✍️ 改写版本
### 爆款模式
**标题**: 打工人必看！这3个AI工具让我每天少加班2小时...
**正文**: [改写后的完整文案]
```

## 🔧 故障排查

### FFmpeg 未找到
**错误**: `ffmpeg not found`
**解决**:
- Windows: `choco install ffmpeg` 或从 https://ffmpeg.org/ 下载
- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

### LLM API 认证失败
**错误**: `Authentication error` 或 `Invalid API key`
**解决**:
1. 检查 `.env` 中的 `LLM_API_KEY`
2. 确认 `LLM_BASE_URL` 正确
3. 测试: `curl -H "Authorization: Bearer $LLM_API_KEY" $LLM_BASE_URL/models`

### 抖音下载失败
**错误**: `All Douyin download methods failed`
**解决**:
1. 在 `.env` 中配置 Cookie: `DOUYIN_COOKIE_TTWID=...`
2. 使用代理: `--proxy http://127.0.0.1:7890`
3. 更新 yt-dlp: `pip install -U yt-dlp`

### YouTube 403 禁止
**错误**: `HTTP Error 403: Forbidden`
**解决**: 使用代理或浏览器 Cookie: `--cookies-from-browser chrome`

### FunASR 模型下载卡住
**解决**: 模型从 ModelScope 下载，如在中国大陆请使用代理。

### 长视频内存不足
**解决**: 流水线自动分段处理 >5 分钟视频。超长视频可在配置中增大 chunk 大小。

### 缓存问题
**解决**: 清除缓存: `rm -rf output/.cache/`

## 📜 开源协议

Apache-2.0 License. 详见 [LICENSE](LICENSE) 文件。
