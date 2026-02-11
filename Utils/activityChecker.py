import asyncio
import coc
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import Config
from sqlManager import SQLManager


async def main():
    # 1. Initialize Database
    db = SQLManager(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        db_name=Config.DB_NAME
    )

    client = coc.Client()

    try:

        print("🔑 Logging into Clash API...")
        await client.login(email=Config.COC_EMAIL, password=Config.COC_PASSWORD)


        print(f"🔍 Fetching data for Clan: {Config.CLAN_TAG}")
        clan = await client.get_clan(Config.CLAN_TAG)

        current_api_tags = []

        print(f"📊 Processing {len(clan.members)} members...")


        for member in clan.members:
            current_api_tags.append(member.tag)


            db.update_player_roster(member)


            db.update_activity_heartbeat(
                player_tag=member.tag,
                current_donations=member.donations,
                current_received=member.received
            )


        active_db_players = db.fetch_all("SELECT player_tag, name FROM players WHERE is_in_clan = TRUE")

        if active_db_players:
            for row in active_db_players:
                db_tag = row['player_tag']


                if db_tag not in current_api_tags:
                    print(f"👋 Player Left: {row['name']} ({db_tag})")
                    db.mark_player_left(db_tag)

    except coc.InvalidCredentials:
        print("Error: Invalid Clash of Clans API credentials.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup connections
        await client.close()
        db.close()
        print("Sync Complete")


if __name__ == "__main__":
    # Run the async main loop
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())