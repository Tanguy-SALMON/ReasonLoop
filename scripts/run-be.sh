#!/bin/bash
# =============================================================================
# BE-Campaign Mock Server Startup Script
# =============================================================================
# Starts a mock be-campaign server for integration testing on port 8000
#
# Usage:
#   ./scripts/run-be.sh          # Start mock be-campaign
#   ./scripts/run-be.sh --reload # Start with auto-reload
#
# Environment Variables:
#   BE_PORT              - Port to listen on (default: 8000)
#   REASONLOOP_URL       - ReasonLoop service URL (default: http://localhost:8001)
#   INTERNAL_SERVICE_SECRET - Secret key for inter-service auth
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Default configuration
export BE_PORT="${BE_PORT:-8000}"
export REASONLOOP_URL="${REASONLOOP_URL:-http://localhost:8001}"

# Check for secret
if [ -z "$INTERNAL_SERVICE_SECRET" ]; then
    echo "⚠️  WARNING: INTERNAL_SERVICE_SECRET not set"
    echo "   Requests to ReasonLoop will fail!"
    echo "   Set the same secret as used by run-rl.sh"
fi

echo "=============================================="
echo "  BE-Campaign Mock Server"
echo "=============================================="
echo "  Port:         $BE_PORT"
echo "  ReasonLoop:   $REASONLOOP_URL"
echo "  Secret Set:   $([ -n "$INTERNAL_SERVICE_SECRET" ] && echo "Yes" || echo "No")"
echo "=============================================="
echo ""

# Check for reload flag
RELOAD_FLAG=""
if [ "$1" == "--reload" ]; then
    RELOAD_FLAG="--reload"
    echo "🔄 Hot reload enabled"
fi

# Create a minimal FastAPI app for testing
python3 << 'PYEOF'
import sys
import os
sys.path.insert(0, os.getcwd())

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import the integration module
from integrations.be_campaign.api.routers.customers import router as customers_router

app = FastAPI(
    title="BE-Campaign Mock Server",
    version="1.0.0",
    description="Mock server for testing ReasonLoop integration",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include customer router
app.include_router(customers_router, prefix="/api/v1/customers")

@app.get("/")
async def root():
    return {
        "name": "BE-Campaign Mock Server",
        "version": "1.0.0",
        "docs": "/docs",
        "customers": "/api/v1/customers",
        "reasonloop": os.getenv("REASONLOOP_URL", "http://localhost:8001"),
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "be-campaign-mock"}

if __name__ == "__main__":
    port = int(os.getenv("BE_PORT", "8000"))
    reload = "--reload" in sys.argv
    
    print(f"🚀 Starting BE-Campaign on http://0.0.0.0:{port}")
    print(f"📚 API Docs: http://localhost:{port}/docs")
    
    uvicorn.run(
        "run_be_server:app" if reload else app,
        host="0.0.0.0",
        port=port,
        reload=reload,
    )
PYEOF
