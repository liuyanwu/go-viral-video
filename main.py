"""
Video Viral Analyzer & Rewriter — CLI Entry Point.

Usage:
    python main.py <URL_or_file>
    python main.py <URL> --output-dir ./output --asr-mode accurate
    python main.py <URL> --skip-analysis   (download + transcript only)
    python main.py --help
"""

import sys
import io

# Fix Windows console encoding for UTF-8 support
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import argparse
from pathlib import Path

from rich.console import Console

console = Console()


def main():
    parser = argparse.ArgumentParser(
        description="🎬 Video Viral Analyzer & Rewriter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py https://www.youtube.com/watch?v=xxx
  python main.py https://v.douyin.com/xxx
  python main.py video.mp4 --asr-mode accurate
  python main.py https://b23.tv/xxx --output-dir ./results
        """,
    )

    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="Video URL or local file path",
    )
    parser.add_argument(
        "--input-file", "-f",
        help="Path to file containing URLs (one per line)",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="./output",
        help="Output directory (default: ./output)",
    )
    parser.add_argument(
        "--asr-mode",
        choices=["fast", "accurate"],
        default=None,
        help="ASR mode: fast (base model) or accurate (large-v3)",
    )
    parser.add_argument(
        "--asr-engine",
        choices=["whisper", "funasr"],
        default=None,
        help="ASR engine: whisper (default) or funasr",
    )
    parser.add_argument(
        "--language", "-l",
        default=None,
        help="Language: auto, zh, en (default: auto)",
    )
    parser.add_argument(
        "--skip-analysis",
        action="store_true",
        help="Only download and transcribe, skip LLM analysis",
    )
    parser.add_argument(
        "--rewrite-modes",
        nargs="+",
        default=["light", "viral"],
        help="Rewrite modes: light, viral (default: both)",
    )
    parser.add_argument(
        "--rewrite-styles",
        nargs="+",
        default=["storytelling"],
        help="Style rewrites: storytelling, emotional, educational, promotional",
    )
    parser.add_argument(
        "--proxy",
        default=None,
        help="HTTP proxy URL (e.g., http://127.0.0.1:7890)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--no-asr-correction",
        action="store_true",
        help="Disable LLM-based ASR error correction",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config and detect platform without downloading",
    )
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate configuration and exit",
    )

    args = parser.parse_args()

    # Build explicit config overrides from CLI args
    config_overrides = {}
    if args.output_dir:
        config_overrides["OUTPUT_DIR"] = args.output_dir
    if args.asr_mode:
        config_overrides["ASR_MODE"] = args.asr_mode
    if args.asr_engine:
        config_overrides["ASR_ENGINE"] = args.asr_engine
    if args.language:
        config_overrides["DEFAULT_LANGUAGE"] = args.language
    if args.proxy:
        config_overrides["HTTP_PROXY"] = args.proxy
    if args.no_asr_correction:
        config_overrides["ENABLE_ASR_CORRECTION"] = "false"

    # Set verbose logging
    if args.verbose:
        import logging
        from utils.logger import set_global_level
        set_global_level(logging.DEBUG)

    # Import after env setup
    from config import load_config, reset_config
    from pipeline import Pipeline

    reset_config()
    load_config(overrides=config_overrides)

    from config import get_config
    config = get_config()

    if args.validate_config:
        print("Validating configuration...")
        issues = []
        if not config.llm.api_key:
            issues.append("WARNING: LLM_API_KEY is not set. LLM analysis will fail.")
        if config.asr.engine not in ("whisper", "funasr"):
            issues.append(f"ERROR: Invalid ASR engine: {config.asr.engine}")
        if issues:
            for issue in issues:
                print(f"  {issue}")
        else:
            print("Configuration is valid.")
        return

    if args.dry_run:
        from utils.platform_detector import detect_platform
        if not args.input:
            print("Error: --dry-run requires an input URL")
            sys.exit(1)
        platform, metadata = detect_platform(args.input)
        print(f"Platform: {platform.value}")
        print(f"Metadata: {metadata}")
        print(f"Config: LLM API key {'set' if config.llm.api_key else 'NOT SET'}")
        print(f"Config: ASR engine: {config.asr.engine}")
        print("Dry run complete. No downloads will be made.")
        return

    if not args.input and not args.input_file:
        print("Error: either provide input URL or --input-file")
        sys.exit(1)

    # Banner
    console.print("\n[bold magenta]🎬 Short Go Viral[/bold magenta]\n")

    # Run pipeline
    pipeline = Pipeline()

    inputs = []
    if args.input_file:
        with open(args.input_file, 'r') as f:
            inputs = [line.strip() for line in f if line.strip()]
    else:
        inputs = [args.input]

    for inp in inputs:
        try:
            result = pipeline.run(
                url_or_path=inp,
                skip_analysis=args.skip_analysis,
                rewrite_modes=args.rewrite_modes,
                rewrite_styles=args.rewrite_styles,
            )

            # Save outputs
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            safe_name = inp.replace("/", "_").replace("\\", "_").replace(":", "_")[:50]
            json_path = output_dir / f"analysis_result_{safe_name}.json"
            result.to_json_file(str(json_path))
            console.print(f"\n📄 JSON saved: [cyan]{json_path}[/cyan]")

            md_path = output_dir / f"analysis_report_{safe_name}.md"
            md_path.write_text(result.to_markdown(), encoding="utf-8")
            console.print(f"📝 Report saved: [cyan]{md_path}[/cyan]")

            if result.virality:
                v = result.virality.scores
                console.print(f"\n[bold]🔥 Virality Score: {v.overall}/100[/bold]")
                console.print(
                    f"   Hook: {v.hook} | Emotion: {v.emotion} | "
                    f"Retention: {v.retention} | CTA: {v.cta} | Social: {v.social_currency}"
                )

            if result.errors:
                console.print(f"\n[yellow]⚠️ {len(result.errors)} error(s) occurred[/yellow]")

            console.print(f"\n✅ Done in {result.processing_time_seconds:.1f}s\n")

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user[/yellow]")
            sys.exit(1)
        except Exception as e:
            console.print(f"\n[red]Error processing {inp}: {e}[/red]")
            if args.verbose:
                import traceback
                traceback.print_exc()


if __name__ == "__main__":
    main()
