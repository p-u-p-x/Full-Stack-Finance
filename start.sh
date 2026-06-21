#!/bin/bash
set -e

echo "=== Starting Full Stack Finance ==="

# ── 1. Start FastAPI backend in the background
echo "[1/2] Starting FastAPI backend on port 8000..."
cd /app/backend
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# ── 2. Wait until the backend is actually answering HTTP requests
echo "Waiting for backend to become healthy..."
for i in {1..60}; do
    if curl -sf http://localhost:8000/ > /dev/null 2>&1; then
        echo "Backend is ready!"
        break
    fi
    sleep 2
done

# ── 3. Start Streamlit in the foreground (keeps the container alive)
echo "[2/2] Starting Streamlit frontend on port 8501..."
cd /app/frontend
exec streamlit run app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false
