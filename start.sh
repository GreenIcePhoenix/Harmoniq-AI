#!/bin/bash
cd ~/harmoniq-ai-nm
source .venv/bin/activate

echo "🚀 Starting Harmoniq AI..."
echo ""

# Kill anything on ports 8000 and 8080
fuser -k 8000/tcp 2>/dev/null
fuser -k 8080/tcp 2>/dev/null

# Serve custom UI on 8080 in background
python3 -m http.server 8080 --directory ~/harmoniq-ui &
UI_PID=$!
echo "✅ Custom UI running on port 8080 (PID: $UI_PID)"

# Start ADK with CORS fix on 8000
echo "✅ ADK API starting on port 8000..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌟 HARMONIQ AI LINKS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Custom UI  → Web Preview port 8080"
echo "  ADK Dev UI → Web Preview port 8000"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

adk web . \
  --host 0.0.0.0 \
  --port 8000 \
  --allow_origins "regex:https://.*\.cloudshell\.dev"

# Cleanup on exit
kill $UI_PID 2>/dev/null
