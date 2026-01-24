# ReasonLoop 🤖

A modular AI agent system with comprehensive metrics tracking, multi-provider LLM support, and intelligent task orchestration.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ Features

- **🤖 Multi-Agent Orchestration**: Intelligent task breakdown and execution
- **📊 Real-Time Metrics**: Actual token usage, costs, and performance tracking



### 3. Test Your Setup

```bash
# List available abilities
python main.py --list-abilities

# Test with simple objective
python main.py --objective "What is Python?" --verbose
```

## 🎯 Usage

### Basic Examples

```bash
# Simple task execution
python main.py --objective "Explain quantum computing in simple terms"

# Research and analysis
python main.py --objective "Research the latest trends in artificial intelligence and create a comprehensive report"

# Creative content generation
python main.py --objective "Write a marketing strategy for a sustainable fashion startup"

# Technical documentation
python main.py --objective "Create a technical specification for a REST API"
```

### Advanced Usage

```bash
# Use specific template
python main.py --template default_tasks --objective "Analyze competitor pricing strategies"

# Verbose logging for debugging
python main.py --objective "Create a business plan" --verbose

# Custom model selection
python main.py --objective "Debug this Python code" --model gpt-4-turbo
```

## 🏗️ Architecture


### Agent Roles & Model Selection

- **🤖 Orchestrator**: High-level coordination and planning
- **📋 Planner**: Task breakdown and strategy development  
- **⚡ Executor**: Content generation and implementation
- **🔍 Reviewer**: Analysis, validation, and quality assurance

## 🔧 Development

### Adding New Abilities

1. Create ability in `abilities/` directory:
```python
# abilities/my_custom_ability.py
def my_custom_ability(prompt: str) -> str:
    # Your implementation
    return "Custom result"
```

2. Register in `abilities/ability_registry.py`:
```python
register_ability("my-custom", my_custom_ability)
```

3. Use in tasks:
```bash
python main.py --objective "Use my custom ability to process this data"
```

### Creating Templates

1. Add JSON template to `templates/`:
```json
{
  "name": "my_template",
  "description": "My custom template",
  "system_message": "You are a specialized agent...",
  "task_prompt": "Given this objective: {objective}..."
}
```

2. Use with `--template` flag:
```bash
python main.py --template my_template --objective "Your objective here"
```


### Debug Mode

```bash
# Enable verbose logging
python main.py --objective "Your task" --verbose

# Check specific log files
tail -f logs/reasonloop_$(date +%Y%m%d)*.log
```


## 📄 License

MIT License - see LICENSE file for details
