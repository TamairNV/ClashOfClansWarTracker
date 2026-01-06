import asyncio
import os
import sys
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import coc
from config import Config
from sqlManager import SQLManager

WAR_ID_TO_FIX = 18
OPPONENT_NAME = "Clan games NO"

async def main():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    client = coc.Client()
    
    try:
        await client.login(Config.COC_EMAIL, Config.COC_PASSWORD)
        print(f"🚑 Attempting to repair War ID {WAR_ID_TO_FIX} vs {OPPONENT_NAME}...")
        
        war_log = await client.get_war_log(Config.CLAN_TAG)
        
        target_war = None
        for entry in war_log:
            if entry.opponent.name == OPPONENT_NAME:
                target_war = entry
                break
        
        if not target_war:
            print("❌ Could not find this war in the API War Log!")
            return

        print(f"✅ Found War! Result: {target_war.result} | Score: {target_war.clan.stars} - {target_war.opponent.stars}")
        
        # 1. Fix Wars Table
        result_str = str(target_war.result).lower()
        if result_str == 'tie': result_str = 'draw'
        
        db.execute("UPDATE wars SET result=%s, end_time=%s WHERE war_id=%s", 
                   (result_str, target_war.end_time.time, WAR_ID_TO_FIX))
        print("Updated wars table.")

        # 2. Fix War Performance (Players)
        print("Restoring player stats...")
        # Note: WarLog entry 'members' might be less detailed than 'get_war' but usually includes attacks.
        # Let's check if we have member data.
        if not target_war.clan.members:
             print("⚠️ No member data in war log entry. Cannot restore player stats!")
             # Try fetching detailed war if possible? No, we can't fetch old war details by ID usually.
             # We rely on what's in the log object.
             return

        for member in target_war.clan.members:
            attacks_used = len(member.attacks)
            total_stars = sum(a.stars for a in member.attacks)
            avg_destruction = sum(a.destruction for a in member.attacks) / attacks_used if attacks_used > 0 else 0
            
            # We assume defensive stars are lost (0) if not in log, or we can't get them easily.
            # Update DB
            db.execute("""
                UPDATE war_performance 
                SET stars=%s, destruction_percentage=%s, attacks_used=%s 
                WHERE war_id=%s AND player_tag=%s
            """, (total_stars, avg_destruction, attacks_used, WAR_ID_TO_FIX, member.tag))
            
            # 3. Restore Attacks (Granular)
            for i, attack in enumerate(member.attacks, 1):
                # Basic attack data (WarLog might miss duration/army details)
                attack_data = {
                    'stars': attack.stars,
                    'destruction': attack.destruction,
                    'duration': getattr(attack, 'duration', 0), 
                    'army_composition': '{}', # Likely missing in log
                    'order': i,
                    'defender_tag': attack.defender_tag,
                    'defender_th': attack.defender.town_hall if attack.defender else 0
                }
                db.update_war_attack(WAR_ID_TO_FIX, member.tag, attack_data)

        print("✅ Repair complete!")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.close()
        db.close()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
