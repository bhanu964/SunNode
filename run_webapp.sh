#!/usr/bin/env bash
# run_webapp.sh — Launch SunNode DSS Web Application
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================================"
echo "⚡ Starting SunNode Decision Support System (DSS - Telangana)"
echo "======================================================================"

# 1. Verify or rebuild pre-bundled data
if [ ! -f "webapp/data/substations.json" ] || [ ! -f "webapp/data/districts_simplified.geojson" ]; then
    echo "📦 Bundling Stage 4.5 GIS & Techno-Economic Data Assets..."
    python3 webapp/build_webapp_data.py
fi

# 2. Check Python environment
PYTHON_CMD="python3"
if [ -f ".venv/bin/python3" ]; then
    PYTHON_CMD=".venv/bin/python3"
fi

# 3. Determine available port (default: 8000, fallback to 8001+)
PORT=$($PYTHON_CMD -c "
import socket
for p in range(8000, 8050):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('', p))
            print(p)
            break
        except OSError:
            continue
")

# 4. Launch browser in background after 1.2s
(
    sleep 1.2
    if which open > /dev/null; then
        open "http://localhost:${PORT}"
    elif which xdg-open > /dev/null; then
        xdg-open "http://localhost:${PORT}"
    fi
) &

# 5. Run HTTP server
echo "🚀 Web server listening on http://localhost:${PORT}"
exec $PYTHON_CMD webapp/server.py $PORT
