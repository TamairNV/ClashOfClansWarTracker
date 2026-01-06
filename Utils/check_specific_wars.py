import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from sqlManager import SQLManager

def check_wars():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    
    print("--- 🔍 Checking Wars 25+ ---")
    rows = db.fetch_all("SELECT war_id, opponent_name, war_type, opponent_tag, state, result FROM wars WHERE war_id >= 25")
    for row in rows:
        print(f"ID: {row['war_id']} | Type: {row['war_type']} | Opponent: {row['opponent_name']} | Tag: {row['opponent_tag']} | State: {row['state']} | Result: {row['result']}")

    db.close()

if __name__ == "__main__":
    check_wars()
