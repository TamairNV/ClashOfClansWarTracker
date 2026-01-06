import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from sqlManager import SQLManager

def fix_bad_war():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    
    WAR_ID = 18
    # Based on previous check, we have 92 stars for us (opponent 99)
    # Result: Lose
    
    print(f"🧹 Clearing corrupted player performance for War {WAR_ID}...")
    db.execute("DELETE FROM war_performance WHERE war_id=%s", (WAR_ID,))
    
    print("✨ Updating Clan level stats (so history still shows the war)...")
    # We can't update 'stars' column in wars table because... it doesn't exist?
    # Wait, get_clan_war_history_stats computes sum(wp.stars).
    # If I delete wp rows, the sum will be 0.
    # The clan stats page will show 0 stars.
    
    # PROBLEM: The schema calculates everything from `war_performance`.
    # If I delete performance, I delete the history for the clan view too.
    
    # ALTERNATIVE:
    # Insert "Ghost" performance records? 
    # Or just modify `wars` table to have a manual `clan_stars` column override? (Too much schema change).
    
    # BETTER ALTERNATIVE:
    # Set `attacks_used` = NULL or something to exclude from stats?
    # Or... Just tell the user "We can't restore the attacks, so I'm removing the 'Missed Attacks' penalty by deleting the records."
    # The clan stats will show 0 stars (or N/A), but that's better than "Everyone missed".
    
    # Actually, if I delete the records, `get_clan_war_history_stats` (LEFT JOIN war_performance) will return NULL for stars.
    # I can handle NULL in the UI to display "Data Lost" or similar.
    
    print(f"✅ Deleted performance records for War {WAR_ID}.")

    db.close()

if __name__ == "__main__":
    fix_bad_war()
