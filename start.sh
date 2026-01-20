#!/usr/bin/env bash
set -euo pipefail

uvicorn app.main:app --host 0.0.0.0 --port 8000 &
backend_pid=$!

streamlit run app/frontend.py --server.port "${PORT:-8501}" --server.address 0.0.0.0 &
frontend_pid=$!

trap 'kill -TERM "$backend_pid" "$frontend_pid" 2>/dev/null' SIGTERM SIGINT

wait -n "$backend_pid" "$frontend_pid"
