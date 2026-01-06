import pymysql
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config

def export_schema():
    conn = pymysql.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )
    
    output_file = "schema.sql"
    
    with conn.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        tables = [list(row.values())[0] for row in cursor.fetchall()]
        
        with open(output_file, "w") as f:
            f.write(f"-- Clash of Clans War Tracker Schema Export\n")
            f.write(f"-- Database: {Config.DB_NAME}\n\n")
            
            for table in tables:
                cursor.execute(f"SHOW CREATE TABLE {table}")
                result = cursor.fetchone()
                # 'Create Table' column holds the SQL
                create_sql = result['Create Table']
                
                f.write(f"-- Table structure for table `{table}`\n")
                f.write(f"DROP TABLE IF EXISTS `{table}`;\n")
                f.write(f"{create_sql};\n\n")
                
    print(f"✅ Schema exported to {output_file}")
    conn.close()

if __name__ == "__main__":
    export_schema()
