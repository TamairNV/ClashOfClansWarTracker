import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from sqlManager import SQLManager

def check_bad_results():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    
    print("--- 🔍 Checking Data Types ---")
    rows = db.fetch_all("SELECT war_id, start_time, result FROM wars WHERE state='warEnded' LIMIT 1")
    if rows:
        print(f"Row: {rows[0]}")
        print(f"Type of start_time: {type(rows[0]['start_time'])}")
        print(f"Type of result: {type(rows[0]['result'])}")

    db.close()

if __name__ == "__main__":
    check_bad_results()
