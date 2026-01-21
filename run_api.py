#!/usr/bin/env python3
"""
ReasonLoop Campaign API Server

Usage:
    python run_api.py

    # With custom host/port
    API_HOST=127.0.0.1 API_PORT=3000 python run_api.py

    # Debug mode (auto-reload)
    API_DEBUG=true python run_api.py

    # Or use uvicorn directly
    uvicorn api.main:app --reload --port 8000
"""

import os
import sys
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
from dotenv import load_dotenv

load_dotenv()


def main():
    """Start the API server"""
    import uvicorn
    from api.core.config import get_config

    config = get_config()

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║             ReasonLoop Campaign API                          ║
╠══════════════════════════════════════════════════════════════╣
║  Host:     {config.host:<48} ║
║  Port:     {config.port:<48} ║
║  Debug:    {str(config.debug):<48} ║
║  Docs:     http://{config.host}:{config.port}/docs{" ":<27} ║
║  Debug:    {str(config.debug):<48} ║
║  Docs:     http://{config.host}:{config.port}/docs{' ':<27} ║
╚══════════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "api.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level="info" if not config.debug else "debug",
    )


if __name__ == "__main__":
    main()
