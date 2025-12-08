
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from Utils.sqlManager import SQLManager

def update_schema():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    print("🔌 Connecting to database...")
    
    try:
        # Check if column exists
        check_sql = """
            SELECT count(*) as cnt 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'wars' 
            AND COLUMN_NAME = 'result'
        """
        exists = db.fetch_one(check_sql, (Config.DB_NAME,))
        
        if exists['cnt'] == 0:
            print("🚀 Adding 'result' column to 'wars' table...")
            sql = "ALTER TABLE wars ADD COLUMN result VARCHAR(10) DEFAULT NULL"
            db.execute(sql)
            print("✅ Column added successfully.")
            
            # Optional: Try to populate it? 
            # For now let's just default to NULL to fix the crash.
            # Ideally we would calculate it from war_performance vs war_opponents summaries, 
            # but getting the site back up is priority.
        else:
            print("ℹ️ Column 'result' already exists.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    update_schema()
