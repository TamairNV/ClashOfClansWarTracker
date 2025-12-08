
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from Utils.sqlManager import SQLManager

def backfill_results():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    print("🔌 Connecting to database...")
    
    try:
        # Fetch all ended wars with missing results
        sql = "SELECT war_id, opponent_name FROM wars WHERE state = 'warEnded' AND (result IS NULL OR result = '')"
        wars = db.fetch_all(sql)
        print(f"found {len(wars)} wars to update...")

        for war in wars:
            wid = war['war_id']
            
            # Get Our Stats
            our_stats = db.fetch_one("""
                SELECT SUM(stars) as stars, AVG(destruction_percentage) as dest 
                FROM war_performance WHERE war_id = %s
            """, (wid,))
            
            # Get Enemy Stats
            enemy_stats = db.fetch_one("""
                SELECT SUM(stars) as stars, AVG(destruction) as dest 
                FROM war_opponents WHERE war_id = %s
            """, (wid,))
            
            our_stars = our_stats['stars'] or 0
            our_dest = our_stats['dest'] or 0
            
            # Use raw sum for destruction comparison if averages are surprisingly close, but averages should work
            # Actually, total destruction is safer.
            our_total_dest = our_dest * (db.fetch_one("SELECT COUNT(*) as c FROM war_performance WHERE war_id=%s", (wid,))['c'] or 1) # Rough approx if needed, but let's stick to stars first.
            
            # Correction: war_opponents destruction is per base. 
            # Total destruction is usually what decides tiebreakers (total percentage points)
            # but avg is proportionally same if map size is same.
            
            enemy_stars = enemy_stats['stars'] or 0
            enemy_dest = enemy_stats['dest'] or 0
            
            result = 'draw'
            if our_stars > enemy_stars:
                result = 'win'
            elif our_stars < enemy_stars:
                result = 'lose'
            else:
                # Tie on stars, check destruction
                if our_dest > enemy_dest:
                    result = 'win'
                elif our_dest < enemy_dest:
                    result = 'lose'
                else:
                    result = 'draw'
            
            print(f"Update War {wid} vs {war['opponent_name']}: {our_stars}-{enemy_stars} => {result}")
            
            # Update DB
            db.execute("UPDATE wars SET result = %s WHERE war_id = %s", (result, wid))
            
        print("✅ Backfill complete.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    backfill_results()
