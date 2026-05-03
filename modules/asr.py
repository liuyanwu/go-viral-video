"""
ASR (Automatic Speech Recognition) module.
Supports Whisper (default) with FunASR as optional alternative.
Optimized for Chinese tech/AI content with domain vocabulary injection.
"""

import subprocess
import shutil
import json
import tempfile
import uuid
from pathlib import Path
from typing import Optional, Any

from models import TranscriptResult, SubtitleSegment, SubtitleSource
from config import get_config
from exceptions import ASRError
from utils.logger import setup_logger

logger = setup_logger("ASR")

try:
    import whisper
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False

try:
    from funasr import AutoModel
    HAS_FUNASR = True
except ImportError:
    HAS_FUNASR = False

# Domain-specific vocabulary hints for Whisper initial_prompt
# These help Whisper recognize tech/AI terms correctly
DOMAIN_VOCABULARY = {
    "general": "通义，火山引擎，阿里云，大模型，AI，人工智能，部署，本地部署，云端，开源，参数，提示词，生态",
    "tech": "Workbody，Arc，Klow，API，SDK，GPU，CUDA，算力，积分，套餐，免费，订阅，服务器，容器，Docker",
    "ai_tools": "通义千问，Qwen，Claude，GPT，Llama，Stable Diffusion，Midjourney，Runway，Sora，Kling，可灵",
}

# Common ASR error patterns for post-processing
COMMON_ASR_ERRORS = {
    "同盡": "通义",
    "阳响": "影响",
    "不属": "部署",
    "注射": "注册",
    "气分": "积分",
    "使减减": "使用",
    "机分": "积分",
    "侠牙": "按需",
    "赐楼": "主流",
    "国险": "国产",
    "云丹": "云端",
    "手约": "签约",
    "初音": "初心",
    "白漂": "白嫖",
    "小龙虾": "大模型",
    "领寸本": "零基础",
    "工处": "工具",
    "地规美确": "分形美学",
    "续适": "叙事",
    "生涂": "生长",
    "大排": "大牌",
    "富裕": "赋予",
    "现性": "线性",
    "化矿": "宏观",
    "同关": "宏观",
    "骗套": "嵌套",
    "看锁": "探索",
    "生起": "旅行",
    "路部": "布局",
    "运进": "运镜",
    "续视": "叙事",
    "机幕": "折纸",
    "重組": "重组",
    "器官": "奇观",
    "本路": "迷路",
    "神媒": "审美",
    "顶合": "顶层",
    "失息": "工程师",
    "架构时": "架构师",
    "边盘": "构建",
    "鼎层": "底层",
    "指能": "只能",
    "安心内台": "某些",
    "Valentine": "Valentino",
    "Consure": "Contextual",
    "flowability": "Flowability",
    "ASP": "ASMR",
}


class ASREngine:
    """
    ASR engine wrapper supporting Whisper and FunASR.
    Extracts audio from video, then transcribes to text with timestamps.
    Optimized for Chinese content with domain vocabulary injection.
    """

    _funasr_model: Optional[Any] = None

    def __init__(self):
        self.config = get_config().asr
        self._loaded_model = None
        self._loaded_model_key = None

    def transcribe(
        self,
        video_path: str,
        platform: str = "general",
        title: str = "",
    ) -> TranscriptResult:
        """
        Transcribe a video file to text.

        Args:
            video_path: Path to the video file.
            platform: Platform type for domain vocabulary (general/tech/ai_tools).
            title: Video title for context-aware transcription.

        Returns:
            TranscriptResult with segments and text.
        """
        audio_path = self._extract_audio(video_path)
        if not audio_path:
            raise ASRError("Failed to extract audio from video")

        try:
            if self.config.engine == "funasr":
                return self._transcribe_funasr(audio_path)
            else:
                return self._transcribe_whisper(audio_path, platform, title)
        finally:
            self._cleanup_audio(audio_path)

    def _cleanup_audio(self, audio_path: str):
        """Remove temporary audio and SRT files after transcription."""
        try:
            p = Path(audio_path)
            if p.exists():
                p.unlink()
                logger.debug(f"Cleaned up temporary audio: {audio_path}")
            # Also clean up SRT file
            srt_path = p.with_suffix(".srt")
            if srt_path.exists():
                srt_path.unlink()
                logger.debug(f"Cleaned up temporary SRT: {srt_path}")
        except Exception as e:
            logger.debug(f"Failed to cleanup audio: {e}")

    @staticmethod
    def _cleanup_temp_dir():
        """Clean up orphaned files from previous runs in the temp directory."""
        temp_dir = Path(tempfile.gettempdir()) / "go-viral-video"
        if not temp_dir.exists():
            return
        try:
            cleaned = 0
            for f in temp_dir.glob("*.wav"):
                f.unlink()
                cleaned += 1
            for f in temp_dir.glob("*.srt"):
                f.unlink()
                cleaned += 1
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} orphaned temp files")
        except Exception as e:
            logger.debug(f"Failed to cleanup temp dir: {e}")

    def _get_whisper_model(self, model_name: str):
        """Load or return cached Whisper model."""
        cache_key = model_name
        if self._loaded_model is not None and self._loaded_model_key == cache_key:
            return self._loaded_model

        if not HAS_WHISPER:
            raise ASRError(
                "openai-whisper is not installed. Run: pip install openai-whisper"
            )

        logger.info(f"Loading Whisper model: {model_name}")
        self._loaded_model = whisper.load_model(model_name)
        self._loaded_model_key = cache_key
        return self._loaded_model

    def _extract_audio(self, video_path: str) -> Optional[str]:
        """Extract audio from video to 16kHz mono WAV with noise reduction."""
        if not shutil.which("ffmpeg"):
            raise ASRError("FFmpeg is required for audio extraction")

        temp_dir = Path(tempfile.gettempdir()) / "go-viral-video"
        temp_dir.mkdir(exist_ok=True)
        audio_path = str(temp_dir / f"{uuid.uuid4().hex}.wav")

        # Enhanced audio extraction with noise reduction and gain normalization
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-af", "highpass=f=80,lowpass=f=8000,dynaudnorm=g=5",  # Noise reduction + normalization
            audio_path,
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0 and Path(audio_path).exists():
                logger.info(f"Audio extracted: {audio_path}")
                return audio_path
            else:
                logger.error(f"FFmpeg error: {result.stderr[:300]}")
        except subprocess.TimeoutExpired:
            logger.error("Audio extraction timed out")

        return None

    def _build_initial_prompt(self, platform: str, title: str) -> str:
        """Build domain-specific initial prompt for Whisper."""
        parts = [DOMAIN_VOCABULARY.get("general", "")]
        parts.append(DOMAIN_VOCABULARY.get(platform, ""))
        parts.append(DOMAIN_VOCABULARY.get("tech", ""))
        parts.append(DOMAIN_VOCABULARY.get("ai_tools", ""))

        # Add title keywords for context
        if title:
            parts.append(title)

        return "，".join(filter(None, parts))

    def _transcribe_whisper(
        self,
        audio_path: str,
        platform: str = "general",
        title: str = "",
    ) -> TranscriptResult:
        """Transcribe using OpenAI Whisper with domain optimization."""
        model_name = (
            self.config.whisper_model_fast
            if self.config.mode == "fast"
            else self.config.whisper_model_accurate
        )

        model = self._get_whisper_model(model_name)

        # Build domain-specific initial prompt
        initial_prompt = self._build_initial_prompt(platform, title)
        logger.info(f"Using domain vocabulary: {initial_prompt[:100]}...")

        logger.info("Transcribing...")
        result = model.transcribe(
            audio_path,
            verbose=False,
            word_timestamps=False,
            language="zh",  # Force Chinese for better accuracy
            initial_prompt=initial_prompt,
            condition_on_previous_text=True,
            no_speech_threshold=0.6,
            temperature=(0.0, 0.2, 0.4, 0.6, 0.8),  # Multi-temperature fallback
        )

        # Convert to our format
        segments = []
        for i, seg in enumerate(result.get("segments", [])):
            segments.append(SubtitleSegment(
                index=i + 1,
                start_time=self._seconds_to_srt_time(seg["start"]),
                end_time=self._seconds_to_srt_time(seg["end"]),
                text=seg["text"].strip(),
            ))

        raw_text = " ".join(s.text for s in segments)
        language = result.get("language", "zh")

        # Apply rule-based post-processing
        raw_text = self._apply_rule_based_correction(raw_text)

        # Save SRT
        srt_path = str(Path(audio_path).with_suffix(".srt"))
        self._save_srt(segments, srt_path)

        logger.info(f"Transcription complete: {len(segments)} segments, lang={language}")

        return TranscriptResult(
            source=SubtitleSource.ASR,
            language=language,
            raw_segments=segments,
            raw_text=raw_text,
            srt_path=srt_path,
        )

    def _apply_rule_based_correction(self, text: str) -> str:
        """Apply rule-based corrections for common ASR errors."""
        corrected = text
        for wrong, right in COMMON_ASR_ERRORS.items():
            corrected = corrected.replace(wrong, right)
        return corrected

    def _transcribe_funasr(self, audio_path: str) -> TranscriptResult:
        """Transcribe using FunASR (Chinese-optimized)."""
        if not HAS_FUNASR:
            raise ASRError(
                "funasr is not installed. Run: pip install funasr modelscope"
            )

        if ASREngine._funasr_model is None:
            logger.info("Loading FunASR model (paraformer-zh)...")
            ASREngine._funasr_model = AutoModel(
                model="paraformer-zh",
                vad_model="fsmn-vad",
                punc_model="ct-punc",
            )
            logger.info("FunASR model loaded")
        model = ASREngine._funasr_model

        logger.info("Transcribing with FunASR...")
        result = model.generate(input=audio_path)

        segments = []
        if result and len(result) > 0:
            res = result[0]
            text = res.get("text", "")
            sentence_info = res.get("sentence_info", [])
            if sentence_info:
                for i, sent in enumerate(sentence_info):
                    segments.append(SubtitleSegment(
                        index=i + 1,
                        start_time=self._ms_to_srt_time(sent.get("start", 0)),
                        end_time=self._ms_to_srt_time(sent.get("end", 0)),
                        text=sent.get("text", ""),
                    ))
            else:
                segments.append(SubtitleSegment(
                    index=1,
                    start_time="00:00:00,000",
                    end_time="99:59:59,999",
                    text=text,
                ))

        raw_text = " ".join(s.text for s in segments)
        raw_text = self._apply_rule_based_correction(raw_text)

        srt_path = str(Path(audio_path).with_suffix(".srt"))
        self._save_srt(segments, srt_path)

        return TranscriptResult(
            source=SubtitleSource.ASR,
            language="zh",
            raw_segments=segments,
            raw_text=raw_text,
            srt_path=srt_path,
        )

    # ──────── Helpers ────────

    @staticmethod
    def _seconds_to_srt_time(seconds: float) -> str:
        """Convert seconds to SRT timestamp format."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    @staticmethod
    def _ms_to_srt_time(ms: int) -> str:
        """Convert milliseconds to SRT timestamp format."""
        seconds = ms / 1000
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        remainder = int(ms % 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{remainder:03d}"

    @staticmethod
    def _save_srt(segments: list[SubtitleSegment], path: str):
        """Save subtitle segments as SRT file."""
        lines = []
        for seg in segments:
            lines.append(str(seg.index))
            lines.append(f"{seg.start_time} --> {seg.end_time}")
            lines.append(seg.text)
            lines.append("")
        Path(path).write_text("\n".join(lines), encoding="utf-8")


# Clean up orphaned temp files on module import
ASREngine._cleanup_temp_dir()
