import pymysql
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config

def apply_migration():
    print("🔄 Applying Database Migration for Discord Bot...")
    
    connection = pymysql.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        autocommit=True
    )
    
    try:
        with connection.cursor() as cursor:
            # Add role column
            try:
                cursor.execute("ALTER TABLE players ADD COLUMN role VARCHAR(50) DEFAULT 'Member'")
                print("✅ Added 'role' column to players table.")
            except pymysql.MySQLError as e:
                if e.args[0] == 1060: # Duplicate column name
                    print("⚠️ 'role' column already exists.")
                else:
                    print(f"❌ Error adding 'role' column: {e}")

            # Add discord_id column
            try:
                cursor.execute("ALTER TABLE players ADD COLUMN discord_id VARCHAR(50) DEFAULT NULL")
                print("✅ Added 'discord_id' column to players table.")
            except pymysql.MySQLError as e:
                if e.args[0] == 1060:
                    print("⚠️ 'discord_id' column already exists.")
                else:
                    print(f"❌ Error adding 'discord_id' column: {e}")
                    
    finally:
        connection.close()
        print("✅ Migration Complete.")

if __name__ == "__main__":
    apply_migration()
