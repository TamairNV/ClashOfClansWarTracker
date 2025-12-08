import asyncio
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import coc
from config import Config
from sqlManager import SQLManager

async def main():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    client = coc.Client()

    try:
        await client.login(Config.COC_EMAIL, Config.COC_PASSWORD)
        
        # --- CLEANUP STALE WARS ---
        print("🧹 Checking for stale wars...")
        stale_wars = db.get_stale_wars()
        for stale in stale_wars:
            print(f"⚠️ Found stale war vs {stale['opponent_name']} (ID: {stale['war_id']}). Force closing...")
            db.force_close_war(stale['war_id'])
            print(f"✅ War {stale['war_id']} marked as ended.")
            
        print(f"⚔️ Checking Current War for {Config.CLAN_TAG}...")
        war = await client.get_current_war(Config.CLAN_TAG)

        raw_state = str(war.state)
        state_map = {"In War": "inWar", "inWar": "inWar", "Preparation": "preparation", "preparation": "preparation",
                     "War Ended": "warEnded", "warEnded": "warEnded"}
        clean_state = state_map.get(raw_state, raw_state)

        if clean_state in ['inWar', 'warEnded', 'preparation']:
            print(f"Processing War vs {war.opponent.name} (State: {clean_state})...")
            war_type = 'regular' if war.type == 'random' else war.type
            start_time = war.start_time.time if war.start_time else None
            end_time = war.end_time.time if war.end_time else None

            if not start_time: return

            # Calculate Result Logic
            result = None
            if clean_state == 'warEnded':
                if war.clan.stars > war.opponent.stars:
                    result = 'win'
                elif war.clan.stars < war.opponent.stars:
                    result = 'lose'
                else:
                     if war.clan.destruction > war.opponent.destruction:
                         result = 'win'
                     elif war.clan.destruction < war.opponent.destruction:
                         result = 'lose'
                     else:
                         result = 'draw'

            war_data = {'opponent_name': war.opponent.name, 'opponent_tag': war.opponent.tag, 'type': war_type,
                        'state': clean_state, 'start_time': start_time, 'end_time': end_time, 'result': result}
            war_id = db.update_war(war_data)

            if not war_id: return

            for member in war.clan.members:
                attacks_used = len(member.attacks)
                # Update Summary
                total_stars = sum(a.stars for a in member.attacks)
                avg_destruction = sum(a.destruction for a in member.attacks) / attacks_used if attacks_used > 0 else 0
                defense_stars = member.best_opponent_attack.stars if member.best_opponent_attack else 0
                player_data = {'tag': member.tag, 'town_hall': member.town_hall, 'stars': total_stars,
                               'destruction': avg_destruction, 'attacks_used': attacks_used,
                               'defense_stars': defense_stars}
                db.update_war_performance(war_id, player_data)

                # Update Individual Attacks (Granular)
                for i, attack in enumerate(member.attacks, 1):
                    # 1. Parse Army Composition
                    army_json = []
                    # coc.py returns 'units' as a list of Unit objects (name, level, etc.)
                    # We'll need to check if 'units' attribute exists and iterate
                    if hasattr(attack, 'units'):
                        for unit in attack.units:
                            army_json.append({'name': unit.name, 'level': unit.level})
                    
                    # 2. Parse Hero Equipment
                    equipment_json = []
                    if hasattr(attack, 'hero_equipment'):
                         for equip in attack.hero_equipment:
                             equipment_json.append({'name': equip.name, 'level': equip.level})

                    import json
                    attack_data = {
                        'stars': attack.stars,
                        'destruction': attack.destruction,
                        'duration': attack.duration, 
                        'army_composition': json.dumps(army_json),
                        'hero_equipment': json.dumps(equipment_json),
                        'order': i,
                        'defender_tag': attack.defender_tag,
                        'defender_th': attack.defender.town_hall if attack.defender else 0
                    }
                    db.update_war_attack(war_id, member.tag, attack_data)

            # --- TRACK DEFENSES (Attacks against us) ---
            # To get attacks against us, we look at the OPPONENT'S members and their attacks
            for enemy in war.opponent.members:
                for i, attack in enumerate(enemy.attacks, 1):
                    # The 'defender' is US.
                    if attack.defender_tag:
                         # Parse Enemy Army/Equip just like above
                        enemy_army = []
                        if hasattr(attack, 'units'):
                            for unit in attack.units:
                                enemy_army.append({'name': unit.name, 'level': unit.level})
                        
                        enemy_equip = []
                        if hasattr(attack, 'hero_equipment'):
                             for equip in attack.hero_equipment:
                                 enemy_equip.append({'name': equip.name, 'level': equip.level})
                        
                        import json
                        defense_data = {
                            'attacker_tag': enemy.tag,
                            'attacker_name': enemy.name,
                            'stars': attack.stars,
                            'destruction': attack.destruction,
                            'duration': attack.duration,
                            'order': i,
                            'army_composition': json.dumps(enemy_army),
                            'hero_equipment': json.dumps(enemy_equip)
                        }
                        # Store in war_defenses table
                        db.update_war_defense(war_id, attack.defender_tag, defense_data)
                # The 'backfill' script was calculating result from this table erroneously.
                # Now that we save 'result' directly, we don't need to backfill from this table.
                
                stars_surrendered = member.best_opponent_attack.stars if member.best_opponent_attack else 0
                destruction_surrendered = member.best_opponent_attack.destruction if member.best_opponent_attack else 0
                enemy_data = {'tag': member.tag, 'map_position': member.map_position, 'town_hall': member.town_hall,
                              'stars': stars_surrendered, 'destruction': destruction_surrendered}
                db.update_war_opponent(war_id, enemy_data)

            print(f"✅ Updated stats for {len(war.clan.members)} players and opponents.")
        else:
            print(f"💤 War State: {raw_state} (Not tracking)")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.close()
        db.close()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())