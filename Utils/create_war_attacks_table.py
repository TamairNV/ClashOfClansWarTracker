import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from sqlManager import SQLManager

def update_schema():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    
    print("🚀 Re-creating war_attacks table with new columns...")
    
    # Drop first to ensure schema update (since it's a new feature, data loss is acceptable)
    db.execute("DROP TABLE IF EXISTS war_attacks")
    
    sql = """
    CREATE TABLE war_attacks (
        attack_id INT AUTO_INCREMENT PRIMARY KEY,
        war_id INT NOT NULL,
        player_tag VARCHAR(15) NOT NULL,
        stars INT DEFAULT 0,
        destruction FLOAT DEFAULT 0.0,
        duration INT DEFAULT 0, -- Attack duration in seconds
        army_composition JSON, -- JSON string of troops/spells used
        attack_order INT DEFAULT 1,
        defender_tag VARCHAR(15),
        defender_th INT,
        
        FOREIGN KEY (war_id) REFERENCES wars(war_id) ON DELETE CASCADE,
        FOREIGN KEY (player_tag) REFERENCES players(player_tag) ON DELETE CASCADE
    );
    """
    
    try:
        db.execute(sql)
        db.connection.commit()
        print("✅ Successfully created war_attacks table.")
    except Exception as e:
        print(f"❌ Error creating table: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    update_schema()
