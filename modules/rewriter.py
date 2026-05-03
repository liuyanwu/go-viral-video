"""
LLM-powered content rewriter module.
3 modes: Light, Viral, Style (4 variants).
"""

from typing import List, Optional

from config import get_config
from models import RewriteResult, RewriteVariant, RewriteMode, RewriteStyle
from prompts.rewrite import (
    REWRITE_SYSTEM_PROMPT,
    REWRITE_LIGHT_PROMPT, REWRITE_VIRAL_PROMPT,
    REWRITE_STYLE_PROMPT, STYLE_DESCRIPTIONS,
)
from utils.llm_client import get_llm_client
from utils.logger import setup_logger

logger = setup_logger("Rewriter")


class Rewriter:
    """Generate multiple rewrite variants from transcript."""

    def rewrite(
        self,
        transcript_text: str,
        modes: Optional[List[str]] = None,
        styles: Optional[List[str]] = None,
    ) -> RewriteResult:
        """
        Generate rewrites in specified modes and styles.

        Args:
            transcript_text: Cleaned transcript text.
            modes: Which modes to generate. Default: ["light", "viral"].
            styles: Which style variants. Default: ["storytelling"].
        """
        if modes is None:
            modes = ["light", "viral"]
        if styles is None:
            styles = ["storytelling", "abstract"]

        client = get_llm_client()
        result = RewriteResult()
        max_chars = get_config().max_transcript_chars
        text = transcript_text[:max_chars]

        # Light rewrite
        if "light" in modes:
            logger.info("Generating light rewrite...")
            try:
                variant = client.chat_structured(
                    prompt=REWRITE_LIGHT_PROMPT.format(transcript=f"<TRANSCRIPT_START>\n{text}\n<TRANSCRIPT_END>"),
                    response_model=RewriteVariant,
                    system=REWRITE_SYSTEM_PROMPT,
                    temperature=0.7,
                )
                variant.mode = RewriteMode.LIGHT
                variant.word_count = len(variant.script)
                result.light = variant
            except Exception as e:
                logger.error(f"Light rewrite failed: {e}")

        # Viral rewrite
        if "viral" in modes:
            logger.info("Generating viral rewrite...")
            try:
                variant = client.chat_structured(
                    prompt=REWRITE_VIRAL_PROMPT.format(transcript=text),
                    response_model=RewriteVariant,
                    system=REWRITE_SYSTEM_PROMPT,
                    temperature=0.8,
                )
                variant.mode = RewriteMode.VIRAL
                variant.word_count = len(variant.script)
                result.viral = variant
            except Exception as e:
                logger.error(f"Viral rewrite failed: {e}")

        # Style variants
        for style_key in styles:
            if style_key not in STYLE_DESCRIPTIONS:
                continue
            style_info = STYLE_DESCRIPTIONS[style_key]
            logger.info(f"Generating style rewrite: {style_info['name']}...")
            try:
                prompt = REWRITE_STYLE_PROMPT.format(
                    transcript=text,
                    style_name=style_info["name"],
                    style_description=style_info["description"],
                )
                variant = client.chat_structured(
                    prompt=prompt,
                    response_model=RewriteVariant,
                    system=REWRITE_SYSTEM_PROMPT,
                    temperature=0.8,
                )
                variant.mode = RewriteMode.STYLE
                variant.style = RewriteStyle(style_key)
                variant.word_count = len(variant.script)
                result.style_variants.append(variant)
            except Exception as e:
                logger.error(f"Style rewrite ({style_key}) failed: {e}")

        return result
