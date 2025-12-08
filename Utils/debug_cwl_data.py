
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from Utils.sqlManager import SQLManager
import json

def debug_cwl():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    print("🔌 Connecting to database...")
    
    # Get last 20 ended wars
    sql = """
        SELECT w.war_id, w.opponent_name, w.result, w.state, w.start_time
        FROM wars w
        WHERE w.state = 'warEnded'
        ORDER BY w.start_time DESC
        LIMIT 20
    """
    wars = db.fetch_all(sql)
    print(f"Stats for last {len(wars)} wars:\n")
    print(f"{'Date':<12} | {'Opponent':<15} | {'Result':<6} | {'Our ★':<6} | {'Enemy ★':<6} | {'Our %':<6} | {'Enemy %':<6}")
    print("-" * 80)
    
    for war in wars:
        wid = war['war_id']
        
        # Our stats
        our = db.fetch_one("SELECT SUM(stars) as stars, AVG(destruction_percentage) as dest FROM war_performance WHERE war_id=%s", (wid,))
        our_stars = our['stars'] or 0
        our_dest = our['dest'] or 0
        
        # Enemy stats
        enemy = db.fetch_one("SELECT SUM(stars) as stars, AVG(destruction) as dest FROM war_opponents WHERE war_id=%s", (wid,))
        enemy_stars = enemy['stars'] or 0
        enemy_dest = enemy['dest'] or 0
        
        print(f"{war['start_time'].strftime('%m-%d'):<12} | {war['opponent_name'][:15]:<15} | {war['result'] or 'N/A':<6} | {our_stars:<6} | {enemy_stars:<6} | {our_dest:<6.1f} | {enemy_dest:<6.1f}")

    db.close()

if __name__ == "__main__":
    debug_cwl()
