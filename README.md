# ReasonLoop 🤖

A modular AI agent system with comprehensive metrics tracking, multi-provider LLM support, and intelligent task orchestration.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ Features

- **🤖 Multi-Agent Orchestration**: Intelligent task breakdown and execution
- **📊 Real-Time Metrics**: Actual token usage, costs, and performance tracking
- **🔄 Multi-Provider Support**: XAI (Grok), OpenAI, Anthropic, Ollama, Z.ai
- **⚡ Async Architecture**: Concurrent task execution with proper resource management
- **🎯 Role-Based Models**: Different AI models optimized for planning, execution, and review
- **📈 Comprehensive Analytics**: Session-based metrics with cost optimization insights
- **🛡️ Production Ready**: Comprehensive error handling and connection validation

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd ReasonLoop

# Install dependencies
pip install -r requirements.txt

# Or use poetry (recommended)
poetry install
```

### 2. Configuration

Create your `.env` file:

```bash
cp .env.example .env
# Edit .env with your settings
```

#### XAI Configuration (Recommended)

```env
# LLM Provider
LLM_PROVIDER=xai

# API Configuration
XAI_API_KEY=your-xai-api-key
XAI_MODEL=grok-4-1-fast-non-reasoning

# Role-based models (automatically selected based on task type)
XAI_MODEL_ORCHESTRATOR=grok-4-1-fast-non-reasoning
XAI_MODEL_PLANNER=grok-4-1-fast-non-reasoning
XAI_MODEL_EXECUTOR=grok-4-1-fast-non-reasoning
XAI_MODEL_REVIEWER=grok-4-1-fast-non-reasoning

# Basic settings
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4096
```

#### Other Providers

<details>
<summary>OpenAI Configuration</summary>

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4
```

</details>

<details>
<summary>Anthropic Configuration</summary>

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-api-key
ANTHROPIC_MODEL=claude-sonnet-3.5
```

</details>

<details>
<summary>Ollama Configuration</summary>

```env
LLM_PROVIDER=ollama
OLLAMA_API_URL=http://localhost:11434/api/generate
OLLAMA_MODEL=llama3
```

</details>

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

### Template Examples

<details>
<summary>Available Templates</summary>

- **default_tasks**: General-purpose task execution
- **marketing_insights**: Marketing analysis and strategy
- **revenue_optimization**: Revenue-focused analysis
- **ecommerce_metrics**: E-commerce performance analysis
- **autonomous_ecommerce_growth**: Comprehensive e-commerce growth strategy

</details>

## 📊 Metrics & Analytics

ReasonLoop provides comprehensive metrics tracking:

### Real-Time Metrics
- **Token Usage**: Actual tokens consumed from LLM APIs
- **Cost Tracking**: Real USD costs from provider APIs
- **Performance**: Tokens per second, response times
- **Provider Efficiency**: Multi-provider comparison

### Session Analytics
```json
{
  "usage": {
    "prompt_tokens": 407,
    "completion_tokens": 1173,
    "total_tokens": 1580,
    "model": "grok-4-1-fast-non-reasoning",
    "provider": "xai",
    "cost_usd": 0.64375,
    "usage_source": "api"
  }
}
```

### Metrics Files
- **Prompt Logs**: `logs/prompts/YYYYMMDD_HHMMSS_ability_taskN_prompt.json`
- **Session Metrics**: `logs/metrics/session_ID_timestamp.json`
- **Application Logs**: `logs/reasonloop_timestamp.log`

## 🏗️ Architecture

### Core Components

```
ReasonLoop/
├── abilities/              # Individual AI capabilities
│   ├── text_completion.py  # LLM integration with metrics
│   ├── web_search.py       # Web search functionality
│   ├── web_scrape.py       # Content extraction
│   └── ...
├── core/                   # Execution engine
│   ├── execution_loop.py   # Main orchestration logic
│   └── task_manager.py     # Task breakdown and execution
├── config/                 # Configuration management
├── utils/                  # Utilities and helpers
│   ├── metrics.py         # Metrics collection and tracking
│   ├── llm_utils.py       # LLM provider utilities
│   └── prompt_logger.py    # Comprehensive logging
└── templates/             # Prompt templates for different use cases
```

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

## 📈 Use Cases

### Research & Analysis
- **Market Research**: Automated competitive analysis
- **Technical Documentation**: API documentation generation
- **Academic Research**: Literature review and synthesis
- **Data Analysis**: Database queries and insights

### Content & Marketing
- **Content Strategy**: Blog posts, articles, social media
- **Marketing Campaigns**: Multi-channel campaign development
- **SEO Optimization**: Keyword research and content optimization
- **Brand Analysis**: Competitor benchmarking and positioning

### Business Intelligence
- **Performance Analytics**: KPI tracking and optimization
- **Customer Insights**: Segmentation and behavior analysis
- **Revenue Optimization**: Pricing strategies and upselling
- **Process Automation**: Workflow optimization and streamlining

### E-commerce
- **Product Research**: Market analysis and competitive intelligence
- **Customer Journey**: Experience optimization and conversion analysis
- **Inventory Management**: Demand forecasting and stock optimization
- **Campaign Performance**: Multi-channel attribution and ROI analysis

## 🛠️ Troubleshooting

### Common Issues

<details>
<summary>API Connection Errors</summary>

**Problem**: `✗ LLM API Test Failed: API key is invalid`

**Solution**: 
1. Check your `.env` file has the correct API key
2. Verify the API key has sufficient credits
3. Test with provider's direct API

</details>

<details>
<summary>High Costs</summary>

**Problem**: Unexpectedly high token usage

**Solution**:
1. Review metrics in `logs/prompts/` files
2. Use shorter, more specific prompts
3. Consider switching to more cost-effective models
4. Enable caching where possible

</details>

<details>
<summary>Poor Performance</summary>

**Problem**: Slow execution or timeouts

**Solution**:
1. Check internet connectivity
2. Verify API rate limits
3. Use `--verbose` flag for debugging
4. Consider using faster models for simpler tasks

</details>

### Debug Mode

```bash
# Enable verbose logging
python main.py --objective "Your task" --verbose

# Check specific log files
tail -f logs/reasonloop_$(date +%Y%m%d)*.log
```

## 📋 Requirements

- **Python**: 3.8 or higher
- **Dependencies**: See `requirements.txt`
- **API Access**: At least one LLM provider (XAI, OpenAI, Anthropic, or Ollama)
- **Internet**: Required for web-based abilities and API calls
- **Memory**: 2GB+ recommended for complex tasks

## 🔒 Security & Privacy

- **API Keys**: Stored in environment variables (`.env`)
- **Data Handling**: No persistent storage of sensitive data
- **Logs**: Automatic rotation and cleanup
- **Privacy**: Local processing where possible

## 📄 License

MIT License - see LICENSE file for details

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

- **Issues**: Use GitHub Issues for bugs and feature requests
- **Documentation**: Check `docs/` directory for detailed guides
- **Examples**: See `examples/` directory for usage patterns

## 🗺️ Roadmap

- [ ] **Web UI**: Interactive dashboard for task management
- [ ] **Streaming**: Real-time response streaming
- [ ] **Plugin System**: Third-party ability integration
- [ ] **Advanced Analytics**: ML-powered performance insights
- [ ] **Team Collaboration**: Multi-user workspace support
- [ ] **API Gateway**: RESTful API for external integrations

## 🙏 Acknowledgments

Built with modern Python async architecture, inspired by autonomous agent frameworks, and designed for production-scale AI task orchestration.

---

**Ready to automate your AI workflows?** Start with a simple objective and see ReasonLoop break it down into actionable tasks! 🚀