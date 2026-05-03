# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-05-03

### Added
- Twitter/X image/text note support with vision LLM analysis
- Instagram crawler module with Reels/Post/Stories support
- Content caching system with TTL support
- Pipeline metrics collection and reporting
- Long video chunk processing for memory-efficient ASR
- Platform handler registry for extensible download support
- Pipeline stage framework for customizable workflows
- Rich progress bar for pipeline execution
- Unified anti-detection headers for all crawlers
- Configuration validation with actionable error messages
- Custom exception hierarchy with error codes and context

### Changed
- Refactored global state to dependency injection pattern
- Integrated metrics into pipeline stage tracking
- Improved error messages with troubleshooting hints
- Enhanced security with path traversal protection
- Added FunASR model caching for better performance
- Fixed LLM prompt injection vulnerabilities

### Fixed
- Cache never being written (now caches results correctly)
- Test assertion for default ASR engine
- Package structure and CLI entry point

### Removed
- All external project references ("Ported from...")
- Dead code and unused imports

## Migration

### From v1.x to v2.0

#### Breaking Changes

1. **Python version**: Minimum Python 3.9 (was 3.8)
2. **Config**: `LLM_API_KEY` is now required for LLM analysis stages
3. **Output directory**: Must be within current working directory (path traversal protection)
4. **CLI entry point**: Changed from `viral-analyzer` to `go-viral-video`

#### New Features

- Content caching (automatic, in `./output/.cache/`)
- Pipeline metrics (accessible via `from metrics import metrics`)
- Long video chunk processing (automatic for videos >5 min)
- Instagram image/text note support
- Twitter/X image/text note support

#### Migration Steps

1. Update Python to 3.9+
2. Update `.env` with `LLM_API_KEY`
3. Reinstall: `pip install -e .[full]`
4. Clear old cache: `rm -rf output/`
5. Run: `go-viral-video --validate-config`
