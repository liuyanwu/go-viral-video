"""LLM-powered virality analysis module with 5D scoring (0-100)."""

import asyncio
from config import get_config
from models import ViralityAnalysis
from prompts.virality import VIRALITY_SYSTEM_PROMPT, VIRALITY_USER_PROMPT
from utils.llm_client import get_llm_client
from utils.logger import setup_logger

logger = setup_logger("ViralityAnalyzer")


class ViralityAnalyzer:
    """Analyze content virality with quantified 5D scoring."""

    def analyze(self, transcript_text: str) -> ViralityAnalysis:
        """Run virality analysis and return scored results."""
        logger.info("Running virality analysis (5D scoring)...")
        client = get_llm_client()
        max_chars = get_config().max_transcript_chars
        prompt = VIRALITY_USER_PROMPT.format(transcript=transcript_text[:max_chars])
        return client.chat_structured(
            prompt=prompt,
            response_model=ViralityAnalysis,
            system=VIRALITY_SYSTEM_PROMPT,
            temperature=0.6,
        )

    async def analyze_async(self, transcript_text: str) -> ViralityAnalysis:
        """Async wrapper for analyze."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.analyze, transcript_text)
