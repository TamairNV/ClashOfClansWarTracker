import subprocess
import time
import socket
import threading
from waitress import serve
from app import app  # Make sure this script is in the same folder as app.py

import sys
# --- 1. Your Flask Server Setup ---
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


def run_flask():
    """This function starts the web server."""
    local_ip = get_ip()
    print(f"🚀 Server Starting...")
    print(f"   - Local Access: http://localhost:5001")
    print(f"   - LAN Access:   http://{local_ip}:5001")
    print(f"   - Threads:      6")

    # This line blocks forever, so we run this function in a thread
    serve(app, host='0.0.0.0', port=5001, threads=6, url_scheme='https')


# --- 2. Your Scheduler Setup ---
scripts_config = {
    'Utils/war_tracker.py': 10,  # Minutes
    'Utils/activityChecker.py': 5,  # Minutes
    'Utils/performance_tracker.py' :720
}

last_run_times = {script: 0 for script in scripts_config}


def run_script(script_path):
    try:
        print(f"--- Running {script_path} ---")
        subprocess.run([sys.executable, script_path], check=True)
        print(f"Finished {script_path}")
    except Exception as e:
        print(f"Error running {script_path}: {e}")


# --- 3. Execution ---
if __name__ == "__main__":

    # Start Flask in a separate thread
    # daemon=True means this thread will die when you quit the main script
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    print("--- Scheduler Started (Flask running in background) ---")

    # Start the scheduler loop
    while True:
        current_time = time.time()

        for script, interval_mins in scripts_config.items():
            interval_seconds = interval_mins * 60

            if current_time - last_run_times[script] >= interval_seconds:
                run_script(script)
                last_run_times[script] = current_time

        time.sleep(1)