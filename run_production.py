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

def wait_for_internet():
    """Blocks execution until internet is available."""
    print("🌐 Checking for internet connection...")
    while True:
        try:
            # Try to connect to Google DNS
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            print("✅ Internet Connection Established.")
            break
        except OSError:
            print("⚠️ No Internet. Retrying in 5s...")
            time.sleep(5)


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
    'Utils/performance_tracker.py' :720,
    'Utils/capital_tracker.py': 60, # Hourly check for Raid Weekend
    'Utils/player_deep_tracker.py': 720 # 12 Hours (Deep stats, Achievements)
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
    """Runs the Discord Bot with auto-restart."""
    print("🤖 Discord Bot Starting...")
    while True:
        try:
            # We run the bot script as a subprocess to keep environments clean
            subprocess.run([sys.executable, "discord_bot/main.py"], check=True)
        except Exception as e:
            print(f"❌ Discord Bot Crashed: {e}")
            print("🔄 Restarting Bot in 10 seconds...")
            time.sleep(10)

if __name__ == "__main__":
    
    # Block until internet is up
    wait_for_internet()

    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Start Discord Bot in a separate thread (since it has its own loop)
    # Note: discord.py blocks, so we put it in a thread.
    bot_thread = threading.Thread(target=run_discord_bot, daemon=True)
    bot_thread.start()

    print("--- Scheduler Started (Flask & Discord Bot running in background) ---")
    print("✅ 24/7 Monitoring Active")

    # Start the scheduler loop
    while True:
        current_time = time.time()

        for script, interval_mins in scripts_config.items():
            interval_seconds = interval_mins * 60

            if current_time - last_run_times[script] >= interval_seconds:
                run_script(script)
                last_run_times[script] = current_time

        time.sleep(1)