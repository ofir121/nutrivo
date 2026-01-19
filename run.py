import subprocess
import time
import sys
import os
import logging

# Setup basic logging for run.py
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

def run():
    logger.info("🚀 Starting Meal Planner Application...")
    
    # 1. Start Backend
    logger.info("➡️  Starting Backend API (Uvicorn)...")
    backend = subprocess.Popen(
        ["uvicorn", "app.main:app", "--reload", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait a moment for backend to potentially start (optional)
    time.sleep(2)
    
    # 2. Start Frontend
    logger.info("➡️  Starting Frontend UI (Streamlit)...")
    frontend = subprocess.Popen(
        ["streamlit", "run", "app/frontend.py", "--server.port", "8501"],
        stdout=sys.stdout,
        stderr=sys.stderr
    )

    logger.info("✅ Application works! Access it here:")
    logger.info("   👉 UI:  http://localhost:8501")
    logger.info("   👉 API: http://localhost:8000")
    logger.info("Press Ctrl+C to stop everything.")

    try:
        # Keep main script running while subprocesses are alive
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        logger.info("🛑 Stopping application...")
        backend.terminate()
        frontend.terminate()
        logger.info("Done.")

if __name__ == "__main__":
    run()
