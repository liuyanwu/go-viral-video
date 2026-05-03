"""
Main pipeline orchestrator for Video Viral Analyzer & Rewriter.
Executes all pipeline stages in sequence: Download → Subtitle → ASR → Clean → Analyze → Rewrite.
"""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from config import get_config, ServiceContainer
from metrics import metrics
from models import (
    AnalysisResult, VideoInfo, TranscriptResult,
    SubtitleSource, Platform,
)
from modules.downloader import VideoDownloader
from modules.subtitle_extractor import SubtitleExtractor
from modules.asr import ASREngine
from modules.text_cleaner import TextCleaner
from modules.asr_corrector import ASRCorrector
from modules.summarizer import Summarizer
from modules.virality_analyzer import ViralityAnalyzer
from modules.structure_analyzer import StructureAnalyzer
from modules.rewriter import Rewriter
from modules.go_viral_advisor import GoViralAdvisor
from utils.logger import setup_logger

logger = setup_logger("Pipeline")

SEPARATOR_WIDTH = 60


class Pipeline:
    """
    Orchestrates the full video analysis pipeline.

    Stages:
    1. Download video (or validate local file)
    2. Extract subtitles (embedded / platform / OCR)
    3. ASR fallback (if no subtitles found)
    4. Clean text
    5. Summarize (LLM)
    6. Virality analysis (LLM)
    7. Structure breakdown (LLM)
    8. Rewrite generation (LLM)
    9. Output structured JSON + Markdown
    """

    def __init__(self, services: Optional[ServiceContainer] = None):
        if services is None:
            services = ServiceContainer(get_config())
        self.services = services
        self.config = services.config
        self.downloader = VideoDownloader()
        self.subtitle_extractor = SubtitleExtractor()
        self.asr_engine = ASREngine()
        self.text_cleaner = TextCleaner()
        self.asr_corrector = ASRCorrector()
        self.summarizer = Summarizer()
        self.virality_analyzer = ViralityAnalyzer()
        self.structure_analyzer = StructureAnalyzer()
        self.rewriter = Rewriter()
        self.go_viral_advisor = GoViralAdvisor()

    def run(
        self,
        url_or_path: str,
        skip_download: bool = False,
        skip_analysis: bool = False,
        rewrite_modes: Optional[List[str]] = None,
        rewrite_styles: Optional[List[str]] = None,
    ) -> AnalysisResult:
        """
        Execute the full pipeline.
        """
        # Extract URL if the input contains other text (e.g. copied from app)
        import re
        from pathlib import Path
        url_match = re.search(r'(https?://[^\s]+)', url_or_path)
        if url_match:
            try:
                if not Path(url_or_path).exists():
                    url_or_path = url_match.group(1)
            except OSError:
                url_or_path = url_match.group(1)

        start_time = time.time()
        errors = []
        warnings = []

        logger.info("=" * SEPARATOR_WIDTH)
        logger.info("🚀 [bold]Video Viral Analyzer & Rewriter[/bold]")
        logger.info("=" * SEPARATOR_WIDTH)
        logger.info(f"Input: {url_or_path}")

        cached = self.services.cache.get(url_or_path)
        if cached is not None:
            logger.info("✅ Cache hit, returning cached result")
            return cached

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
        ) as progress:
            # ──── Stage 1: Download ────
            logger.info("\n📥 [bold]Stage 1: Download[/bold]")
            _stage_start = time.time()
            download_task = progress.add_task("[cyan]Downloading...", total=None)
            try:
                video_info = self.downloader.download(url_or_path)
                metrics.record_stage("download", time.time() - _stage_start)
                progress.update(download_task, description="[green]Download complete", completed=True)
                logger.info(f"✅ Downloaded: {video_info.local_path}")
                video_info.downloaded_at = datetime.now()
            except Exception as e:
                metrics.record_stage("download", time.time() - _stage_start)
                metrics.record_error("DownloadError")
                progress.update(download_task, description="[red]Download failed")
                logger.error(f"❌ Download failed: {e}")
                errors.append(f"Download failed: {e}")
                # Create minimal result with error
                result = AnalysisResult(
                    video=VideoInfo(url=url_or_path, platform=Platform.UNKNOWN),
                    transcript=TranscriptResult(source=SubtitleSource.ASR),
                    errors=errors,
                    processing_time_seconds=time.time() - start_time,
                )
                try:
                    self.services.cache.put(url_or_path, result)
                except Exception:
                    pass
                return result

            # ──── Stage 2: Subtitle Extraction ────
            logger.info("\n📝 [bold]Stage 2: Subtitle Extraction[/bold]")
            _stage_start = time.time()

            # Check if this is an image/text note (Xiaohongshu / Twitter)
            is_image_text_note = video_info.download_method in ("xhs_image_text_note", "twitter_image_text_note", "instagram_image_text_note")

            if is_image_text_note:
                # For image/text notes, read the extracted text directly
                logger.info("[Image/Text Note] Reading extracted text content...")
                subtitle_task = progress.add_task("[cyan]Reading text content...", total=None)
                try:
                    text_path = Path(video_info.local_path)
                    if text_path.exists():
                        raw_text = text_path.read_text(encoding="utf-8")
                        from models import SubtitleSegment
                        transcript = TranscriptResult(
                            source=SubtitleSource.MANUAL,
                            language="zh",
                            raw_text=raw_text,
                            cleaned_text=raw_text,
                            corrected_text="",
                        )
                        logger.info(f"✅ Loaded image/text note: {len(raw_text)} chars")
                    else:
                        raise FileNotFoundError(f"Text file not found: {video_info.local_path}")
                except Exception as e:
                    logger.error(f"❌ Failed to load image/text note: {e}")
                    errors.append(f"Image/text note load failed: {e}")
                    transcript = TranscriptResult(source=SubtitleSource.MANUAL)
                progress.update(subtitle_task, description="[green]Text content loaded", completed=True)
                metrics.record_stage("subtitle", time.time() - _stage_start)
            else:
                subtitle_task = progress.add_task("[cyan]Extracting subtitles...", total=None)
                try:
                    transcript = self.subtitle_extractor.extract(
                        video_path=video_info.local_path,
                        url=url_or_path,
                    )
                    metrics.record_stage("subtitle", time.time() - _stage_start)
                    progress.update(subtitle_task, description="[green]Subtitle extraction complete", completed=True)
                except Exception as e:
                    metrics.record_stage("subtitle", time.time() - _stage_start)
                    metrics.record_error("SubtitleError")
                    progress.update(subtitle_task, description="[red]Subtitle extraction failed")
                    raise

                # ──── Stage 3: ASR Fallback ────
                if not transcript.raw_text and transcript.source == SubtitleSource.ASR:
                    logger.info("\n🎤 [bold]Stage 3: ASR Transcription[/bold]")
                    _stage_start = time.time()
                    try:
                        platform_key = video_info.platform.value if video_info.platform else "general"
                        
                        # Check if video is long and needs chunking
                        needs_chunking = video_info.duration_seconds > 300  # 5 minutes

                        if needs_chunking:
                            asr_task = progress.add_task("[cyan]Transcribing (chunked)...", total=None)
                            logger.info(f"Long video detected ({video_info.duration_seconds:.0f}s), enabling chunked ASR...")
                            from modules.chunk_processor import ChunkProcessor
                            processor = ChunkProcessor(chunk_duration_seconds=300, overlap_seconds=5)
                            
                            # Extract audio first
                            audio_path = self.asr_engine._extract_audio(video_info.local_path)
                            
                            # Split audio into chunks
                            chunk_dir = self.config.output_dir / "chunks"
                            audio_chunks = processor.split_audio(audio_path, chunk_dir)
                            logger.info(f"Split audio into {len(audio_chunks)} chunks")
                            
                            # Transcribe each chunk
                            chunk_texts = []
                            for i, chunk_path in enumerate(audio_chunks):
                                logger.info(f"Transcribing chunk {i+1}/{len(audio_chunks)}...")
                                progress.update(asr_task, description=f"[cyan]Transcribing chunk {i+1}/{len(audio_chunks)}...")
                                chunk_result = self.asr_engine.transcribe(chunk_path, platform=platform_key)
                                if chunk_result.raw_text:
                                    chunk_texts.append(chunk_result.raw_text)
                            
                            # Merge chunk transcripts
                            merged_text = processor.merge_text(chunk_texts, overlap_chars=50)
                            transcript.raw_text = merged_text
                            transcript.cleaned_text = merged_text
                            
                            # Cleanup chunks
                            for chunk_path in audio_chunks:
                                try:
                                    Path(chunk_path).unlink(missing_ok=True)
                                except Exception:
                                    pass
                            
                            # Cleanup extracted audio
                            if audio_path:
                                try:
                                    Path(audio_path).unlink(missing_ok=True)
                                except Exception:
                                    pass
                        else:
                            # Normal ASR for short videos
                            asr_task = progress.add_task("[cyan]Transcribing audio...", total=None)
                            transcript = self.asr_engine.transcribe(
                                video_info.local_path,
                                platform=platform_key,
                                title=video_info.title,
                            )
                        
                        metrics.record_stage("asr", time.time() - _stage_start)
                        progress.update(asr_task, description="[green]ASR complete", completed=True)
                        logger.info(f"✅ ASR complete: {len(transcript.raw_text)} chars")
                    except Exception as e:
                        metrics.record_stage("asr", time.time() - _stage_start)
                        metrics.record_error("ASRError")
                        progress.update(asr_task, description="[red]ASR failed")
                        logger.error(f"❌ ASR failed: {e}")
                        errors.append(f"ASR failed: {e}")
                        warnings.append("No transcript available, analysis will be limited")
                else:
                    logger.info("⏭️ ASR skipped (subtitles found)")

            # ──── Stage 4: Text Cleaning ────
            logger.info("\n🧹 [bold]Stage 4: Text Cleaning[/bold]")
            _stage_start = time.time()
            clean_task = progress.add_task("[cyan]Cleaning text...", total=None)
            if transcript.raw_text or transcript.raw_segments:
                transcript = self.text_cleaner.clean(transcript)
                logger.info(f"✅ Cleaned: {len(transcript.cleaned_text)} chars")
                progress.update(clean_task, description="[green]Text cleaning complete", completed=True)
            metrics.record_stage("clean", time.time() - _stage_start)

            # ──── Stage 4.5: ASR Correction (LLM-based, 2-pass) ────
            if self.config.enable_asr_correction and transcript.source == SubtitleSource.ASR:
                logger.info("\n🔧 [bold]Stage 4.5: ASR Correction (2-pass)[/bold]")
                _stage_start = time.time()
                correction_task = progress.add_task("[cyan]Correcting ASR errors...", total=None)
                try:
                    original = transcript.cleaned_text
                    platform_key = video_info.platform.value if video_info.platform else "unknown"
                    transcript.corrected_text = self.asr_corrector.correct(
                        transcript.cleaned_text,
                        platform=platform_key,
                        title=video_info.title,
                        author=video_info.author,
                    )
                    metrics.record_stage("asr_correction", time.time() - _stage_start)
                    if transcript.corrected_text != original:
                        logger.info(f"✅ ASR corrected: {len(original)} → {len(transcript.corrected_text)} chars")
                        progress.update(correction_task, description="[green]ASR corrected", completed=True)
                    else:
                        logger.info("✅ ASR text unchanged (already correct)")
                        progress.update(correction_task, description="[green]ASR text unchanged", completed=True)
                except Exception as e:
                    metrics.record_stage("asr_correction", time.time() - _stage_start)
                    metrics.record_error("ASRCorrectionError")
                    progress.update(correction_task, description="[red]ASR correction failed")
                    logger.warning(f"ASR correction skipped: {e}")
                    transcript.corrected_text = transcript.cleaned_text

            # Early exit if no analysis needed
            if skip_analysis or not transcript.cleaned_text:
                result = AnalysisResult(
                    video=video_info,
                    transcript=transcript,
                    errors=errors,
                    warnings=warnings,
                    processing_time_seconds=time.time() - start_time,
                )
                try:
                    self.services.cache.put(url_or_path, result)
                except Exception:
                    pass
                return result

            # ──── Stage 5-7: Concurrent LLM Analysis ────
            summary = None
            virality = None
            structure = None
            go_viral = None
            
            analysis_text = transcript.corrected_text or transcript.cleaned_text
            
            async def _run_analysis_stages():
                """Run summary, virality, and structure analysis concurrently."""
                async def _summary_task():
                    nonlocal summary
                    try:
                        logger.info("\n📋 [bold]Stage 5: Summary[/bold]")
                        summary_task = progress.add_task("[cyan]Generating summary...", total=None)
                        result = self.summarizer.summarize(analysis_text)
                        progress.update(summary_task, description="[green]Summary complete", completed=True)
                        logger.info(f"✅ Summary: {result.one_sentence[:50]}...")
                        return result
                    except Exception as e:
                        progress.update(summary_task, description="[red]Summary failed")
                        logger.error(f"❌ Summary failed: {e}")
                        errors.append(f"Summary failed: {e}")
                        return None

                async def _virality_task():
                    nonlocal virality
                    try:
                        logger.info("\n🔥 [bold]Stage 6: Virality Analysis[/bold]")
                        virality_task = progress.add_task("[cyan]Analyzing virality...", total=None)
                        result = self.virality_analyzer.analyze(analysis_text)
                        progress.update(virality_task, description="[green]Virality analysis complete", completed=True)
                        logger.info(
                            f"✅ Virality: overall={result.scores.overall}/100 "
                            f"({result.viral_potential})"
                        )
                        return result
                    except Exception as e:
                        progress.update(virality_task, description="[red]Virality analysis failed")
                        logger.error(f"❌ Virality analysis failed: {e}")
                        errors.append(f"Virality analysis failed: {e}")
                        return None

                async def _structure_task():
                    nonlocal structure
                    try:
                        logger.info("\n🏗️ [bold]Stage 7: Structure Breakdown[/bold]")
                        structure_task = progress.add_task("[cyan]Analyzing structure...", total=None)
                        result = self.structure_analyzer.analyze(analysis_text)
                        progress.update(structure_task, description="[green]Structure analysis complete", completed=True)
                        logger.info("✅ Structure breakdown complete")
                        return result
                    except Exception as e:
                        progress.update(structure_task, description="[red]Structure analysis failed")
                        logger.error(f"❌ Structure analysis failed: {e}")
                        errors.append(f"Structure analysis failed: {e}")
                        return None

                async def _go_viral_task():
                    nonlocal go_viral
                    try:
                        logger.info("\n🚀 [bold]Stage 8: Go Viral Advice[/bold]")
                        go_viral_task = progress.add_task("[cyan]Generating viral advice...", total=None)
                        if virality and structure:
                            result = self.go_viral_advisor.advise(analysis_text, virality, structure)
                            progress.update(go_viral_task, description="[green]Go Viral advice complete", completed=True)
                            logger.info(f"✅ Go Viral: {len(result.tips)} tips generated")
                            return result
                        else:
                            progress.update(go_viral_task, description="[yellow]Skipped (missing analysis)")
                            return None
                    except Exception as e:
                        progress.update(go_viral_task, description="[red]Go Viral advice failed")
                        logger.error(f"❌ Go Viral advice failed: {e}")
                        errors.append(f"Go Viral advice failed: {e}")
                        return None

                results = await asyncio.gather(
                    _summary_task(),
                    _virality_task(),
                    _structure_task(),
                    _go_viral_task(),
                    return_exceptions=False
                )
                return results

            try:
                logger.info("\n🧠 [bold]Stages 5-7: Concurrent LLM Analysis[/bold]")
                _stage_start = time.time()
                asyncio.run(_run_analysis_stages())
                metrics.record_stage("concurrent_analysis", time.time() - _stage_start)
            except Exception as e:
                logger.warning(f"Concurrent analysis failed, falling back to sequential: {e}")
                errors.clear()
                
                # ──── Stage 5: Summary (Sequential Fallback) ────
                logger.info("\n📋 [bold]Stage 5: Summary[/bold]")
                _stage_start = time.time()
                summary_task = progress.add_task("[cyan]Generating summary...", total=None)
                try:
                    summary = self.summarizer.summarize(analysis_text)
                    metrics.record_stage("summary", time.time() - _stage_start)
                    progress.update(summary_task, description="[green]Summary complete", completed=True)
                    logger.info(f"✅ Summary: {summary.one_sentence[:50]}...")
                except Exception as e:
                    metrics.record_stage("summary", time.time() - _stage_start)
                    metrics.record_error("SummaryError")
                    progress.update(summary_task, description="[red]Summary failed")
                    logger.error(f"❌ Summary failed: {e}")
                    errors.append(f"Summary failed: {e}")

                # ──── Stage 6: Virality Analysis (Sequential Fallback) ────
                logger.info("\n🔥 [bold]Stage 6: Virality Analysis[/bold]")
                _stage_start = time.time()
                virality_task = progress.add_task("[cyan]Analyzing virality...", total=None)
                try:
                    virality = self.virality_analyzer.analyze(analysis_text)
                    metrics.record_stage("virality", time.time() - _stage_start)
                    progress.update(virality_task, description="[green]Virality analysis complete", completed=True)
                    logger.info(
                        f"✅ Virality: overall={virality.scores.overall}/100 "
                        f"({virality.viral_potential})"
                    )
                except Exception as e:
                    metrics.record_stage("virality", time.time() - _stage_start)
                    metrics.record_error("ViralityError")
                    progress.update(virality_task, description="[red]Virality analysis failed")
                    logger.error(f"❌ Virality analysis failed: {e}")
                    errors.append(f"Virality analysis failed: {e}")

                # ──── Stage 7: Structure Breakdown (Sequential Fallback) ────
                logger.info("\n🏗️ [bold]Stage 7: Structure Breakdown[/bold]")
                _stage_start = time.time()
                structure_task = progress.add_task("[cyan]Analyzing structure...", total=None)
                try:
                    structure = self.structure_analyzer.analyze(analysis_text)
                    metrics.record_stage("structure", time.time() - _stage_start)
                    progress.update(structure_task, description="[green]Structure analysis complete", completed=True)
                    logger.info("✅ Structure breakdown complete")
                except Exception as e:
                    metrics.record_stage("structure", time.time() - _stage_start)
                    metrics.record_error("StructureError")
                    progress.update(structure_task, description="[red]Structure analysis failed")
                    logger.error(f"❌ Structure analysis failed: {e}")
                    errors.append(f"Structure analysis failed: {e}")

                # ──── Stage 8: Go Viral Advice (Sequential Fallback) ────
                logger.info("\n🚀 [bold]Stage 8: Go Viral Advice[/bold]")
                _stage_start = time.time()
                go_viral_task = progress.add_task("[cyan]Generating viral advice...", total=None)
                try:
                    if virality and structure:
                        go_viral = self.go_viral_advisor.advise(analysis_text, virality, structure)
                        metrics.record_stage("go_viral", time.time() - _stage_start)
                        progress.update(go_viral_task, description=f"[green]Go Viral: {len(go_viral.tips)} tips", completed=True)
                        logger.info(f"✅ Go Viral advice: {len(go_viral.tips)} tips generated")
                    else:
                        progress.update(go_viral_task, description="[yellow]Skipped (missing analysis)")
                        logger.info("⏭️ Go Viral advice skipped (missing virality/structure analysis)")
                except Exception as e:
                    metrics.record_stage("go_viral", time.time() - _stage_start)
                    metrics.record_error("GoViralError")
                    progress.update(go_viral_task, description="[red]Go Viral advice failed")
                    logger.error(f"❌ Go Viral advice failed: {e}")
                    errors.append(f"Go Viral advice failed: {e}")

            # ──── Stage 8: Rewrite Generation ────
            rewrites = None
            logger.info("\n✍️ [bold]Stage 8: Rewrite Generation[/bold]")
            _stage_start = time.time()
            rewrite_task = progress.add_task("[cyan]Generating rewrites...", total=None)
            try:
                analysis_text = transcript.corrected_text or transcript.cleaned_text
                rewrites = self.rewriter.rewrite(
                    analysis_text,
                    modes=rewrite_modes,
                    styles=rewrite_styles,
                )
                metrics.record_stage("rewrite", time.time() - _stage_start)
                count = sum([
                    1 if rewrites.light else 0,
                    1 if rewrites.viral else 0,
                    len(rewrites.style_variants),
                ])
                progress.update(rewrite_task, description=f"[green]Generated {count} variants", completed=True)
                logger.info(f"✅ Generated {count} rewrite variants")
            except Exception as e:
                metrics.record_stage("rewrite", time.time() - _stage_start)
                metrics.record_error("RewriteError")
                progress.update(rewrite_task, description="[red]Rewrite failed")
                logger.error(f"❌ Rewrite failed: {e}")
                errors.append(f"Rewrite failed: {e}")

        # ──── Final Output ────
        processing_time = time.time() - start_time

        result = AnalysisResult(
            video=video_info,
            transcript=transcript,
            summary=summary,
            virality=virality,
            structure=structure,
            go_viral=go_viral,
            rewrites=rewrites,
            errors=errors,
            warnings=warnings,
            processing_time_seconds=processing_time,
        )

        # Cache the result for future lookups
        try:
            self.services.cache.put(url_or_path, result)
        except Exception:
            pass  # Cache failure should not break pipeline

        metrics.record_run(success=len(errors) == 0, duration=processing_time)

        logger.info("\n" + "=" * SEPARATOR_WIDTH)
        logger.info(f"🏁 Pipeline complete in {processing_time:.1f}s")
        if errors:
            logger.warning(f"⚠️ {len(errors)} error(s) occurred")
        logger.info(f"Metrics: {metrics.get_summary()}")
        logger.info("=" * SEPARATOR_WIDTH)

        return result
