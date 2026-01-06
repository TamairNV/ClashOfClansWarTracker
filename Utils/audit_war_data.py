import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from sqlManager import SQLManager

def audit_wars():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    
    print("--- 🔍 War State Distribution ---")
    rows = db.fetch_all("SELECT state, COUNT(*) as count FROM wars GROUP BY state")
    for row in rows:
        print(f"State: {row['state']} | Count: {row['count']}")

    print("\n--- 🕵️‍♀️ Check for NULL/None in Key Columns ---")
    suspicious = db.fetch_all("""
        SELECT war_id, start_time, state, opponent_name, war_type, end_time 
        FROM wars 
        WHERE 
            state IS NULL OR state = 'None' OR state = 'NONE' OR
            opponent_name IS NULL OR opponent_name = 'None' OR
            war_type IS NULL OR war_type = 'None' OR
            (state = 'warEnded' AND end_time IS NULL)
    """)
    
    if not suspicious:
        print("✅ No suspicious NULL/None data found in wars table.")
    else:
        for war in suspicious:
            print(f"⚠️ Suspicious Data -> ID: {war['war_id']} | Opponent: {war.get('opponent_name')} | State: {war.get('state')} | Type: {war.get('war_type')} | End: {war.get('end_time')}")

    db.close()

if __name__ == "__main__":
    audit_wars()
