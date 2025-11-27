import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from sqlManager import SQLManager

def update_schema():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    
    print("🚀 Creating war_attacks table...")
    
    sql = """
    CREATE TABLE IF NOT EXISTS war_attacks (
        attack_id INT AUTO_INCREMENT PRIMARY KEY,
        war_id INT NOT NULL,
        player_tag VARCHAR(15) NOT NULL,
        stars INT DEFAULT 0,
        destruction FLOAT DEFAULT 0.0,
        attack_order INT DEFAULT 1, -- 1 for first attack, 2 for second
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
