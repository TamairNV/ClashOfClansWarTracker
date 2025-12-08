import asyncio
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import coc
from config import Config

async def inspect():
    client = coc.Client()
    await client.login(Config.COC_EMAIL, Config.COC_PASSWORD)
    
    print("🔍 Fetching War Log...")
    try:
        # NOTE: public war log must be enabled for this to work
        # and we need to verify if live API provides unit details here.
        war_log = await client.get_war_log(Config.CLAN_TAG, limit=1)
        
        if not war_log:
            print("No wars in usage log.")
            await client.close()
            return

        last_war = war_log[0]
        # In war log, we usually don't get full member/attack objects directly?
        # coc.py models WarLogEntry differently.
        # It typically DOES NOT include individual attack units unless we fetch the specific war by tag?
        # But we can't fetch old wars by tag usually.
        
        print("Last War Opponent:", last_war.opponent.name)
        # Check if we can access members/attacks
        # The WarLogEntry has 'clan' and 'opponent', but does 'clan' have 'members'?
        # coc docs say WarLogEntry has 'clan' (WarLogClan) which has 'members' (list of WarMember)?
        # Let's see.
        
        if hasattr(last_war, 'clan') and hasattr(last_war.clan, 'members'):
            members = last_war.clan.members
            print(f"Found {len(members)} members in log.")
            if members:
                member = members[0]
                if member.attacks:
                    attack = member.attacks[0]
                    print(f" Attack Attributes: {dir(attack)}")
                    print(f" Has units? {hasattr(attack, 'units')}")
                    if hasattr(attack, 'units'):
                        print(f" Units: {attack.units}")
                else:
                    print("Member has no attacks in log entry.")
        else:
            print("WarLogEntry does not have detailed members list.")
            
    except Exception as e:
        print(f"Error: {e}")
        
    await client.close()

if __name__ == "__main__":
    asyncio.run(inspect())
