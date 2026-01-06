import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from sqlManager import SQLManager

def inspect_war():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    
    # Find war roughly matching the date
    print("--- 🔍 Searching for War on 2025-12-18 ---")
    sql = "SELECT * FROM wars WHERE DATE(start_time) = '2025-12-18' OR DATE(end_time) = '2025-12-18'"
    wars = db.fetch_all(sql)
    
    if not wars:
        print("❌ No wars found on that date.")
        return

    for war in wars:
        print(f"ID: {war['war_id']} | Start: {war['start_time']} | End: {war['end_time']} | Opponent: {war['opponent_name']} | Result: {war['result']}")
        
        # Check performance stats
        stats = db.fetch_one("SELECT SUM(stars) as total_stars, SUM(attacks_used) as total_attacks FROM war_performance WHERE war_id=%s", (war['war_id'],))
        print(f"   Stats in DB: {stats['total_stars']} Stars | {stats['total_attacks']} Attacks")

    db.close()

if __name__ == "__main__":
    inspect_war()
