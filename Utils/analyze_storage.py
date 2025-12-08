import pymysql
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config

def get_size():
    conn = pymysql.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )
    
    with conn.cursor() as cursor:
        # 1. Total Database Size
        cursor.execute("""
            SELECT 
                ROUND(SUM(data_length + index_length) / 1024, 2) AS total_kb,
                ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS total_mb
            FROM information_schema.tables 
            WHERE table_schema = %s
        """, (Config.DB_NAME,))
        total_size = cursor.fetchone()
        
        # 2. Row Counts
        cursor.execute("SELECT COUNT(*) as count FROM wars")
        war_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM war_attacks")
        attack_count = cursor.fetchone()['count']
        
        # 3. Estimate per War
        # A war consists of 1 War Row + ~50 Performance Rows + ~100 Attack Rows + ~50 Opponent Rows
        # Let's approximate by dividing total size by war count (rough estimate)
        if war_count > 0:
            avg_per_war_kb = total_size['total_kb'] / war_count
        else:
            avg_per_war_kb = 0
            
        print(f"📊 Database Storage Report")
        print(f"--------------------------")
        print(f"Total Size:   {total_size['total_kb']} KB  ({total_size['total_mb']} MB)")
        print(f"Total Wars:   {war_count}")
        print(f"Total Attacks:{attack_count}")
        print(f"--------------------------")
        print(f"Est. Size per War: ~{avg_per_war_kb:.2f} KB")
        print(f"(Includes roster snapshots, attacks, and metadata)")

if __name__ == "__main__":
    get_size()
