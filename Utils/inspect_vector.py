import asyncio
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import coc
from config import Config

async def inspect():
    client = coc.Client()
    await client.login(Config.COC_EMAIL, Config.COC_PASSWORD)
    
    print("🔍 Fetching Current War...")
    war = await client.get_current_war(Config.CLAN_TAG)
    
    found_attack = False
    for member in war.clan.members:
        if member.attacks:
            attack = member.attacks[0]
            print(f"\nExample Attack by {member.name}:")
            print("Attributes:", dir(attack))
            print("vars:", vars(attack))
            found_attack = True
            break
            
    if not found_attack:
        print("No attacks found in current war to inspect.")
        
    await client.close()

if __name__ == "__main__":
    asyncio.run(inspect())
