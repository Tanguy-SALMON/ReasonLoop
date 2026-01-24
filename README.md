# ReasonLoop 🤖

A modular AI agent system with comprehensive metrics tracking, multi-provider LLM support, and intelligent task orchestration.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)


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
# Multi-Agent Creative Team (recommended for email campaigns)
# Uses Copywriter, Art Director, and Developer agents
python main.py --template email_creative_team --objective "Generate emails for https://example.com"

# Simpler email generation (4-task pipeline)
python main.py --template email_campaign_generator --objective "Generate emails for https://example.com"

# Website intelligence and email campaign generation
# Outputs: output/yoursite.com/emails/minimalist.html, bold.html, elegant.html
python main.py --template email_creative_team --objective "Generate branded emails for https://yoursite.com" --verbose

# Deep website scraping with screenshots
python main.py --objective "Crawl https://example.com with screenshots, max_pages=5, save to output/example.com/screenshots/"

# Website intelligence extraction
python main.py --objective "Analyze https://example.com for brand identity, products, and customer insights"

# Verbose logging for debugging
python main.py --objective "Create a business plan" --verbose
```

## 🎨 Multi-Agent Creative Team

The `email_creative_team` agent orchestrates a team of specialists to create professional email campaigns:

### The Team

| Role | Responsibility |
|------|----------------|
| **@copywriter** | Subject lines, headlines, body copy, CTAs |
| **@art_director** | Layout, colors, typography, spacing |
| **@developer** | Production HTML, inline CSS, compatibility |

### Workflow (11 tasks)

```
Phase 1: Brand Research (website-intelligence)
    │
    ├── Phase 2: Copywriting (3 personas in parallel)
    │   ├── MINIMALIST copy
    │   ├── BOLD copy
    │   └── ELEGANT copy
    │
    ├── Phase 3: Art Direction (3 personas)
    │   ├── MINIMALIST design specs
    │   ├── BOLD design specs
    │   └── ELEGANT design specs
    │
    ├── Phase 4: Development (3 HTML templates)
    │   ├── minimalist.html
    │   ├── bold.html
    │   └── elegant.html
    │
    └── Phase 5: Save templates to output/
```

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


## 📦 Use as a Python Package

ReasonLoop can be installed as a Python package in your main application:

```bash
pip install -e /path/to/ReasonLoop
```

```python
from reasonloop import run_agent

# Run an agent template
result = run_agent(
    "email_campaign_generator", 
    "Generate emails for https://www.shiseido.com/us/en/"
)
```

### Real-World Example: BE-Campaign Integration

ReasonLoop is designed to be integrated into larger applications using an **Asynchronous Sidecar** strategy:

- **Web Scraping**: Crawl client websites to extract brand assets
- **AI Analysis**: Analyze brand identity, tone, colors, and products
- **Data Enrichment**: Adjust email content tone based on brand intelligence
- **Formatted Document Generation**: Create branded HTML templates and reports

```python
# In BE-Campaign's email automation workflow
from reasonloop import run_agent

# Step 1: Extract brand intelligence from client's website
result = run_agent(
    "email_website_intelligence",
    "https://www.client-brand.com"
)

# Step 2: Generate branded email templates
result = run_agent(
    "email_campaign_generator",
    "Generate emails for https://www.client-brand.com"
)

# Output saved to: output/www.client-brand.com/
# ├── intelligence/    <- Brand data for tone adjustment
# ├── emails/          <- Ready-to-use HTML templates
# └── metrics/         <- Execution analytics
```

---

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

### Creating Agent Definitions

2. Use with `--template` flag:
```bash
python main.py --template my_custom_agent --objective "Your objective here"
```



```bash
# Enable verbose logging
python main.py --objective "Your task" --verbose

# Check specific log files
tail -f logs/reasonloop_$(date +%Y%m%d)*.log
```


## 📄 License

MIT License - see LICENSE file for details
