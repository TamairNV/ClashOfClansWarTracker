
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from Utils.sqlManager import SQLManager
from collections import Counter

def analyze_donations():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    print("🔌 Connecting to database...")
    
    try:
        # Fetch all donation timestamp hours
        # We assume activity_type = 'donation'
        sql = "SELECT HOUR(timestamp) as h, COUNT(*) as c FROM player_activity_log WHERE activity_type = 'donation' GROUP BY h ORDER BY c DESC"
        results = db.fetch_all(sql)
        
        print("\n📊 Donation Activity by UTC Hour:")
        print(f"{'Hour (UTC)':<12} | {'Donations':<10}")
        print("-" * 25)
        
        total_donations = sum(r['c'] for r in results)
        
        for row in results:
            hour = row['h']
            count = row['c']
            bar = "█" * int((count / results[0]['c']) * 20)
            print(f"{hour:02d}:00       | {count:<4} {bar}")
            
        # Find the 4-hour window with max donations
        # Convert to list of (hour, count) tuples, filling missing hours with 0
        hour_counts = {r['h']: r['c'] for r in results}
        
        best_window_start = 0
        max_window_count = 0
        
        for start_h in range(24):
            current_window_count = 0
            for i in range(4): # 4 hour window
                h = (start_h + i) % 24
                current_window_count += hour_counts.get(h, 0)
            
            if current_window_count > max_window_count:
                max_window_count = current_window_count
                best_window_start = start_h
        
        end_h = (best_window_start + 4) % 24
        print(f"\n🔥 Best 4-Hour Window: {best_window_start:02d}:00 - {end_h:02d}:00 UTC")
        print(f"   ({max_window_count} donations recorded in this period)")
        
    finally:
        db.close()

if __name__ == "__main__":
    analyze_donations()
