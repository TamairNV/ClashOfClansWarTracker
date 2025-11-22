import asyncio
import coc
from config import Config
from sqlManager import SQLManager
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


async def main():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    client = coc.Client()

    try:
        print("🔑 Logging in...")
        await client.login(Config.COC_EMAIL, Config.COC_PASSWORD)

        print(f"📜 Fetching War Log for {Config.CLAN_TAG}...")
        # Fetch last 20 wars
        war_log = await client.get_war_log(Config.CLAN_TAG, limit=20)

        for war in war_log:
            print(f"Processing war vs {war.opponent.name} ({war.end_time})")

            # Prepare data
            war_data = {
                'opponent_name': war.opponent.name,
                'opponent_tag': war.opponent.tag,
                'type': 'regular',  # War log doesn't always specify type well, default regular
                'state': 'warEnded',
                'start_time': war.end_time.replace(days=2),  # Approx start time (End - 48h)
                'end_time': war.end_time
            }

            # Save to DB
            db.update_war(war_data)

            # NOTE: We cannot update 'war_performance' here because
            # standard API warlog usually DOES NOT contain member attack lists.

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.close()
        db.close()
        print("✅ Backfill Complete")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())