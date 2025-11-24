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

            war_data = {'opponent_name': war.opponent.name, 'opponent_tag': war.opponent.tag, 'type': war_type,
                        'state': clean_state, 'start_time': start_time, 'end_time': end_time}
            war_id = db.update_war(war_data)

            if not war_id: return

            for member in war.clan.members:
                attacks_used = len(member.attacks)
                total_stars = sum(a.stars for a in member.attacks)
                best_destruction = max((a.destruction for a in member.attacks), default=0)
                defense_stars = member.best_opponent_attack.stars if member.best_opponent_attack else 0
                player_data = {'tag': member.tag, 'town_hall': member.town_hall, 'stars': total_stars,
                               'destruction': best_destruction, 'attacks_used': attacks_used,
                               'defense_stars': defense_stars}
                db.update_war_performance(war_id, player_data)

            for member in war.opponent.members:
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