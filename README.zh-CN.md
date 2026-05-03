# 视频爆款分析与改写神器 (Video Viral Analyzer & Rewriter)

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

一个强大的跨平台视频分析与改写流水线工具。支持自动下载视频、提取字幕、多维度（5D）评估爆款潜力、拆解叙事结构，并一键将文案改写为多种爆款风格。

> **双模式兼容**：既可作为 **AI Skill**（被 AI Agent 调用），也可作为 **CLI 命令行工具**（人工使用）。

[English Documentation](README.md) | [Skill 接口文档](SKILL.md)

## 🎯 支持平台

| 平台 | 下载方式 | 字幕来源 | 特殊支持 |
|------|---------|---------|---------|
| **抖音** | API直连 → yt-dlp → 浏览器接管 | ASR | XBogus/ABogus签名 |
| **小红书** | 页面解析 → yt-dlp | ASR / 笔记文字 / **图文笔记** | `__INITIAL_STATE__` 提取，**Vision LLM 图片分析** |
| **YouTube** | yt-dlp 增强模式 | 自动字幕(中/英/日/韩) + 章节 | h264优先 |
| **TikTok** | 爬虫 + yt-dlp | yt-dlp 自动字幕 / ASR | 短链解析 |
| **B站** | 爬虫 + yt-dlp | API字幕 / yt-dlp | W-RID签名 |
| **Instagram** | yt-dlp + 页面解析 | ASR | Reels，**图文帖子** |
| **Twitter/X** | yt-dlp + 页面解析 | ASR / **图文推文** | 视频 + 图文推文，**Vision LLM 图片分析** |

### 🖼️ 图文笔记支持

流水线全面支持小红书和 Twitter/X 的图文笔记：

1. **小红书图文笔记**：自动提取标题、描述和标签，使用 Vision LLM 分析图片内容
2. **Twitter/X 图文推文**：通过 yt-dlp 获取推文元数据，提取文字并分析附带图片
3. **Instagram 图文帖子**：支持图片帖子的文字提取和图片分析

**图片分析要求：**
- 需要使用支持 Vision 的大模型（如 `qwen3.6-plus`、`gpt-4o` 等）
- 在 `.env` 中配置：
  ```ini
  LLM_MODEL=qwen3.6-plus
  LLM_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
  ```

## 🚀 安装

```bash
git clone https://github.com/your-org/go-viral-video.git
cd go-viral-video
pip install -r requirements.txt

# 可选依赖
pip install openai-whisper           # 语音识别
pip install playwright && playwright install chromium  # 抖音浏览器接管

cp .env.example .env                 # 填入大模型 API Key
```

**系统要求**：必须安装 `FFmpeg` 并配置 PATH。

### 🍪 配置 Cookie 指南（破解抖音反爬的关键）

为了确保下载的最高成功率和速度（使用 T1/T2 接口直接下载无水印原画），建议配置浏览器的 Cookie。

**✨ 方法一：全自动读取（极度推荐）**
只需要安装可选依赖 `browser-cookie3`：
```bash
pip install browser-cookie3
```
只要安装了它，且您在本地 Chrome 或 Edge 浏览器中访问过抖音，代码就会**自动读取并加载 Cookie**，彻底免去手动抓包填写的烦恼！

**⚙️ 方法二：手动抓包填入 (.env 文件)**
如果您部署在云端服务器，或者方法一失效，您需要手动配置：
1. 打开 Chrome 或 Edge 浏览器，访问 `https://www.douyin.com`。
2. （强烈建议）扫码登录您的账号，这能极大提高风控存活率。
3. 按 `F12` 打开开发者工具，切换到 **Application**（应用程序） 或 **Storage**（存储） 标签页。
4. 在左侧面板展开 **Cookies**，点击 `https://www.douyin.com`。
5. 找到以下 4 个键对应的值，并复制到您的 `.env` 文件中：
   - `ttwid`
   - `odin_tt`
   - `passport_csrf_token` （在 .env 中对应 `DOUYIN_COOKIE_CSRF_TOKEN`）
   - `sessionid` （登录后才有）

您的 `.env` 文件配置好后应该类似这样：
```ini
DOUYIN_COOKIE_TTWID=1%7Cxxxxxx
DOUYIN_COOKIE_ODIN_TT=xxxxxx
DOUYIN_COOKIE_CSRF_TOKEN=xxxxxx
DOUYIN_COOKIE_SESSIONID=xxxxxx
```

## 💻 使用方法

### 模式一：命令行工具（人工使用）

```bash
# 全流程分析
python main.py https://www.youtube.com/watch?v=dQw4w9WgXcQ

# 分析抖音视频
python main.py https://v.douyin.com/xxxxx

# 分析小红书视频笔记
python main.py https://xhslink.com/xxxxx

# 分析 B站视频
python main.py https://www.bilibili.com/video/BV1xx411c7mD

# 仅下载和转写
python main.py video.mp4 --skip-analysis --asr-mode accurate
```

### 模式二：AI Skill（Agent 调用）

```python
from skill import run_skill

# 全流程分析
result = run_skill({
    "url": "https://v.douyin.com/xxxxx",
    "mode": "full",   # full | download | transcript | analyze
})

print(result["success"])   # True/False
print(result["data"])      # 完整分析结果
print(result["message"])   # 可读摘要
```

### 模式 2b：Python 库函数

```python
from skill import analyze_video, download_video, extract_transcript, score_virality

# 一键全分析
result = analyze_video("https://www.youtube.com/watch?v=xxx")

# 仅下载视频
result = download_video("https://v.douyin.com/xxxxx")

# 仅提取文案
result = extract_transcript("https://xhslink.com/xxxxx")

# 仅评估爆款指数
result = score_virality("https://b23.tv/xxx")
```

### 四种执行模式

| 模式 | 下载 | 转写 | LLM分析 | 改写 | 适用场景 |
|------|------|------|---------|------|---------|
| `full` | ✅ | ✅ | ✅ | ✅ | 完整分析流水线 |
| `analyze` | ✅ | ✅ | ✅ | ❌ | 只分析不改写 |
| `transcript` | ✅ | ✅ | ❌ | ❌ | 只需要文案文本 |
| `download` | ✅ | ❌ | ❌ | ❌ | 只需要下载视频 |

完整 Skill 输入输出 Schema 见 [SKILL.md](SKILL.md)。

## 📜 开源协议

Apache-2.0 License. 详情请参阅 `LICENSE`。
