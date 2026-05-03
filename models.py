"""
Pydantic v2 data models for the Video Viral Analyzer & Rewriter.
Defines the structured JSON output schema for the entire pipeline.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class Platform(str, Enum):
    DOUYIN = "douyin"
    TIKTOK = "tiktok"
    BILIBILI = "bilibili"
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    KUAISHOU = "kuaishou"
    XIAOHONGSHU = "xiaohongshu"
    LOCAL = "local"
    UNKNOWN = "unknown"


class HookType(str, Enum):
    CURIOSITY = "curiosity"         # 好奇心
    SHOCK = "shock"                 # 震惊/反转
    CONFLICT = "conflict"           # 冲突/争议
    NOVELTY = "novelty"             # 新奇/罕见
    PAIN_POINT = "pain_point"       # 痛点共鸣
    STORYTELLING = "storytelling"   # 故事牵引
    QUESTION = "question"           # 提问式
    DATA = "data"                   # 数据/事实


class RewriteMode(str, Enum):
    LIGHT = "light"                 # 轻改 — 换词不换意
    VIRAL = "viral"                 # 爆款改 — 强化钩子/节奏/CTA
    STYLE = "style"                 # 风格改 — 变换叙事风格


class RewriteStyle(str, Enum):
    STORYTELLING = "storytelling"   # 故事叙述
    EMOTIONAL = "emotional"         # 情感共鸣
    EDUCATIONAL = "educational"     # 知识科普
    PROMOTIONAL = "promotional"     # 营销推广
    ABSTRACT = "abstract"           # 抽象表达


class SubtitleSource(str, Enum):
    EMBEDDED = "embedded"           # FFmpeg extracted
    PLATFORM = "platform"           # yt-dlp / platform API
    OCR = "ocr"                     # RapidOCR
    ASR = "asr"                     # Whisper / FunASR
    MANUAL = "manual"               # User provided


# ──────────────────────────────────────────────
# Video & Download
# ──────────────────────────────────────────────

class VideoInfo(BaseModel):
    """Metadata about the downloaded video."""
    url: str = Field(description="Original input URL")
    platform: Platform = Field(description="Detected platform")
    video_id: str = Field(default="", description="Platform-specific video ID")
    title: str = Field(default="", description="Video title")
    author: str = Field(default="", description="Author/creator name")
    duration_seconds: float = Field(default=0, description="Video duration in seconds")
    local_path: str = Field(default="", description="Local file path after download")
    download_method: str = Field(default="", description="Method used to download")
    downloaded_at: Optional[datetime] = None


# ──────────────────────────────────────────────
# Transcript
# ──────────────────────────────────────────────

class SubtitleSegment(BaseModel):
    """A single timed subtitle segment."""
    index: int = 0
    start_time: str = "00:00:00,000"   # SRT format
    end_time: str = "00:00:00,000"
    text: str = ""


class TranscriptResult(BaseModel):
    """Raw and cleaned transcript data."""
    source: SubtitleSource = Field(description="How the transcript was obtained")
    language: str = Field(default="auto", description="Detected language code")
    raw_segments: List[SubtitleSegment] = Field(default_factory=list)
    raw_text: str = Field(default="", description="Raw concatenated text from ASR/subtitles")
    cleaned_text: str = Field(default="", description="Cleaned, normalized text")
    corrected_text: str = Field(default="", description="LLM-corrected transcript (ASR error fixed)")
    srt_path: Optional[str] = Field(default=None, description="Path to SRT file")


# ──────────────────────────────────────────────
# Summary
# ──────────────────────────────────────────────

class ChapterMark(BaseModel):
    """A chapter/section marker with timestamp."""
    timestamp: str = ""
    title: str = ""
    summary: str = ""


class ContentSummary(BaseModel):
    """LLM-generated content summary."""
    one_sentence: str = Field(default="", description="TL;DR in one sentence")
    key_points: List[str] = Field(default_factory=list, description="3-5 key takeaways")
    chapters: List[ChapterMark] = Field(default_factory=list, description="Timeline chapters")
    target_audience: str = Field(default="", description="Who this content is for")
    content_type: str = Field(default="", description="e.g. tutorial, vlog, review")


# ──────────────────────────────────────────────
# Virality Analysis
# ──────────────────────────────────────────────

class ViralityScores(BaseModel):
    """Quantified virality scores (0-100)."""
    hook: int = Field(ge=0, le=100, description="Hook effectiveness")
    emotion: int = Field(ge=0, le=100, description="Emotional trigger strength")
    retention: int = Field(ge=0, le=100, description="Audience retention / pacing")
    cta: int = Field(ge=0, le=100, description="Call-to-action effectiveness")
    social_currency: int = Field(ge=0, le=100, description="Shareability / social value")
    overall: int = Field(ge=0, le=100, description="Weighted composite score")


class ViralityAnalysis(BaseModel):
    """Full virality analysis result."""
    scores: ViralityScores = Field(default_factory=lambda: ViralityScores(hook=0, emotion=0, retention=0, cta=0, social_currency=0, overall=0))
    hook_type: HookType = HookType.CURIOSITY
    hook_text: str = Field(default="", description="The actual hook text/phrase")
    strengths: List[str] = Field(default_factory=list, description="What works well")
    weaknesses: List[str] = Field(default_factory=list, description="What could improve")
    explanation: str = Field(default="", description="Natural language analysis")
    viral_potential: str = Field(default="", description="low/medium/high/very_high")


# ──────────────────────────────────────────────
# Structure Breakdown
# ──────────────────────────────────────────────

class StructureSection(BaseModel):
    """A section of the content structure."""
    name: str = ""                      # e.g. "hook", "setup", "conflict"
    text: str = ""                      # The actual text of this section
    timestamp_start: str = ""
    timestamp_end: str = ""
    purpose: str = ""                   # Why this section works


class ContentStructure(BaseModel):
    """Narrative structure breakdown."""
    hook: StructureSection = Field(default_factory=StructureSection)
    setup: StructureSection = Field(default_factory=StructureSection)
    conflict: StructureSection = Field(default_factory=StructureSection)
    climax: StructureSection = Field(default_factory=StructureSection)
    cta: StructureSection = Field(default_factory=StructureSection)
    rhetorical_devices: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    narrative_style: str = Field(default="", description="Overall narrative style")


class GoViralTip(BaseModel):
    """A single actionable tip to improve virality."""
    category: str = Field(description="Category: hook, pacing, emotion, cta, title, thumbnail, timing, engagement")
    priority: str = Field(description="high / medium / low")
    title: str = Field(description="Short tip title")
    description: str = Field(description="Detailed explanation of what to do and why")
    example: str = Field(default="", description="Concrete example of how to implement")


class GoViralAdvice(BaseModel):
    """Actionable recommendations to maximize content virality."""
    overall_strategy: str = Field(default="", description="1-2 sentence overall strategy")
    top_3_actions: List[str] = Field(default_factory=list, description="Top 3 highest-impact actions to take")
    tips: List[GoViralTip] = Field(default_factory=list, description="Detailed actionable tips")
    title_suggestions: List[str] = Field(default_factory=list, description="3-5 alternative title suggestions")
    hook_alternatives: List[str] = Field(default_factory=list, description="2-3 alternative hook suggestions")
    platform_tips: List[str] = Field(default_factory=list, description="Platform-specific optimization tips")


# ──────────────────────────────────────────────
# Rewrite
# ──────────────────────────────────────────────

class RewriteVariant(BaseModel):
    """A single rewrite variant."""
    mode: RewriteMode = RewriteMode.LIGHT
    style: Optional[RewriteStyle] = None
    title: str = Field(default="", description="Rewritten title")
    script: str = Field(default="", description="Full rewritten script")
    hook: str = Field(default="", description="Rewritten hook (first 3-5s)")
    cta: str = Field(default="", description="Rewritten call-to-action")
    word_count: int = 0
    changes_summary: str = Field(default="", description="What was changed and why")


class RewriteResult(BaseModel):
    """All rewrite variants."""
    light: Optional[RewriteVariant] = None
    viral: Optional[RewriteVariant] = None
    style_variants: List[RewriteVariant] = Field(default_factory=list)


# ──────────────────────────────────────────────
# Top-level Output
# ──────────────────────────────────────────────

class AnalysisResult(BaseModel):
    """
    Top-level analysis result combining all pipeline outputs.
    This is the final structured JSON output of the entire system.
    """
    version: str = "1.0.0"
    generated_at: datetime = Field(default_factory=datetime.now)

    # Pipeline stages
    video: VideoInfo
    transcript: TranscriptResult
    summary: Optional[ContentSummary] = None
    virality: Optional[ViralityAnalysis] = None
    structure: Optional[ContentStructure] = None
    go_viral: Optional[GoViralAdvice] = None
    rewrites: Optional[RewriteResult] = None

    # Processing metadata
    processing_time_seconds: float = 0
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    def to_json_file(self, path: str) -> str:
        """Save to JSON file."""
        from pathlib import Path as P
        p = P(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.model_dump_json(indent=2, exclude_none=True), encoding="utf-8")
        return str(p)

    def to_markdown(self) -> str:
        """Generate a human-readable Markdown report."""
        lines = []
        lines.append(f"# 📊 Video Viral Analysis Report")
        lines.append(f"")
        lines.append(f"**Generated:** {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Processing Time:** {self.processing_time_seconds:.1f}s")
        lines.append(f"")

        # Video info
        lines.append(f"## 🎬 Video Info")
        lines.append(f"- **URL:** {self.video.url}")
        lines.append(f"- **Platform:** {self.video.platform.value}")
        lines.append(f"- **Title:** {self.video.title or 'N/A'}")
        lines.append(f"- **Author:** {self.video.author or 'N/A'}")
        lines.append(f"- **Duration:** {self.video.duration_seconds:.0f}s")
        lines.append(f"")

        # Transcript
        lines.append(f"## 📝 Transcript")
        lines.append(f"- **Source:** {self.transcript.source.value}")
        lines.append(f"- **Language:** {self.transcript.language}")
        lines.append(f"")

        # Original raw transcript (never truncated)
        if self.transcript.raw_text:
            lines.append(f"### Original Transcript (ASR Raw)")
            lines.append(f"```")
            lines.append(self.transcript.raw_text)
            lines.append(f"```")
            lines.append(f"")

        # Corrected transcript
        if self.transcript.corrected_text:
            lines.append(f"### Corrected Transcript")
            lines.append(f"```")
            lines.append(self.transcript.corrected_text)
            lines.append(f"```")
            lines.append(f"")
        elif self.transcript.cleaned_text:
            lines.append(f"### Cleaned Transcript")
            lines.append(f"```")
            lines.append(self.transcript.cleaned_text)
            lines.append(f"```")
            lines.append(f"")

        # Summary
        if self.summary:
            lines.append(f"## 📋 Summary")
            lines.append(f"**{self.summary.one_sentence}**")
            lines.append(f"")
            if self.summary.key_points:
                lines.append(f"### Key Points")
                for point in self.summary.key_points:
                    lines.append(f"- {point}")
                lines.append(f"")

        # Virality
        if self.virality:
            v = self.virality
            lines.append(f"## 🔥 Virality Analysis")
            lines.append(f"### Scores")
            lines.append(f"| Dimension | Score |")
            lines.append(f"|-----------|-------|")
            lines.append(f"| 🎣 Hook | {v.scores.hook}/100 |")
            lines.append(f"| 💖 Emotion | {v.scores.emotion}/100 |")
            lines.append(f"| ⏱️ Retention | {v.scores.retention}/100 |")
            lines.append(f"| 📢 CTA | {v.scores.cta}/100 |")
            lines.append(f"| 🌐 Social Currency | {v.scores.social_currency}/100 |")
            lines.append(f"| **🏆 Overall** | **{v.scores.overall}/100** |")
            lines.append(f"")
            lines.append(f"**Hook Type:** {v.hook_type.value}")
            lines.append(f"**Viral Potential:** {v.viral_potential}")
            lines.append(f"")
            if v.explanation:
                lines.append(f"### Analysis")
                lines.append(f"{v.explanation}")
                lines.append(f"")

        # Structure
        if self.structure:
            lines.append(f"## 🏗️ Content Structure")
            for section_name in ["hook", "setup", "conflict", "climax", "cta"]:
                section = getattr(self.structure, section_name)
                if section and section.text:
                    lines.append(f"### {section_name.title()}")
                    lines.append(f"{section.text}")
                    if section.purpose:
                        lines.append(f"*Purpose: {section.purpose}*")
                    lines.append(f"")

        # Rewrites
        if self.rewrites:
            lines.append(f"## ✍️ Rewrites")
            if self.rewrites.light:
                lines.append(f"### Light Rewrite")
                lines.append(f"{self.rewrites.light.script}")
                lines.append(f"")
            if self.rewrites.viral:
                lines.append(f"### Viral Rewrite")
                lines.append(f"{self.rewrites.viral.script}")
                lines.append(f"")
            for sv in self.rewrites.style_variants:
                lines.append(f"### Style: {sv.style.value if sv.style else 'custom'}")
                lines.append(f"{sv.script}")
                lines.append(f"")

        # Go Viral Advice
        if self.go_viral:
            g = self.go_viral
            lines.append(f"## 🚀 Go Viral 优化建议")
            if g.overall_strategy:
                lines.append(f"**整体策略:** {g.overall_strategy}")
                lines.append(f"")
            if g.top_3_actions:
                lines.append(f"### 🔥 Top 3 关键行动")
                for i, action in enumerate(g.top_3_actions, 1):
                    lines.append(f"{i}. {action}")
                lines.append(f"")
            if g.tips:
                lines.append(f"### 💡 详细建议")
                for tip in g.tips:
                    priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(tip.priority, "⚪")
                    lines.append(f"#### {priority_icon} [{tip.category}] {tip.title}")
                    lines.append(f"{tip.description}")
                    if tip.example:
                        lines.append(f"*示例: {tip.example}*")
                    lines.append(f"")
            if g.title_suggestions:
                lines.append(f"### 📝 标题建议")
                for t in g.title_suggestions:
                    lines.append(f"- {t}")
                lines.append(f"")
            if g.hook_alternatives:
                lines.append(f"### 🎣 钩子替代建议")
                for h in g.hook_alternatives:
                    lines.append(f"- {h}")
                lines.append(f"")
            if g.platform_tips:
                lines.append(f"### 📱 平台优化建议")
                for t in g.platform_tips:
                    lines.append(f"- {t}")
                lines.append(f"")

        # Errors
        if self.errors:
            lines.append(f"## ⚠️ Errors")
            for err in self.errors:
                lines.append(f"- {err}")
            lines.append(f"")

        return "\n".join(lines)
