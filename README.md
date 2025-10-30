### README.md

#### Project
- Ultra-minimal async agent runner using Ollama (qwen3:4b-instruct) and plain SQL (aiomysql).
- Files: app.py, abilities.py, agent_loader.py, memory.py, agent.yaml, .env

#### Bootstrap
- Root files to create:
  - app.py
  - abilities.py
  - agent_loader.py
  - memory.py
  - agent.yaml
  - .env

#### .env (example)
- OLLAMA_HOST=http://localhost:11434
- DB_HOST=127.0.0.1
- DB_PORT=3306
- DB_USER=magento
- DB_PASS=secret
- DB_NAME=magento_db

#### Quickstart commands
- Pull model in Ollama:
  - ollama pull qwen3:4b-instruct
- Run the agent:
  - python app.py --objective "Plan a nice travel in Bangkok" --agent agent.yaml

#### Example agent.yaml (Magento performance)
```
---
name: ecommerce_performance_agent
description: Specialized agent for Magento performance optimization
author: ReasonLoop
version: 1.0
abilities:
  - text-completion
  - web-search
  - web-scrape
  - mysql-schema
  - mysql-query
tags:
  - ecommerce
  - performance
  - magento
---

## REASONING FRAMEWORK
1. First gather baseline performance metrics from MySQL and server logs
2. Identify potential bottlenecks across these categories: database queries, caching, frontend assets, server configuration
3. For each potential issue, estimate impact using this formula: (frequency × severity × ease of fix)
4. Prioritize optimizations that will provide the greatest performance improvement with minimal risk

## DECISION CRITERIA
When recommending changes, evaluate each option against these weighted factors:
- Performance impact: 40%
- Implementation complexity: 30%
- Stability risk: 30%

## REQUIRED OUTPUT
Your final recommendations must include:
1. Specific, actionable changes with implementation steps
2. Expected performance improvement (quantified where possible)
3. Risk assessment for each change
4. Verification method to confirm improvement
```

#### Use cases

- Magento performance assessment (MySQL + reasoning)
  - Objective: "Identify slow queries in checkout and propose fixes"
  - Flow:
    - mysql-schema: introspect key tables (sales, quote, inventory)
    - mysql-query: run EXPLAIN on known heavy queries
    - web-search: gather known Magento 2.4.7 tuning tips
    - text-completion: synthesize prioritized recommendations
  - Command:
    - python app.py --objective "Identify slow queries in checkout and propose fixes" --agent agent.yaml

- Cache/cdn validation
  - Objective: "Assess cache hit ratio problems and propose Nginx/Redis tuning"
  - Flow:
    - mysql-query: read cache-related metrics if stored; or plan inspection steps
    - web-search: pull best-practices for Magento FPC + Redis
    - text-completion: output concrete Nginx/Redis config adjustments with impact/risk
  - Command:
    - python app.py --objective "Assess cache hit ratio problems and propose Nginx/Redis tuning" --agent agent.yaml

- Frontend asset optimization
  - Objective: "Reduce TTFB and payload for homepage"
  - Flow:
    - web-scrape: fetch homepage HTML (internal URL)
    - text-completion: identify heavy assets, bundling/minification opportunities, HTTP/2 hints
    - web-search: cross-check with Magento frontend guidelines
  - Command:
    - python app.py --objective "Reduce TTFB and payload for homepage" --agent agent.yaml

- Incident postmortem summarization
  - Objective: "Summarize last incident with DB overload and propose guardrails"
  - Flow:
    - mysql-query: fetch slow log/metrics snapshots
    - text-completion: timeline + root cause + mitigations
  - Command:
    - python app.py --objective "Summarize last incident with DB overload and propose guardrails" --agent agent.yaml

#### Memory (optional, prepared)
- Table: agent_memories (good/bad results for later recall).
- First-time schema:
  - In code: call ensure_schema() from memory.py before run.
- Save result (later):
  - save_memory(agent_name, objective, tags, input_text, output_text, label="good"|"bad")

#### Notes
- Async-first; simple concurrency limiting (no retries, fail fast).
- Plain SQL only; if DB not reachable during mysql-* ability, app exits with error.
- Tags are metadata for later routing/analytics; not used in execution flow yet.
