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

    # 4. Add 'hero_equipment' to war_attacks
    try:
        db.execute("ALTER TABLE war_attacks ADD COLUMN hero_equipment JSON")
        print("✅ Added 'hero_equipment' column to war_attacks.")
    except pymysql.MySQLError as e:
        if "Duplicate column name" in str(e):
            print("🔹 'hero_equipment' column already exists.")
        else:
            print(f"⚠️ Error adding 'hero_equipment': {e}")

    # 5. Create 'war_defenses' table (Tracks attacks AGAINST us)
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS war_defenses (
                defense_id INT AUTO_INCREMENT PRIMARY KEY,
                war_id INT,
                defender_tag VARCHAR(20),
                attacker_tag VARCHAR(20),
                attacker_name VARCHAR(50),
                stars INT,
                destruction_percentage FLOAT,
                duration_seconds INT,
                attack_order INT,
                army_composition JSON,
                hero_equipment JSON,
                UNIQUE KEY unique_defense (war_id, defender_tag, attack_order),
                FOREIGN KEY (war_id) REFERENCES wars(war_id) ON DELETE CASCADE
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
        """)
        print("✅ Verified/Created 'war_defenses' table.")
    except Exception as e:
        print(f"❌ Failed to create war_defenses table: {e}")
    # 6. Add 'builder_base_trophies' to players
    try:
        db.execute("ALTER TABLE players ADD COLUMN builder_base_trophies INT DEFAULT 0")
        print("✅ Added 'builder_base_trophies' column to players.")
    except pymysql.MySQLError as e:
        if "Duplicate column name" in str(e):
            print("🔹 'builder_base_trophies' column already exists.")
        else:
            print(f"⚠️ Error adding 'builder_base_trophies': {e}")

    # 7. Create 'raid_weekends' table
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS raid_weekends (
                raid_id VARCHAR(20) PRIMARY KEY, -- using start_time string or specialized ID
                state VARCHAR(20),
                start_time DATETIME,
                end_time DATETIME,
                total_loot INT,
                total_attacks INT,
                districts_destroyed INT,
                medals_earned INT
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
        """)
        print("✅ Verified/Created 'raid_weekends' table.")
    except Exception as e:
        print(f"❌ Failed to create raid_weekends table: {e}")

    # 8. Create 'raid_members' table
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS raid_members (
                raid_id VARCHAR(20),
                player_tag VARCHAR(20),
                name VARCHAR(50),
                attacks_count INT,
                loot_looted INT,
                medals_bonus INT,
                PRIMARY KEY (raid_id, player_tag),
                FOREIGN KEY (raid_id) REFERENCES raid_weekends(raid_id) ON DELETE CASCADE
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
        """)
        print("✅ Verified/Created 'raid_members' table.")
    except Exception as e:
        print(f"❌ Failed to create raid_members table: {e}")

    # 9. Add 'achievements' to players
    try:
        db.execute("ALTER TABLE players ADD COLUMN achievements JSON")
        print("✅ Added 'achievements' column to players.")
    except pymysql.MySQLError as e:
        if "Duplicate column name" in str(e):
            print("🔹 'achievements' column already exists.")
        else:
            print(f"⚠️ Error adding 'achievements': {e}")
            
    finally:
        db.close()

if __name__ == "__main__":
    create_table()

