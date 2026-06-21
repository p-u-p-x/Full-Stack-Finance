#!/bin/bash
set -e

# Start FastAPI in background
cd /app/backend
uvicorn main:app --host 0.0.0.0 --port 8000 &

# Start Streamlit (foreground)
cd /app/frontend
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
