"""
Comprehensive mock tests for LLM-dependent modules.

Tests Summarizer, ViralityAnalyzer, StructureAnalyzer, Rewriter,
ASRCorrector, and LLMClient by mocking the OpenAI SDK and/or
utils.llm_client.LLMClient.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import reset_config
from models import (
    ContentSummary,
    ViralityAnalysis,
    ViralityScores,
    HookType,
    ContentStructure,
    StructureSection,
    RewriteResult,
    RewriteVariant,
    RewriteMode,
    RewriteStyle,
)


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

SAMPLE_TRANSCRIPT = """
你知道吗？2024年AI的发展速度超出了所有人的想象。
首先，大语言模型的能力有了质的飞跃。GPT-4o、Claude 3.5、Qwen 2.5
都在多模态理解上取得了突破。
其次，AI Agent开始真正落地。从自动化办公到智能客服，
AI正在改变我们的工作方式。
最后，开源模型的性能已经接近闭源模型，这让更多人能够使用AI技术。
如果你觉得这期内容有用，请点赞关注，我们下期再见！
"""


@pytest.fixture(autouse=True)
def isolate_config():
    """Reset config before each test to avoid state leakage."""
    reset_config()
    with patch("config._config") as mock_cfg:
        mock_cfg.llm.base_url = "https://example.com/v1"
        mock_cfg.llm.api_key = "test-api-key"
        mock_cfg.llm.model = "test-model"
        mock_cfg.llm.max_tokens = 4096
        mock_cfg.llm.temperature = 0.7
        mock_cfg.asr.engine = "funasr"
        mock_cfg.asr.mode = "fast"
        mock_cfg.output_dir = Path("./output")
        mock_cfg.max_transcript_chars = 50000
        mock_cfg.default_language = "auto"
        mock_cfg.enable_asr_correction = True
        yield mock_cfg
    reset_config()


def _make_mock_llm_client():
    """Create a mock LLMClient instance with chat_structured method."""
    mock_instance = MagicMock()
    return mock_instance


# ──────────────────────────────────────────────
# TestSummarizer
# ──────────────────────────────────────────────

class TestSummarizer:
    def test_summarize_success(self):
        from modules.summarizer import Summarizer

        mock_summary = {
            "one_sentence": "2024年AI发展迅速，多模态和Agent落地是亮点",
            "key_points": ["大语言模型能力飞跃", "AI Agent真正落地", "开源模型接近闭源"],
            "chapters": [],
            "target_audience": "科技爱好者和开发者",
            "content_type": "科普",
        }

        with patch("modules.summarizer.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_structured.return_value = ContentSummary(**mock_summary)
            mock_get_client.return_value = mock_client

            summarizer = Summarizer()
            result = summarizer.summarize(SAMPLE_TRANSCRIPT)

            assert isinstance(result, ContentSummary)
            assert "AI" in result.one_sentence
            assert len(result.key_points) == 3
            assert result.target_audience != ""
            assert result.content_type != ""

    def test_summarize_with_chapters(self):
        from modules.summarizer import Summarizer

        mock_summary = {
            "one_sentence": "AI技术综述",
            "key_points": ["模型进步", "应用落地"],
            "chapters": [
                {"timestamp": "00:00", "title": "引言", "summary": "介绍AI发展"},
                {"timestamp": "01:00", "title": "模型", "summary": "大模型能力"},
            ],
            "target_audience": "大众",
            "content_type": "教程",
        }

        with patch("modules.summarizer.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_structured.return_value = ContentSummary(**mock_summary)
            mock_get_client.return_value = mock_client

            summarizer = Summarizer()
            result = summarizer.summarize(SAMPLE_TRANSCRIPT)

            assert isinstance(result, ContentSummary)
            assert len(result.chapters) == 2
            assert result.chapters[0].title == "引言"

    def test_summarize_llm_error(self):
        from modules.summarizer import Summarizer

        with patch("modules.summarizer.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_structured.side_effect = Exception("LLM API error")
            mock_get_client.return_value = mock_client

            summarizer = Summarizer()
            with pytest.raises(Exception, match="LLM API error"):
                summarizer.summarize(SAMPLE_TRANSCRIPT)


# ──────────────────────────────────────────────
# TestViralityAnalyzer
# ──────────────────────────────────────────────

class TestViralityAnalyzer:
    def test_analyze_success(self):
        from modules.virality_analyzer import ViralityAnalyzer

        mock_analysis = {
            "scores": {
                "hook": 75,
                "emotion": 60,
                "retention": 80,
                "cta": 70,
                "social_currency": 65,
                "overall": 72,
            },
            "hook_type": "curiosity",
            "hook_text": "你知道吗？2024年AI的发展速度超出了所有人的想象",
            "strengths": ["开头使用疑问句引发好奇", "信息密度高"],
            "weaknesses": ["CTA较为常规", "情感共鸣不足"],
            "explanation": "该视频以好奇心驱动开头，信息结构清晰",
            "viral_potential": "medium",
        }

        with patch("modules.virality_analyzer.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_structured.return_value = ViralityAnalysis(**mock_analysis)
            mock_get_client.return_value = mock_client

            analyzer = ViralityAnalyzer()
            result = analyzer.analyze(SAMPLE_TRANSCRIPT)

            assert isinstance(result, ViralityAnalysis)
            assert isinstance(result.scores, ViralityScores)
            assert result.scores.hook == 75
            assert result.scores.overall == 72
            assert result.hook_type == HookType.CURIOSITY
            assert len(result.strengths) == 2
            assert result.viral_potential == "medium"

    def test_analyze_high_viral_potential(self):
        from modules.virality_analyzer import ViralityAnalyzer

        mock_analysis = {
            "scores": {
                "hook": 95,
                "emotion": 90,
                "retention": 92,
                "cta": 88,
                "social_currency": 85,
                "overall": 90,
            },
            "hook_type": "shock",
            "hook_text": "震惊！AI已经能做到这个程度",
            "strengths": ["极强的开头钩子", "情感共鸣强烈"],
            "weaknesses": [],
            "explanation": "爆款结构完整",
            "viral_potential": "very_high",
        }

        with patch("modules.virality_analyzer.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_structured.return_value = ViralityAnalysis(**mock_analysis)
            mock_get_client.return_value = mock_client

            analyzer = ViralityAnalyzer()
            result = analyzer.analyze(SAMPLE_TRANSCRIPT)

            assert result.viral_potential == "very_high"
            assert result.scores.overall == 90
            assert result.hook_type == HookType.SHOCK

    def test_analyze_llm_error(self):
        from modules.virality_analyzer import ViralityAnalyzer

        with patch("modules.virality_analyzer.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_structured.side_effect = Exception("Rate limit exceeded")
            mock_get_client.return_value = mock_client

            analyzer = ViralityAnalyzer()
            with pytest.raises(Exception, match="Rate limit exceeded"):
                analyzer.analyze(SAMPLE_TRANSCRIPT)


# ──────────────────────────────────────────────
# TestStructureAnalyzer
# ──────────────────────────────────────────────

class TestStructureAnalyzer:
    def test_analyze_success(self):
        from modules.structure_analyzer import StructureAnalyzer

        mock_structure = {
            "hook": {
                "name": "hook",
                "text": "你知道吗？2024年AI的发展速度超出了所有人的想象",
                "timestamp_start": "00:00",
                "timestamp_end": "00:05",
                "purpose": "用疑问句激发好奇心",
            },
            "setup": {
                "name": "setup",
                "text": "首先，大语言模型的能力有了质的飞跃",
                "timestamp_start": "00:05",
                "timestamp_end": "00:15",
                "purpose": "建立背景信息",
            },
            "conflict": {
                "name": "conflict",
                "text": "AI Agent开始真正落地",
                "timestamp_start": "00:15",
                "timestamp_end": "00:25",
                "purpose": "展示变化与冲击",
            },
            "climax": {
                "name": "climax",
                "text": "开源模型的性能已经接近闭源模型",
                "timestamp_start": "00:25",
                "timestamp_end": "00:35",
                "purpose": "核心观点呈现",
            },
            "cta": {
                "name": "cta",
                "text": "如果你觉得这期内容有用，请点赞关注",
                "timestamp_start": "00:35",
                "timestamp_end": "00:40",
                "purpose": "引导互动",
            },
            "rhetorical_devices": ["设问", "排比", "对比"],
            "keywords": ["AI", "大语言模型", "Agent", "开源"],
            "narrative_style": "科普讲解",
        }

        with patch("modules.structure_analyzer.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_structured.return_value = ContentStructure(**mock_structure)
            mock_get_client.return_value = mock_client

            analyzer = StructureAnalyzer()
            result = analyzer.analyze(SAMPLE_TRANSCRIPT)

            assert isinstance(result, ContentStructure)
            assert isinstance(result.hook, StructureSection)
            assert result.hook.text != ""
            assert len(result.rhetorical_devices) == 3
            assert len(result.keywords) == 4
            assert result.narrative_style == "科普讲解"

    def test_analyze_partial_structure(self):
        from modules.structure_analyzer import StructureAnalyzer

        mock_structure = {
            "hook": {
                "name": "hook",
                "text": "AI改变世界",
                "timestamp_start": "00:00",
                "timestamp_end": "00:03",
                "purpose": "直接点题",
            },
            "setup": {"name": "setup", "text": "", "timestamp_start": "", "timestamp_end": "", "purpose": ""},
            "conflict": {"name": "conflict", "text": "", "timestamp_start": "", "timestamp_end": "", "purpose": ""},
            "climax": {"name": "climax", "text": "", "timestamp_start": "", "timestamp_end": "", "purpose": ""},
            "cta": {"name": "cta", "text": "", "timestamp_start": "", "timestamp_end": "", "purpose": ""},
            "rhetorical_devices": ["直述"],
            "keywords": ["AI"],
            "narrative_style": "直述",
        }

        with patch("modules.structure_analyzer.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_structured.return_value = ContentStructure(**mock_structure)
            mock_get_client.return_value = mock_client

            analyzer = StructureAnalyzer()
            result = analyzer.analyze(SAMPLE_TRANSCRIPT)

            assert result.hook.text == "AI改变世界"
            assert result.setup.text == ""

    def test_analyze_llm_error(self):
        from modules.structure_analyzer import StructureAnalyzer

        with patch("modules.structure_analyzer.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_structured.side_effect = ValueError("Invalid schema")
            mock_get_client.return_value = mock_client

            analyzer = StructureAnalyzer()
            with pytest.raises(ValueError, match="Invalid schema"):
                analyzer.analyze(SAMPLE_TRANSCRIPT)


# ──────────────────────────────────────────────
# TestRewriter
# ──────────────────────────────────────────────

class TestRewriter:
    def _make_mock_variant(self, mode=RewriteMode.LIGHT, style=None):
        return RewriteVariant(
            mode=mode,
            style=style,
            title="改写后的标题",
            script="这是一段改写后的短视频文案，保持了核心信息但采用了不同的表达方式。",
            hook="改写后的开头钩子",
            cta="记得点赞关注哦",
            word_count=0,
            changes_summary="替换了表达方式，保持结构不变",
        )

    def test_rewrite_light_only(self):
        from modules.rewriter import Rewriter

        with patch("modules.rewriter.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_structured.return_value = self._make_mock_variant(RewriteMode.LIGHT)
            mock_get_client.return_value = mock_client

            rewriter = Rewriter()
            result = rewriter.rewrite(SAMPLE_TRANSCRIPT, modes=["light"], styles=[])

            assert isinstance(result, RewriteResult)
            assert result.light is not None
            assert result.light.mode == RewriteMode.LIGHT
            assert result.light.script != ""
            assert result.viral is None

    def test_rewrite_viral_only(self):
        from modules.rewriter import Rewriter

        with patch("modules.rewriter.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_structured.return_value = self._make_mock_variant(RewriteMode.VIRAL)
            mock_get_client.return_value = mock_client

            rewriter = Rewriter()
            result = rewriter.rewrite(SAMPLE_TRANSCRIPT, modes=["viral"], styles=[])

            assert isinstance(result, RewriteResult)
            assert result.viral is not None
            assert result.viral.mode == RewriteMode.VIRAL
            assert result.light is None

    def test_rewrite_with_style(self):
        from modules.rewriter import Rewriter

        with patch("modules.rewriter.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_structured.side_effect = [
                self._make_mock_variant(RewriteMode.LIGHT),
                self._make_mock_variant(RewriteMode.VIRAL),
                self._make_mock_variant(RewriteMode.STYLE, RewriteStyle.STORYTELLING),
            ]
            mock_get_client.return_value = mock_client

            rewriter = Rewriter()
            result = rewriter.rewrite(
                SAMPLE_TRANSCRIPT,
                modes=["light", "viral"],
                styles=["storytelling"],
            )

            assert result.light is not None
            assert result.viral is not None
            assert len(result.style_variants) == 1
            assert result.style_variants[0].style == RewriteStyle.STORYTELLING
            assert result.style_variants[0].mode == RewriteMode.STYLE

    def test_rewrite_multiple_styles(self):
        from modules.rewriter import Rewriter

        with patch("modules.rewriter.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_structured.side_effect = [
                self._make_mock_variant(RewriteMode.STYLE, RewriteStyle.STORYTELLING),
                self._make_mock_variant(RewriteMode.STYLE, RewriteStyle.EMOTIONAL),
                self._make_mock_variant(RewriteMode.STYLE, RewriteStyle.EDUCATIONAL),
            ]
            mock_get_client.return_value = mock_client

            rewriter = Rewriter()
            result = rewriter.rewrite(
                SAMPLE_TRANSCRIPT,
                modes=[],
                styles=["storytelling", "emotional", "educational"],
            )

            assert len(result.style_variants) == 3
            styles = [v.style for v in result.style_variants]
            assert RewriteStyle.STORYTELLING in styles
            assert RewriteStyle.EMOTIONAL in styles
            assert RewriteStyle.EDUCATIONAL in styles

    def test_rewrite_partial_failure(self):
        from modules.rewriter import Rewriter

        with patch("modules.rewriter.get_llm_client") as mock_get_client:
            mock_client = MagicMock()

            def side_effect(*args, **kwargs):
                prompt = args[0] if args else kwargs.get("prompt", "")
                if "light" in str(prompt).lower() or "轻度" in str(prompt):
                    return self._make_mock_variant(RewriteMode.LIGHT)
                raise Exception("Viral rewrite failed")

            mock_client.chat_structured.side_effect = side_effect
            mock_get_client.return_value = mock_client

            rewriter = Rewriter()
            result = rewriter.rewrite(SAMPLE_TRANSCRIPT, modes=["light", "viral"], styles=[])

            assert result.light is not None
            assert result.viral is None

    def test_rewrite_default_modes(self):
        from modules.rewriter import Rewriter

        with patch("modules.rewriter.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_structured.side_effect = [
                self._make_mock_variant(RewriteMode.LIGHT),
                self._make_mock_variant(RewriteMode.VIRAL),
                self._make_mock_variant(RewriteMode.STYLE, RewriteStyle.STORYTELLING),
            ]
            mock_get_client.return_value = mock_client

            rewriter = Rewriter()
            result = rewriter.rewrite(SAMPLE_TRANSCRIPT)

            assert result.light is not None
            assert result.viral is not None
            assert len(result.style_variants) == 1

    def test_rewrite_invalid_style_skipped(self):
        from modules.rewriter import Rewriter

        with patch("modules.rewriter.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_structured.return_value = self._make_mock_variant(RewriteMode.LIGHT)
            mock_get_client.return_value = mock_client

            rewriter = Rewriter()
            result = rewriter.rewrite(
                SAMPLE_TRANSCRIPT,
                modes=["light"],
                styles=["nonexistent_style"],
            )

            assert result.light is not None
            assert len(result.style_variants) == 0
            mock_client.chat_structured.assert_called_once()


# ──────────────────────────────────────────────
# TestASRCorrector
# ──────────────────────────────────────────────

class TestASRCorrector:
    def test_correct_pass1_only(self):
        from modules.asr_corrector import ASRCorrector

        with patch("modules.asr_corrector.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.return_value = "你知道吗？2024年AI的发展速度超出了所有人的想象。首先，大语言模型的能力有了质的飞跃。"
            mock_get_client.return_value = mock_client

            corrector = ASRCorrector()
            result = corrector.correct(SAMPLE_TRANSCRIPT)

            assert isinstance(result, str)
            assert len(result) > 0
            mock_client.chat.assert_called_once()

    def test_correct_two_passes(self):
        from modules.asr_corrector import ASRCorrector

        with patch("modules.asr_corrector.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.side_effect = [
                "你知道吗？2024年AI的发展速度超出了所有人的想象。",
                "你知道吗？2024年AI的发展速度超出了所有人的想象。（精校版）",
            ]
            mock_get_client.return_value = mock_client

            corrector = ASRCorrector()
            result = corrector.correct(
                SAMPLE_TRANSCRIPT,
                platform="bilibili",
                title="AI发展综述",
                author="科技频道",
            )

            assert isinstance(result, str)
            assert "精校版" in result
            assert mock_client.chat.call_count == 2

    def test_correct_short_text_returns_original(self):
        from modules.asr_corrector import ASRCorrector

        with patch("modules.asr_corrector.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            corrector = ASRCorrector()
            result = corrector.correct("太短了")

            assert result == "太短了"
            mock_client.chat.assert_not_called()

    def test_correct_empty_text(self):
        from modules.asr_corrector import ASRCorrector

        with patch("modules.asr_corrector.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            corrector = ASRCorrector()
            result = corrector.correct("")

            assert result == ""
            mock_client.chat.assert_not_called()

    def test_correct_pass1_fallback_to_original(self):
        from modules.asr_corrector import ASRCorrector

        with patch("modules.asr_corrector.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.side_effect = Exception("API timeout")
            mock_get_client.return_value = mock_client

            corrector = ASRCorrector()
            result = corrector.correct(SAMPLE_TRANSCRIPT)

            assert result == SAMPLE_TRANSCRIPT

    def test_correct_pass2_fallback_to_pass1(self):
        from modules.asr_corrector import ASRCorrector

        with patch("modules.asr_corrector.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.side_effect = [
                "第一轮修正后的文本",
                Exception("Pass 2 failed"),
            ]
            mock_get_client.return_value = mock_client

            corrector = ASRCorrector()
            result = corrector.correct(
                SAMPLE_TRANSCRIPT,
                platform="douyin",
                title="测试标题",
            )

            assert result == "第一轮修正后的文本"


# ──────────────────────────────────────────────
# TestLLMClient
# ──────────────────────────────────────────────

class TestLLMClient:
    def _make_mock_openai_response(self, content: str):
        mock_message = MagicMock()
        mock_message.content = content
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        return mock_response

    def test_chat_success(self):
        from utils.llm_client import LLMClient
        from config import LLMConfig

        mock_cfg = LLMConfig(
            api_key="test-key",
            base_url="https://test.com/v1",
            model="test-model",
        )

        with patch("utils.llm_client.OpenAI") as MockOpenAI:
            mock_openai = MagicMock()
            mock_openai.chat.completions.create.return_value = self._make_mock_openai_response("Hello, world!")
            MockOpenAI.return_value = mock_openai

            client = LLMClient(config=mock_cfg)
            result = client.chat(prompt="Say hello", system="Be friendly")

            assert result == "Hello, world!"
            mock_openai.chat.completions.create.assert_called_once()

    def test_chat_json_success(self):
        from utils.llm_client import LLMClient
        from config import LLMConfig

        mock_cfg = LLMConfig(
            api_key="test-key",
            base_url="https://test.com/v1",
            model="test-model",
        )
        json_content = json.dumps({"topic": "AI", "score": 85})

        with patch("utils.llm_client.OpenAI") as MockOpenAI:
            mock_openai = MagicMock()
            mock_openai.chat.completions.create.return_value = self._make_mock_openai_response(json_content)
            MockOpenAI.return_value = mock_openai

            client = LLMClient(config=mock_cfg)
            result = client.chat_json(prompt="Analyze this")

            assert isinstance(result, dict)
            assert result["topic"] == "AI"
            assert result["score"] == 85

    def test_chat_json_invalid_json_raises(self):
        from utils.llm_client import LLMClient
        from config import LLMConfig

        mock_cfg = LLMConfig(
            api_key="test-key",
            base_url="https://test.com/v1",
            model="test-model",
        )

        with patch("utils.llm_client.OpenAI") as MockOpenAI:
            mock_openai = MagicMock()
            mock_openai.chat.completions.create.return_value = self._make_mock_openai_response("not valid json {{{")
            MockOpenAI.return_value = mock_openai

            client = LLMClient(config=mock_cfg)
            with pytest.raises(json.JSONDecodeError):
                client.chat_json(prompt="Analyze this")

    def test_chat_structured_success(self):
        from utils.llm_client import LLMClient
        from config import LLMConfig

        mock_cfg = LLMConfig(
            api_key="test-key",
            base_url="https://test.com/v1",
            model="test-model",
        )
        json_content = json.dumps({
            "one_sentence": "AI发展很快",
            "key_points": ["模型进步", "应用广泛"],
            "chapters": [],
            "target_audience": "开发者",
            "content_type": "科普",
        })

        with patch("utils.llm_client.OpenAI") as MockOpenAI:
            mock_openai = MagicMock()
            mock_openai.chat.completions.create.return_value = self._make_mock_openai_response(json_content)
            MockOpenAI.return_value = mock_openai

            client = LLMClient(config=mock_cfg)
            result = client.chat_structured(
                prompt="Summarize this",
                response_model=ContentSummary,
            )

            assert isinstance(result, ContentSummary)
            assert result.one_sentence == "AI发展很快"
            assert len(result.key_points) == 2

    def test_chat_structured_invalid_schema_retries(self):
        from utils.llm_client import LLMClient
        from config import LLMConfig, get_config
        from pydantic import BaseModel, ValidationError

        class StrictModel(BaseModel):
            required_field: str
            required_number: int

        mock_cfg = LLMConfig(
            api_key="test-key",
            base_url="https://test.com/v1",
            model="test-model",
        )
        invalid_json = json.dumps({"wrong_field": "no match"})

        with patch("utils.llm_client.OpenAI") as MockOpenAI, \
             patch("utils.llm_client.get_config") as mock_get_config:
            mock_get_config.return_value.llm = mock_cfg
            mock_openai = MagicMock()
            mock_openai.chat.completions.create.return_value = self._make_mock_openai_response(invalid_json)
            MockOpenAI.return_value = mock_openai

            client = LLMClient(config=mock_cfg)
            with pytest.raises((Exception, ValidationError)):
                client.chat_structured(
                    prompt="Summarize",
                    response_model=StrictModel,
                    max_retries=1,
                )

    def test_chat_api_error_raises(self):
        from utils.llm_client import LLMClient
        from config import LLMConfig
        from openai import APIStatusError

        mock_cfg = LLMConfig(
            api_key="test-key",
            base_url="https://test.com/v1",
            model="test-model",
        )

        with patch("utils.llm_client.OpenAI") as MockOpenAI:
            mock_openai = MagicMock()
            mock_openai.chat.completions.create.side_effect = APIStatusError(
                message="Server error",
                response=MagicMock(status_code=500),
                body={"error": "Internal Server Error"},
            )
            MockOpenAI.return_value = mock_openai

            client = LLMClient(config=mock_cfg, max_retries=0)
            with pytest.raises(APIStatusError):
                client.chat(prompt="Test")


# ──────────────────────────────────────────────
# TestGoViralAdvisor
# ──────────────────────────────────────────────

class TestGoViralAdvisor:
    """Tests for GoViralAdvisor module."""

    def test_advise_success(self):
        from modules.go_viral_advisor import GoViralAdvisor
        from models import (
            ViralityAnalysis, ViralityScores, ContentStructure, HookType,
            GoViralAdvice, GoViralTip,
        )

        mock_virality = ViralityAnalysis(
            scores=ViralityScores(hook=45, emotion=60, retention=70, cta=30, social_currency=55, overall=52),
            hook_type=HookType.CURIOSITY,
            hook_text="你知道这个吗",
            strengths=["信息密度高", "结构清晰"],
            weaknesses=["开头不够吸引", "缺少CTA"],
            explanation="内容有价值但呈现方式平淡",
            viral_potential="medium",
        )
        mock_structure = ContentStructure(
            narrative_style="知识科普",
            keywords=["AI", "工具", "效率"],
            rhetorical_devices=["比喻", "对比"],
        )

        mock_advice = GoViralAdvice(
            overall_strategy="强化情感共鸣，优化开头钩子",
            top_3_actions=["重写前3秒", "增加故事元素", "强化CTA"],
            tips=[
                GoViralTip(
                    category="hook",
                    priority="high",
                    title="用冲突开头",
                    description="制造认知冲突抓住注意力",
                    example="90%的人都不知道这个AI技巧"
                )
            ],
            title_suggestions=["AI效率神器", "打工人必备工具", "效率翻倍的秘密"],
            hook_alternatives=["你绝对想不到...", "这个改变了一切"],
            platform_tips=["发布时间选晚上8点", "加3-5个热门标签", "评论区置顶互动问题"]
        )

        with patch("modules.go_viral_advisor.get_config") as mock_cfg, \
             patch("modules.go_viral_advisor.get_llm_client") as mock_get_client:
            mock_cfg.return_value.max_transcript_chars = 50000
            mock_client = MagicMock()
            mock_client.chat_structured.return_value = mock_advice
            mock_get_client.return_value = mock_client

            advisor = GoViralAdvisor()
            result = advisor.advise("test transcript content here", mock_virality, mock_structure)

            assert result.overall_strategy == "强化情感共鸣，优化开头钩子"
            assert len(result.top_3_actions) == 3
            assert len(result.tips) == 1
            assert result.tips[0].category == "hook"
            assert len(result.title_suggestions) == 3
            assert len(result.hook_alternatives) == 2
            assert len(result.platform_tips) == 3

    def test_advise_with_low_scores(self):
        from modules.go_viral_advisor import GoViralAdvisor
        from models import (
            ViralityAnalysis, ViralityScores, ContentStructure, HookType,
            GoViralAdvice, GoViralTip,
        )

        mock_virality = ViralityAnalysis(
            scores=ViralityScores(hook=20, emotion=15, retention=40, cta=10, social_currency=25, overall=22),
            hook_type=HookType.QUESTION,
            hook_text="大家好",
            strengths=[],
            weaknesses=["开头平淡", "无情感触发", "无CTA", "节奏拖沓"],
            explanation="内容缺乏传播潜力",
            viral_potential="low",
        )
        mock_structure = ContentStructure(
            narrative_style="平铺直叙",
            keywords=[],
            rhetorical_devices=[],
        )

        mock_advice = GoViralAdvice(
            overall_strategy="全面重构，增加情感元素",
            top_3_actions=["重写钩子", "增加故事", "添加CTA"],
            tips=[
                GoViralTip(
                    category="emotion",
                    priority="high",
                    title="增加情感触发点",
                    description="加入痛点共鸣",
                    example=""
                )
            ],
            title_suggestions=["标题1"],
            hook_alternatives=["钩子1"],
            platform_tips=["建议1"]
        )

        with patch("modules.go_viral_advisor.get_config") as mock_cfg, \
             patch("modules.go_viral_advisor.get_llm_client") as mock_get_client:
            mock_cfg.return_value.max_transcript_chars = 50000
            mock_client = MagicMock()
            mock_client.chat_structured.return_value = mock_advice
            mock_get_client.return_value = mock_client

            advisor = GoViralAdvisor()
            result = advisor.advise("short content", mock_virality, mock_structure)

            assert result.overall_strategy != ""
            assert len(result.tips) >= 1

    def test_advise_llm_error(self):
        from modules.go_viral_advisor import GoViralAdvisor
        from models import ViralityAnalysis, ViralityScores, ContentStructure, HookType

        mock_virality = ViralityAnalysis(
            scores=ViralityScores(hook=50, emotion=50, retention=50, cta=50, social_currency=50, overall=50),
            hook_type=HookType.CURIOSITY,
            strengths=[],
            weaknesses=[],
            viral_potential="medium",
        )
        mock_structure = ContentStructure()

        with patch("modules.go_viral_advisor.get_config") as mock_cfg, \
             patch("modules.go_viral_advisor.get_llm_client") as mock_get_client:
            mock_cfg.return_value.max_transcript_chars = 50000
            mock_client = MagicMock()
            mock_client.chat_structured.side_effect = Exception("LLM API error")
            mock_get_client.return_value = mock_client

            advisor = GoViralAdvisor()
            with pytest.raises(Exception):
                advisor.advise("test content", mock_virality, mock_structure)
