import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from sqlManager import SQLManager

def check_attacks():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    
    print("--- 🔍 Checking War Attacks for War 18 ---")
    rows = db.fetch_all("SELECT * FROM war_attacks WHERE war_id=18")
    
    if not rows:
        print("❌ No attacks found in war_attacks table either.")
    else:
        print(f"✅ Found {len(rows)} attacks! We can rebuild war_performance.")
        # Print a sample
        print(rows[0])

    db.close()

if __name__ == "__main__":
    check_attacks()
