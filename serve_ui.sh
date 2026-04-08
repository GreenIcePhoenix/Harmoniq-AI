#!/bin/bash
# Serves the Harmoniq UI alongside the ADK backend
cd ~/harmoniq-ai-nm

# Start ADK API server (not web UI) on port 8000
source .venv/bin/activate
adk api_server . --port 8000 &
ADK_PID=$!

echo "✅ ADK API server running (PID: $ADK_PID)"
echo "✅ Open UI via Web Preview on port 8080"

# Serve the UI on port 8080
python3 -m http.server 8080 --directory ui/

# Cleanup
kill $ADK_PID
