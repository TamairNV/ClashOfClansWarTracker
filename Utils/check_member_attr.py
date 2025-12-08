import asyncio
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import coc
from config import Config

async def check():
    client = coc.Client()
    await client.login(Config.COC_EMAIL, Config.COC_PASSWORD)
    try:
        clan = await client.get_clan(Config.CLAN_TAG)
        if clan.members:
            mem = clan.members[0]
            print(f"Checking {mem.name}...")
            print(f"Has achievements? {hasattr(mem, 'achievements')}")
            if hasattr(mem, 'achievements'):
                print(f"First achievement: {mem.achievements[0] if mem.achievements else 'None'}")
        else:
            print("No members found.")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(check())
