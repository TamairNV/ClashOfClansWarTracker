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
                    # Extract Army Composition
                    army_json = {} 
                    attack_data = {
                        'stars': attack.stars,
                        'destruction': attack.destruction,
                        'duration': attack.duration, # Seconds
                        'army_composition': str(army_json),
                        'order': i,
                        'defender_tag': attack.defender_tag,
                        'defender_th': attack.defender.town_hall if attack.defender else 0
                    }
                    db.update_war_attack(war_id, member.tag, attack_data)

            for member in war.opponent.members:
                # FIX: We want stats THEY scored (Offense), not stats SURRENDERED (Defense)
                # But typically war_opponents table tracks the enemy BASES (Targets).
                # If we want 'stars' column to be 'Stars they got', we should sum their attacks?
                # However, previous code used 'best_opponent_attack' which is OUR attack on them.
                # Given 'backfill' assumes 'stars' is THEIR score, we have a schema confusion.
                # Best approach: Use 'stars' for THEIR OFFENSE to fix the stats bug.
                # BUT 'town_hall' and 'map_position' refer to the BASE.
                # Ideally, we'd have 'stars_scored' and 'stars_yielded'.
                # For now, let's stick to fixing the "Draw" bug which relies on Result.
                # We will store Best Opponent Attack (Stars We Got) because that's useful for "Did we verify this base?"
                # AND we rely on the explicitly passed 'result' in war_data for the W/L.
                
                # Reverting to "Stars We Got" logic because 'war_opponents' is primarily a Target List.
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