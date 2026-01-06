import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from sqlManager import SQLManager

def verify():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    
    WAR_ID = 18
    print(f"--- 🔍 Verifying War {WAR_ID} Cleanup ---")
    
    # Check count in war_performance
    rows = db.fetch_all("SELECT * FROM war_performance WHERE war_id=%s", (WAR_ID,))
    print(f"Rows in war_performance: {len(rows)}")
    
    if len(rows) > 0:
        print("❌ Data STILL EXISTS! Deletion failed??")
        print(f"Sample: {rows[0]}")
    else:
        print("✅ war_performance is EMPTY for War 18. No missed attacks should be counted.")

    db.close()

if __name__ == "__main__":
    verify()
