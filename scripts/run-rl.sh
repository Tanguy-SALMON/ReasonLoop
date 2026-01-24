#!/bin/bash
# =============================================================================
# ReasonLoop API Server Startup Script
# =============================================================================
# Starts the ReasonLoop Intelligence Service on port 8001
#
# Usage:
#   ./scripts/run-rl.sh          # Start with default settings
#   ./scripts/run-rl.sh --reload # Start with auto-reload for development
#
# Environment Variables:
#   API_PORT             - Port to listen on (default: 8001)
#   API_HOST             - Host to bind to (default: 0.0.0.0)
#   INTERNAL_SERVICE_SECRET - Secret key for inter-service auth
#   API_DEBUG            - Enable debug mode (default: false)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Default configuration
export API_PORT="${API_PORT:-8001}"
export API_HOST="${API_HOST:-0.0.0.0}"
export API_DEBUG="${API_DEBUG:-false}"

# Generate a default secret if not set (for development only!)
if [ -z "$INTERNAL_SERVICE_SECRET" ]; then
    export INTERNAL_SERVICE_SECRET="dev-secret-$(date +%s | sha256sum | head -c 16)"
    echo "⚠️  WARNING: Using auto-generated INTERNAL_SERVICE_SECRET"
    echo "   Set INTERNAL_SERVICE_SECRET in production!"
    echo "   Secret: $INTERNAL_SERVICE_SECRET"
fi

echo "=============================================="
echo "  ReasonLoop Intelligence Service"
echo "=============================================="
echo "  Host:   $API_HOST"
echo "  Port:   $API_PORT"
echo "  Debug:  $API_DEBUG"
echo "  Secret: ${INTERNAL_SERVICE_SECRET:0:8}..."
echo "=============================================="
echo ""

# Check for reload flag
RELOAD_FLAG=""
if [ "$1" == "--reload" ] || [ "$API_DEBUG" == "true" ]; then
    RELOAD_FLAG="--reload"
    echo "🔄 Hot reload enabled"
fi

# Start the server
echo "🚀 Starting ReasonLoop on http://$API_HOST:$API_PORT"
echo "📚 API Docs: http://localhost:$API_PORT/docs"
echo ""

poetry run uvicorn api.main:app \
    --host "$API_HOST" \
    --port "$API_PORT" \
    $RELOAD_FLAG
