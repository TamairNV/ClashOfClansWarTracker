import asyncio
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

        # Get raw state string
        raw_state = str(war.state)

        # --- FIX: Normalize State ---
        # coc.py sometimes returns "In War" (Enum) but DB needs "inWar" (String)
        state_map = {
            "In War": "inWar",
            "inWar": "inWar",
            "Preparation": "preparation",
            "preparation": "preparation",
            "War Ended": "warEnded",
            "warEnded": "warEnded"
        }
        # Use mapped value, or default to raw if not found
        clean_state = state_map.get(raw_state, raw_state)

        # Check if valid state for tracking
        if clean_state in ['inWar', 'warEnded', 'preparation']:
            print(f"Processing War vs {war.opponent.name} (State: {clean_state})...")

            # Map API type to Database ENUM
            war_type = 'regular' if war.type == 'random' else war.type

            # Safety check for timestamps
            start_time = war.start_time.time if war.start_time else None
            end_time = war.end_time.time if war.end_time else None

            if not start_time:
                print("⚠️ Warning: No start time found. Skipping.")
                return

            war_data = {
                'opponent_name': war.opponent.name,
                'opponent_tag': war.opponent.tag,
                'type': war_type,
                'state': clean_state,  # <--- Using Clean State
                'start_time': start_time,
                'end_time': end_time
            }
            war_id = db.update_war(war_data)

            if not war_id:
                print("❌ Could not retrieve War ID.")
                return

            # 1. Save OUR Team Stats
            for member in war.clan.members:
                attacks_used = len(member.attacks)
                total_stars = sum(a.stars for a in member.attacks)
                best_destruction = max((a.destruction for a in member.attacks), default=0)
                defense_stars = member.best_opponent_attack.stars if member.best_opponent_attack else 0

                player_data = {
                    'tag': member.tag,
                    'town_hall': member.town_hall,
                    'stars': total_stars,
                    'destruction': best_destruction,
                    'attacks_used': attacks_used,
                    'defense_stars': defense_stars
                }
                db.update_war_performance(war_id, player_data)

            # 2. Save ENEMY Team Stats
            for member in war.opponent.members:
                stars_surrendered = member.best_opponent_attack.stars if member.best_opponent_attack else 0
                destruction_surrendered = member.best_opponent_attack.destruction if member.best_opponent_attack else 0

                enemy_data = {
                    'tag': member.tag,
                    'map_position': member.map_position,
                    'town_hall': member.town_hall,
                    'stars': stars_surrendered,
                    'destruction': destruction_surrendered
                }
                db.update_war_opponent(war_id, enemy_data)

            print(f"✅ Updated stats for {len(war.clan.members)} players and opponents.")

        else:
            print(f"💤 War State: {raw_state} (Not tracking)")

    except coc.PrivateWarLog:
        print("❌ Error: Clan War Log is private!")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.close()
        db.close()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())