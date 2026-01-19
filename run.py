import subprocess
import time
import sys
import os

def run():
    print("🚀 Starting Meal Planner Application...")
    
    # 1. Start Backend
    print("➡️  Starting Backend API (Uvicorn)...")
    backend = subprocess.Popen(
        ["uvicorn", "app.main:app", "--reload", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait a moment for backend to potentially start (optional)
    time.sleep(2)
    
    # 2. Start Frontend
    print("➡️  Starting Frontend UI (Streamlit)...")
    frontend = subprocess.Popen(
        ["streamlit", "run", "app/frontend.py", "--server.port", "8501"],
        stdout=sys.stdout,
        stderr=sys.stderr
    )

    print("\n✅ Application works! Access it here:")
    print("   👉 UI:  http://localhost:8501")
    print("   👉 API: http://localhost:8000")
    print("\nPress Ctrl+C to stop everything.")

    try:
        # Keep main script running while subprocesses are alive
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        print("\n🛑 Stopping application...")
        backend.terminate()
        frontend.terminate()
        print("Done.")

if __name__ == "__main__":
    run()
