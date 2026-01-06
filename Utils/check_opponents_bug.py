import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from sqlManager import SQLManager

def check_opponents():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    
    # Check if all opponents in a specific war have the exact same stats (sign of the bug)
    # Get a recent war
    war = db.fetch_one("SELECT war_id FROM wars WHERE state='warEnded' ORDER BY start_time DESC LIMIT 1")
    if not war:
        print("No ended wars found.")
        return

    war_id = war['war_id']
    print(f"Checking War ID: {war_id}")
    
    opponents = db.fetch_all("SELECT * FROM war_opponents WHERE war_id = %s", (war_id,))
    
    first = opponents[0]
    is_suspicious = True
    for op in opponents:
        print(f"Tag: {op['opponent_tag']} | Stars: {op['stars']} | Dest: {op['destruction']}")
        if op['stars'] != first['stars'] or op['destruction'] != first['destruction']:
            is_suspicious = False
            
    if is_suspicious:
        print("\n⚠️  ALL OPPONENTS HAVE IDENTICAL STATS! The bug is confirmed.")
    else:
        print("\n✅ Opponents have varying stats. Data might be okay (or distinctively wrong).")

    db.close()

if __name__ == "__main__":
    check_opponents()
