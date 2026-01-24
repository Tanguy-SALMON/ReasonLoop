# Changelog

All notable changes to ReasonLoop will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-01-24

### Added
- **Multi-Agent Creative Team**: New orchestrated agent system with specialized roles
  - `email_creative_team.md` - 11-task orchestrator for professional email campaigns
  - `agents/roles/copywriter.md` - Expert email copywriter (subject lines, headlines, body copy, CTAs)
  - `agents/roles/art_director.md` - Visual design specialist (layout, colors, typography, spacing)
  - `agents/roles/developer.md` - Email HTML developer (production-ready, cross-client compatible)
- **Role-Based Task Execution**: Tasks can now specify a `role` field to use specialized agent prompts
  - Task list displays roles with `@role` annotation (e.g., `@copywriter`, `@art_director`)
  - Roles are passed through to text-completion for context-aware generation
- **JSON Parser Fix**: Improved regex handling for LLM responses with embedded backticks
  - Fixed issue where ` ```html ` in task descriptions broke JSON extraction
  - Now uses greedy matching with secondary bracket extraction

### Changed
- **Task Manager**: Updated to support role-based execution
  - `_execute_ability()` now accepts optional `role` parameter
  - Increased dependency output context from 2000 to 4000 chars for richer context
  - Task display shows role annotations in magenta color
- **Email Pipeline**: 11-task workflow (was 4) for higher quality output
  - Separate copywriting, art direction, and development phases
  - 3 personas processed in parallel branches (minimalist, bold, elegant)

### Output Structure
```
output/{domain}/
├── emails/
│   ├── minimalist.html
│   ├── bold.html
│   └── elegant.html
├── intelligence/
│   └── intelligence.json
└── metrics/
    └── session_{timestamp}.json
```

## [0.3.0] - 2026-01-24

### Added
- **Multi-LLM Provider Support**: Added Anthropic (Claude) and OpenAI providers to `text_completion.py`
  - Anthropic models: `claude-opus-4-5-20251101`, `claude-sonnet-4-20250514`, `claude-3-5-sonnet-20241022`, `claude-3-haiku-20240307`
  - OpenAI models: `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-3.5-turbo`
  - Easy switching via `LLM_PROVIDER` environment variable
  - Role-based model selection (orchestrator, planner, executor, reviewer)
- **Updated Database Schema**: Enhanced `schema_website_intelligence_simple.sql` with:
  - `design_typography`, `design_spacing`, `design_borders`, `design_shadows`, `design_buttons`, `design_layout` columns
  - `llm_provider` and `llm_model` tracking columns
  - `output_session` path column
  - Additional indexes for `status`, `platform`, `pricing_tier`
  - Comprehensive example queries for LLM comparison and design extraction
- **Pricing Table**: Added cost tracking for all providers (per 1M tokens)

### Changed
- **Explicit Save Task**: Email saving is now an explicit task in the pipeline (not hidden in ability)
  - Updated `email_design_agent.md` to v1.1 with `save-email-templates` as a separate task
  - Removed auto-save logic from `email_design_ability`
- **Simplified Task Manager**: Removed special-case ability handling
  - All non-text-completion abilities now receive consistent parameters: `content` + `domain`
  - Cleaner, more maintainable code
- **Updated .env Configuration**: Added comprehensive Anthropic and OpenAI sections with available models

### Fixed
- Abilities now accept `**kwargs` to handle extra parameters from task_manager gracefully

## [0.2.1] - 2026-01-24

### Added
- **Save Email Templates Ability**: New `save-email-templates` ability that extracts HTML email templates from task output and saves them to `output/[domain]/emails/` folder
- Automatic detection of HTML code blocks and template markers (e.g., `<!-- TEMPLATE 1: MINIMALIST -->`)
- Support for extracting multiple templates (minimalist, bold, elegant) from a single task output

### Changed
- Updated `email_campaign_generator` agent to v1.2 with streamlined 4-task pipeline (was 5 tasks)
- Task manager now passes full dependency output to `save-email-templates` ability (not truncated)
- Replaced `write-file` with dedicated `save-email-templates` ability for better HTML handling

### Fixed
- Email templates now properly saved to `output/[domain]/emails/` folder instead of being lost in session logs

## [0.2.0] - 2026-01-24

### Added
- **Web Scraping System**: Deep website crawling with Playwright for JavaScript rendering
- **Website Intelligence**: Extract brand identity, products, design systems, and customer insights
- **Email Campaign Generation**: Automated branded email creation from website analysis
- **URL Normalization**: Intelligent base URL detection (keeps/removes locale paths based on context)
- **Organized Output Sessions**: Timestamped folders with screenshots/emails/data/summary.md
- **Colored Terminal Output**: Beautiful, readable output with progress bars and status indicators
- **Output Manager**: Centralized file organization with automatic summary generation
- Project structure reorganization (templates → agents, outputs → sessions)
- Clean, timestamp-free console logging (timestamps kept in log files)

### Changed
- Dramatically improved terminal UX with colors and visual indicators
- Reduced logging verbosity (moved detailed logs to DEBUG level)
- Updated folder structure: agents/, sessions/, DOCS/, experiments/
- Better task list display with truncation and clear dependencies
- Progress bars showing completion status visually

### Fixed
- Missing dependencies (playwright, nest-asyncio, colorama)
- Verbose agent loading messages cluttering output
- Long task descriptions breaking readability
- Unclear execution progress

## [0.1.0] - Previous Release

### Added
- Comprehensive LLM metrics tracking with real API usage data
- Session-based metrics management with unique IDs and timestamps
- Cost tracking with provider-specific pricing (XAI: $0.20/M input, $0.50/M output, $0.05/M cached input)
- Real-time performance monitoring (tokens/second, execution time, efficiency scores)
- Multi-provider LLM support with role-based model selection
- Production-ready error handling and connection validation
- Professional CLI with detailed configuration display and progress indicators

### Fixed
- **Critical**: LLM metrics system now captures actual usage data instead of empty objects
- **Critical**: Corrected XAI cost calculation with proper per-million token pricing
- **Critical**: Fixed tick conversion from XAI API (ticks ÷ 10,000,000 = USD)
- **Critical**: Removed duplicate logging calls that bypassed usage data capture
- **Critical**: Fixed missing `json` import causing API response parsing errors
- Simplified provider architecture to focus on XAI (Grok) implementation
- Enhanced error messages with troubleshooting guidance for API connectivity
- Improved metrics validation to ensure data integrity

### Changed
- **Major**: Migrated from estimated token counting to real API usage data
- **Major**: Updated pricing table to reflect actual XAI costs per million tokens
- **Major**: Simplified codebase architecture (removed complex multi-provider abstractions)
- **Major**: Enhanced user experience with professional welcome banners and progress tracking
- **Major**: Upgraded README.md with comprehensive documentation and current examples
- Improved metrics storage format with additional context and validation
- Enhanced logging with detailed debugging information and performance tracking
- Updated command-line interface with better argument handling and validation

### Deprecated
- Old CONFIG.md file (superseded by comprehensive README.md)
- Legacy main_metrics.py (replaced by superior main.py implementation)
- Estimation-based token counting (replaced by real API data)
- Basic error handling approach (replaced by comprehensive validation)

### Removed
- Outdated CONFIG.md documentation (redundant with updated README.md)
- Legacy main_metrics.py entry point (functionality merged into main.py)
- Complex multi-provider factory patterns (simplified to XAI-focused implementation)
- Manual code patching approach (replaced by clean integration)
- Basic token estimation logic (replaced by real API usage tracking)

### Security
- Enhanced API key validation and connection testing before execution
- Improved error handling to prevent information leakage in logs
- Better input validation for configuration parameters
- Secure environment variable handling for sensitive credentials

### Performance
- **Major**: Async/await architecture for concurrent task execution
- **Major**: Session-based metrics collection (no manual patching required)
- **Major**: Real API usage tracking eliminates estimation overhead
- **Major**: Optimized provider selection with role-based model assignment
- Reduced memory footprint through simplified provider architecture
- Improved response times with connection validation and retry logic

## [1.0.0] - 2026-01-16

### Added
- Initial ReasonLoop implementation with multi-agent orchestration
- Basic task management and execution loop
- Support for multiple LLM providers (XAI, OpenAI, Anthropic, Ollama)
- Environment-based configuration system
- Basic metrics collection framework
- CLI interface with command-line argument parsing
- Template-based prompt management system

### Known Issues
- Token counting relied on character-based estimation
- Cost calculation used placeholder pricing structures
- Limited error handling and recovery mechanisms
- Basic user experience without comprehensive feedback

## Technical Debt Addressed

### Before (Issues)
- Empty usage data in all logs (`"usage": {}`)
- Incorrect cost calculations based on wrong pricing assumptions
- Manual code patching for metrics injection
- Complex multi-provider architecture with limited benefits
- Outdated documentation not reflecting current system capabilities

### After (Solutions)
- Complete usage data capture from XAI API responses
- Accurate cost calculation using real provider pricing
- Clean integration through MetricsManager class
- Simplified architecture focused on production use cases
- Comprehensive documentation with current examples and troubleshooting

### Metrics Improvement
- **Before**: 0% metrics capture (empty usage objects)
- **After**: 100% metrics capture (real API data)
- **Improvement**: Complete visibility into LLM usage patterns and costs

### Cost Accuracy
- **Before**: Estimated costs based on character counting
- **After**: Real costs from XAI API (`cost_in_usd_ticks`)
- **Improvement**: Precise financial tracking for budget management

### User Experience
- **Before**: Basic CLI with minimal feedback
- **After**: Professional interface with comprehensive metrics and progress tracking
- **Improvement**: Production-ready user experience with detailed analytics

## Migration Guide

### For Existing Users
1. **Backup current logs**: Metrics structure has changed significantly
2. **Update configuration**: Ensure XAI API key is properly configured
3. **Review pricing**: Costs are now calculated using actual XAI rates
4. **Test setup**: Run `python main.py --list-abilities` to verify configuration

### Configuration Changes
- **No breaking changes** to environment variable structure
- **Enhanced validation** will provide clearer error messages
- **New metrics files** will be created in `logs/prompts/` and `logs/metrics/`

### New Features to Explore
- **Real-time metrics**: Check `logs/prompts/` for detailed usage data
- **Session tracking**: Review `logs/metrics/` for comprehensive analytics
- **Cost optimization**: Use metrics to identify expensive operations
- **Performance monitoring**: Analyze tokens/second and efficiency scores

## Support

For issues related to these changes:
- **Metrics questions**: Check logs in `logs/prompts/` for usage data
- **Cost discrepancies**: Verify XAI API key and account status
- **Configuration issues**: Run with `--verbose` flag for detailed logging
- **Migration problems**: Review this changelog for breaking changes

---

**Note**: This changelog documents the transformation from a basic multi-agent system to a production-ready platform with comprehensive metrics tracking, accurate cost calculation, and professional user experience.