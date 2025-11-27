import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import Config
from Utils.sqlManager import SQLManager

def update_schema():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    
    sql = """
    ALTER TABLE player_activity_log ADD COLUMN value INT DEFAULT 0;
    """
    
    try:
        db.execute(sql)
        print("✅ Successfully added 'value' column to player_activity_log.")
    except Exception as e:
        print(f"❌ Failed to update table: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    update_schema()
