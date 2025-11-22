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

    # 2. Initialize CoC Client
    # We use the standard Client. You can add key_count=5 if you run this often concurrently.
    client = coc.Client()

    try:
        # Login to Supercell
        print("🔑 Logging into Clash API...")
        await client.login(email=Config.COC_EMAIL, password=Config.COC_PASSWORD)

        # 3. Fetch Clan Data
        print(f"🔍 Fetching data for Clan: {Config.CLAN_TAG}")
        clan = await client.get_clan(Config.CLAN_TAG)

        current_api_tags = []

        print(f"📊 Processing {len(clan.members)} members...")

        # --- LOOP 1: PROCESS CURRENT MEMBERS ---
        for member in clan.members:
            current_api_tags.append(member.tag)

            # A. Update Roster (Add if new, update TH/Name if changed)
            # Note: We pass the whole member object; db_manager handles the parsing
            db.update_player_roster(member)

            # B. Check Activity Heartbeat
            # This compares current donations to DB donations
            db.update_activity_heartbeat(
                player_tag=member.tag,
                current_donations=member.donations,
                current_received=member.received
            )

        # --- LOOP 2: DETECT LEAVERS ---
        # Get everyone the DB *thinks* is currently in the clan
        active_db_players = db.fetch_all("SELECT player_tag, name FROM players WHERE is_in_clan = TRUE")

        if active_db_players:
            for row in active_db_players:
                db_tag = row['player_tag']

                # If they are in DB as active, but NOT in the API list we just fetched...
                if db_tag not in current_api_tags:
                    print(f"👋 Player Left: {row['name']} ({db_tag})")
                    db.mark_player_left(db_tag)

    except coc.InvalidCredentials:
        print("❌ Error: Invalid Clash of Clans API credentials.")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Cleanup connections
        await client.close()
        db.close()
        print("✅ Sync Complete")


if __name__ == "__main__":
    # Run the async main loop
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())