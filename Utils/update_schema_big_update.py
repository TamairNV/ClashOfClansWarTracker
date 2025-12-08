
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from sqlManager import SQLManager

def update_schema():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    print("🔌 Connecting to database...")
    
    try:
        print("🛠️ Adding new columns for Big Update...")
        # Add columns if they don't exist
        sql = """
        ALTER TABLE players 
        ADD COLUMN IF NOT EXISTS favorite_time_label VARCHAR(50) DEFAULT NULL,
        ADD COLUMN IF NOT EXISTS activity_score FLOAT DEFAULT 0.0;
        """
        db.execute(sql)
        print("✅ Schema updated successfully!")
        
    except Exception as e:
        print(f"❌ Error updating schema: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    update_schema()
