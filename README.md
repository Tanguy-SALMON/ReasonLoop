# Clone the repository
git clone https://github.com/yourusername/reasonloop.git
cd reasonloop

# Install dependencies
pip install -r requirements.txt

# Or use poetry (recommended)
poetry install
```

### 2. Configuration

Create your `.env` file from the example:
```bash
cp .env.example .env
# Edit .env file with your settings
```

#### OpenAI-Compatible Configuration (Recommended)
```env
# LLM Provider
LLM_PROVIDER=openai

# API Configuration
OPENAI_API_URL=https://api.z.ai/api/paas/v4/chat/completions
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=glm-4.6

# Multi-Agent Models (all using GLM-4.6)
OPENAI_MODEL_ORCHESTRATOR=glm-4.6
OPENAI_MODEL_PLANNER=glm-4.6
OPENAI_MODEL_EXECUTOR=glm-4.6
OPENAI_MODEL_REVIEWER=glm-4.6

# Basic settings
LLM_TEMPERATURE=0.7
WEB_SEARCH_ENABLED=true
```

#### Ollama Configuration
```env
# LLM Provider
LLM_PROVIDER=ollama

# Multi-Agent Models
OLLAMA_MODEL_ORCHESTRATOR=minimax-m2:cloud
OLLAMA_MODEL_PLANNER=gpt-oss:120b-cloud
OLLAMA_MODEL_EXECUTOR=gpt-oss:20b-cloud
OLLAMA_MODEL_REVIEWER=gpt-oss:20b-cloud

# Basic settings
LLM_TEMPERATURE=0.1
WEB_SEARCH_ENABLED=true
```

### 3. Test Configuration

```bash
# Validate your configuration
python test_config.py

# Run multi-agent demo
python example_multi_agent.py
```

## 🎮 Usage

### Basic Usage

```bash
# Run with default objective and template
python main.py

# Specify custom objective
python main.py --objective "Create a marketing plan for a new product"

# Use specific template
python main.py --template marketing_insights --objective "Analyze customer data"

# List available abilities
python main.py --list-abilities
```

### Template Examples

#### Marketing Insights Template
```bash
python main.py --template marketing_insights --objective "Analyze Q3 sales data and provide actionable insights"
```

#### Propensity Modeling Template  
```bash
python main.py --template propensity_modeling --objective "Create personalized email campaign for customer segment"
```

#### Default Tasks Template
```bash
python main.py --template default_tasks --objective "Research and summarize competitor strategies"
```

### Multi-Agent Features

The system automatically assigns different AI models based on task type:
- **Planning tasks** → Uses larger models for complex reasoning
- **Execution tasks** → Uses models optimized for content generation
- **Review tasks** → Uses models focused on analysis and validation
- **Coordination tasks** → Uses orchestration models

## 🏗️ Project Structure

```
reasonloop/
├── abilities/            # Individual capabilities
│   ├── ability_registry.py
│   ├── text_completion.py
│   ├── Web Search.py
│   ├── web_scrape.py
│   └── mysql_abilities.py
├── config/               # Configuration settings
│   ├── settings.py
│   └── logging_config.py
├── core/                 # Core execution logic
│   ├── execution_loop.py
│   └── task_manager.py
├── models/               # Data models
│   ├── task.py
│   └── result.py
├── templates/            # Prompt templates for different agent types
│   ├── default_tasks.json
│   ├── marketing_insights.json
│   └── propensity_modeling.json
├── utils/                # Utility functions
│   └── json_parser.py
├── logs/                 # Log files (created at runtime)
├── main.py               # Entry point
├── example_multi_agent.py # Demo script
└── requirements.txt      # Dependencies
```

## 🔧 Extending ReasonLoop

### Adding a New Ability

1. Create a new file in the `abilities/` directory
2. Implement your ability function
3. Register it with the ability registry
4. Update the task creation prompt in `core/task_manager.py`

Example:
```python
# abilities/image_generation.py
def image_generation_ability(prompt: str) -> str:
    # Implementation here
    return "URL to generated image"

# Register this ability
from abilities.ability_registry import register_ability
register_ability("image-generation", image_generation_ability)
```

### Adding a New Template

1. Create a new JSON file in the `templates/` directory
2. Define the template structure with system_message and task_prompt
3. Include placeholders for dynamic content
4. Test with `--template` flag

## 🎯 Use Cases

- **Research Assistant**: Gather and synthesize information on specific topics
- **Data Analysis**: Query databases and analyze results
- **Content Creation**: Generate structured content based on research
- **Marketing Intelligence**: Analyze customer data and provide insights
- **Campaign Optimization**: Personalize email and marketing campaigns
- **Task Automation**: Break down complex objectives into executable steps

## 📋 Requirements

- Python 3.8+
- Required packages listed in requirements.txt
- Internet connection for web-based abilities
- MySQL database for database abilities (optional)
- LLM API access (OpenAI, Ollama, Anthropic, or Z.ai)

## 📄 License

MIT License

## 🙏 Acknowledgements

ReasonLoop is inspired by BabyCatAGI, a fork of BabyAGI and other autonomous agent frameworks that leverage language models for task execution.

## ⚠️ Note

ReasonLoop is designed for educational and research purposes. Always review the outputs and ensure they meet your requirements before using them in production environments.

---

## 🔮 Next Development Steps

- [ ] Implement additional specialized templates for different domains
- [ ] Add streaming response support
- [ ] Enhance error recovery mechanisms
- [ ] Integrate more specialized abilities (image generation, code execution, etc.)
- [ ] Add web UI for easier interaction
- [ ] Implement task result caching for improved performance