# ReasonLoop Configuration Guide

This document explains how to configure ReasonLoop using environment variables and the `.env` file.

## Overview

ReasonLoop has been migrated from JSON-based configuration to environment variable-based configuration using a `.env` file. This provides better security, easier deployment, and more flexible configuration management.

## Configuration Files

- **`.env`** - Main configuration file (not committed to version control)
- **`config/settings.py`** - Configuration loader and defaults
- **`test_config.py`** - Configuration validation script

## Environment Variables

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_OBJECTIVE` | "Create a 3-day itinerary for Bangkok" | Default task objective |
| `PROMPT_TEMPLATE` | "default_tasks" | Template for task generation |
| `MAX_RETRIES` | 2 | Maximum retry attempts for failed tasks |
| `RETRY_DELAY` | 2.0 | Delay between retries (seconds) |

### LLM Provider Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | "ollama" | LLM provider (ollama, anthropic, openai) |
| `LLM_TEMPERATURE` | 0.1 | Response randomness (0.0-2.0) |
| `LLM_MAX_TOKENS` | 2048 | Maximum tokens per response |
| `LLM_REPEAT_PENALTY` | 1.1 | Repetition penalty |
| `LLM_TOP_P` | 0.8 | Top-p sampling parameter |
| `LLM_SEED` | 42 | Random seed for reproducibility |
| `LLM_NUM_CTX` | 2048 | Context window size |

### Multi-Agent Ollama Models

ReasonLoop supports different models for different AI roles:

| Variable | Default | Role |
|----------|---------|------|
| `OLLAMA_MODEL_ORCHESTRATOR` | "minimax-m2:cloud" | Coordination and delegation |
| `OLLAMA_MODEL_PLANNER` | "gpt-oss:120b-cloud" | Strategic planning and task creation |
| `OLLAMA_MODEL_EXECUTOR` | "gpt-oss:20b-cloud" | Content generation and execution |
| `OLLAMA_MODEL_REVIEWER` | "gpt-oss:20b-cloud" | Quality review and analysis |
| `OLLAMA_MODEL` | "minimax-m2:cloud" | Default/fallback model |

### Ollama Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_API_URL` | "http://localhost:11434/api/generate" | Ollama API endpoint |

### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | "localhost" | Database host |
| `DB_PORT` | 3306 | Database port |
| `DB_USER` | "root" | Database username |
| `DB_PASSWORD` | "" | Database password |
| `DB_DATABASE` | "reasonloop" | Database name |

### Web Search Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `WEB_SEARCH_ENABLED` | true | Enable web search capability |
| `WEB_SEARCH_RESULTS_COUNT` | 5 | Number of search results to return |

### Other Provider Settings (Optional)

#### Anthropic
| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | "" | Anthropic API key |
| `ANTHROPIC_MODEL` | "claude-instant-1.2" | Anthropic model |

#### OpenAI
| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | "" | OpenAI API key |
| `OPENAI_MODEL` | "gpt-3.5-turbo" | OpenAI model |

## Setup Instructions

### 1. Create .env File

Copy the example configuration to create your `.env` file:

```bash
cp .env.example .env  # If you have an example file
# OR create .env manually with your settings
```

### 2. Configure Ollama Models

Make sure you have the required Ollama models installed:

```bash
# Pull the models specified in your .env file
ollama pull minimax-m2:cloud
ollama pull gpt-oss:120b-cloud
ollama pull gpt-oss:20b-cloud

# Verify models are available
ollama list
```

### 3. Validate Configuration

Run the configuration test to verify everything is set up correctly:

```bash
python test_config.py
```

For verbose output:
```bash
python test_config.py --verbose
```

### 4. Test Multi-Agent Setup

Test the multi-agent functionality:

```bash
# Dry run (no API calls)
python example_multi_agent.py --dry-run

# Full test (requires Ollama to be running)
python example_multi_agent.py
```

## Multi-Agent Architecture

### Role Determination

The system automatically determines which AI model to use based on task keywords:

- **Orchestrator** (`minimax-m2:cloud`): Coordination tasks
- **Planner** (`gpt-oss:120b-cloud`): Tasks containing "create", "plan", "design", "outline", "structure"
- **Executor** (`gpt-oss:20b-cloud`): Tasks containing "execute", "implement", "generate", "write", "produce"
- **Reviewer** (`gpt-oss:20b-cloud`): Tasks containing "review", "analyze", "evaluate", "check", "validate"

### Using Specific Roles

You can specify a role when calling text completion:

```python
from abilities.text_completion import text_completion_ability

# Use specific role
response = text_completion_ability("Create a plan", role="planner")

# Use default role determination
response = text_completion_ability("Create a plan")
```

## Security Best Practices

1. **Never commit `.env` files** - They're already in `.gitignore`
2. **Use environment-specific files** - `.env.development`, `.env.production`
3. **Rotate API keys regularly** - Especially for production environments
4. **Use secure database passwords** - Avoid empty passwords in production

## Troubleshooting

### Configuration Not Loading

1. Verify `.env` file exists in project root
2. Check file permissions
3. Install python-dotenv: `pip install python-dotenv`
4. Run configuration test: `python test_config.py`

### Ollama Connection Issues

1. Start Ollama service: `ollama serve`
2. Verify models are installed: `ollama list`
3. Check API URL in `.env`: `OLLAMA_API_URL=http://localhost:11434/api/generate`
4. Test connection: `python example_multi_agent.py --skip-demo`

### Database Connection Issues

1. Verify database server is running
2. Check database credentials in `.env`
3. Test connection manually
4. Verify database exists: `mysql -u root -p -e "SHOW DATABASES;"`

### Web Search Not Working

1. Check `WEB_SEARCH_ENABLED=true` in `.env`
2. Verify internet connection
3. Check logs for specific error messages

## Migration from JSON Config

If you're migrating from the old `config/settings.json` approach:

1. **Backup your old config**: `cp config/settings.json config/settings.json.backup`
2. **Create `.env` file** with equivalent settings
3. **Remove old JSON file**: The system will now use `.env` by default
4. **Test configuration**: `python test_config.py`

## Example .env File

```env
# ReasonLoop Configuration

# General Settings
DEFAULT_OBJECTIVE=Create a 3-day itinerary for Bangkok
PROMPT_TEMPLATE=default_tasks
MAX_RETRIES=2
RETRY_DELAY=2.0

# LLM Provider Configuration
LLM_PROVIDER=ollama

# Ollama API Configuration
OLLAMA_API_URL=http://localhost:11434/api/generate

# Multi-Agent Model Configuration
OLLAMA_MODEL_ORCHESTRATOR=minimax-m2:cloud
OLLAMA_MODEL_PLANNER=gpt-oss:120b-cloud
OLLAMA_MODEL_EXECUTOR=gpt-oss:20b-cloud
OLLAMA_MODEL_REVIEWER=gpt-oss:20b-cloud

# Default Ollama Model (for backward compatibility)
OLLAMA_MODEL=minimax-m2:cloud

# LLM Parameters
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=2048
LLM_REPEAT_PENALTY=1.1
LLM_TOP_P=0.8
LLM_SEED=42
LLM_NUM_CTX=2048

# Web Search Configuration
WEB_SEARCH_ENABLED=true
WEB_SEARCH_RESULTS_COUNT=5

# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_DATABASE=reasonloop
```

## Dependencies

Make sure you have the required dependencies installed:

```bash
pip install python-dotenv
# OR if using poetry
poetry add python-dotenv
```

The following packages are automatically included:
- `python-dotenv>=1.0.0` - Environment variable loading
- `requests>=2.32.5` - HTTP requests for API calls
- `mysql-connector-python` - MySQL database connectivity (if using database features)

## Support

For configuration issues:
1. Run `python test_config.py --verbose` to see all settings
2. Check the logs in the `logs/` directory
3. Verify your Ollama models are working: `ollama list`
4. Test individual components with the example scripts