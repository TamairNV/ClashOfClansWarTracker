import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from sqlManager import SQLManager

def main():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    
    # Get all players
    players = db.get_all_active_players()
    
    print(f"🔍 Analyzing {len(players)} players...")
    
    for p in players:
        tag = p['player_tag']
        name = p['name']
        
        # Get Stats
        stats = db.get_player_war_stats(tag)
        if not stats: continue
        
        total = stats['total_attacks']
        missed = stats['missed_attacks']
        
        # We are looking for the "11/12" case
        if total and total >= 10:
            print(f"\n👤 {name} ({tag})")
            print(f"   Stats: {total}/{total + missed} (Missed: {missed})")
            
            # Drill down into wars
            sql = """
                SELECT w.war_id, w.opponent_name, w.war_type, wp.attacks_used, w.start_time
                FROM war_performance wp
                JOIN wars w ON wp.war_id = w.war_id
                WHERE wp.player_tag = %s AND w.state = 'warEnded'
                ORDER BY w.start_time DESC
            """
            wars = db.fetch_all(sql, (tag,))
            
            for w in wars:
                w_type = w['war_type']
                used = w['attacks_used']
                
                # Replicate Logic
                is_cwl = w_type and w_type.lower() == 'cwl'
                expected = 1 if is_cwl else 2
                is_missed = expected - used
                
                status = "✅" if is_missed <= 0 else f"❌ Missed {is_missed}"
                print(f"   - {w['start_time']} vs {w['opponent_name']} | Type: {w_type} | Attacks: {used}/{expected} | {status}")

    db.close()

if __name__ == "__main__":
    main()
