import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import Config
from Utils.sqlManager import SQLManager

def create_table():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    
    sql = """
    CREATE TABLE IF NOT EXISTS player_activity_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        player_tag VARCHAR(15),
        activity_type VARCHAR(20), -- 'donation', 'attack', 'login_seen'
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (player_tag) REFERENCES players(player_tag) ON DELETE CASCADE
    );
    """
    
    try:
        db.execute(sql)
        print("✅ Successfully created player_activity_log table.")
    except Exception as e:
        print(f"❌ Failed to create table: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_table()
