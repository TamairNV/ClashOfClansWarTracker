
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from Utils.sqlManager import SQLManager

def inspect_wars():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    print("--- Last 5 Wars in DB ---")
    wars = db.fetch_all("SELECT war_id, opponent_name, state, result, end_time, war_type FROM wars ORDER BY end_time DESC LIMIT 5")
    for w in wars:
        print(w)
    db.close()

if __name__ == "__main__":
    inspect_wars()
