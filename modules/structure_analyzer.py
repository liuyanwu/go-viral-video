"""LLM-powered content structure breakdown module."""

import asyncio
from config import get_config
from models import ContentStructure
from prompts.structure import STRUCTURE_SYSTEM_PROMPT, STRUCTURE_USER_PROMPT
from utils.llm_client import get_llm_client
from utils.logger import setup_logger

logger = setup_logger("StructureAnalyzer")


class StructureAnalyzer:
    """Break down content into narrative structure components."""

    def analyze(self, transcript_text: str) -> ContentStructure:
        """Analyze narrative structure of transcript."""
        logger.info("Analyzing content structure...")
        client = get_llm_client()
        max_chars = get_config().max_transcript_chars
        prompt = STRUCTURE_USER_PROMPT.format(transcript=transcript_text[:max_chars])
        return client.chat_structured(
            prompt=prompt,
            response_model=ContentStructure,
            system=STRUCTURE_SYSTEM_PROMPT,
            temperature=0.5,
        )

    async def analyze_async(self, transcript_text: str) -> ContentStructure:
        """Async wrapper for analyze."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.analyze, transcript_text)
