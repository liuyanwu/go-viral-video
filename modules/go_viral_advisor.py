"""Go Viral advice generation module."""

import asyncio
from config import get_config
from models import GoViralAdvice
from prompts.go_viral import GO_VIRAL_SYSTEM_PROMPT, GO_VIRAL_USER_PROMPT
from utils.llm_client import get_llm_client
from utils.logger import setup_logger

logger = setup_logger("GoViralAdvisor")


class GoViralAdvisor:
    """Generate actionable viral optimization advice."""

    def advise(
        self,
        transcript_text: str,
        virality_analysis,
        structure_analysis,
    ) -> GoViralAdvice:
        """Generate go-viral advice based on analysis results."""
        logger.info("Generating Go Viral advice...")
        client = get_llm_client()
        max_chars = get_config().max_transcript_chars
        text = transcript_text[:max_chars]

        # Extract data from analysis objects
        v = virality_analysis
        s = structure_analysis

        prompt = GO_VIRAL_USER_PROMPT.format(
            transcript=text,
            virality_overall=v.scores.overall if v else 0,
            virality_potential=v.viral_potential if v else "unknown",
            hook_type=v.hook_type.value if v and v.hook_type else "unknown",
            hook_score=v.scores.hook if v else 0,
            emotion_score=v.scores.emotion if v else 0,
            retention_score=v.scores.retention if v else 0,
            cta_score=v.scores.cta if v else 0,
            social_score=v.scores.social_currency if v else 0,
            strengths=", ".join(v.strengths[:3]) if v and v.strengths else "无",
            weaknesses=", ".join(v.weaknesses[:3]) if v and v.weaknesses else "无",
            narrative_style=s.narrative_style if s else "未知",
            keywords=", ".join(s.keywords[:5]) if s and s.keywords else "无",
            rhetorical_devices=", ".join(s.rhetorical_devices[:3]) if s and s.rhetorical_devices else "无",
        )

        return client.chat_structured(
            prompt=prompt,
            response_model=GoViralAdvice,
            system=GO_VIRAL_SYSTEM_PROMPT,
            temperature=0.7,
        )

    async def advise_async(self, transcript_text, virality_analysis, structure_analysis):
        """Async wrapper."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.advise, transcript_text, virality_analysis, structure_analysis
        )
