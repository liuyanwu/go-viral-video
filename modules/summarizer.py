"""LLM-powered content summarization module."""

import asyncio
from config import get_config
from models import ContentSummary
from prompts.summary import SUMMARY_SYSTEM_PROMPT, SUMMARY_USER_PROMPT
from utils.llm_client import get_llm_client
from utils.logger import setup_logger

logger = setup_logger("Summarizer")


class Summarizer:
    """Generate structured summaries from transcript text."""

    def summarize(self, transcript_text: str) -> ContentSummary:
        """Generate summary from cleaned transcript."""
        logger.info("Generating summary...")
        client = get_llm_client()
        max_chars = get_config().max_transcript_chars
        prompt = SUMMARY_USER_PROMPT.format(transcript=transcript_text[:max_chars])
        return client.chat_structured(
            prompt=prompt,
            response_model=ContentSummary,
            system=SUMMARY_SYSTEM_PROMPT,
            temperature=0.5,
        )

    async def summarize_async(self, transcript_text: str) -> ContentSummary:
        """Async wrapper for summarize."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.summarize, transcript_text)
