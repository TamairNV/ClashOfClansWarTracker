import asyncio
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import coc
from config import Config

async def inspect_achievements():
    client = coc.Client()
    await client.login(Config.COC_EMAIL, Config.COC_PASSWORD)
    
    print("🔍 Fetching Clan and First Member...")
    clan = await client.get_clan(Config.CLAN_TAG)
    
    if clan.members:
        member_tag = clan.members[0].tag
        print(f"Fetching full details for {clan.members[0].name} ({member_tag})...")
        
        # We need to fetch the full player object to get achievements, 
        # as the member object in get_clan might be partial.
        player = await client.get_player(member_tag)
        
        print(f"\n🏆 Achievements for {player.name}:")
        if hasattr(player, 'achievements'):
            # Print first 5 to show structure
            for i, ach in enumerate(player.achievements[:5]):
                print(f" - {ach.name}: {ach.value}/{ach.target} (Stars: {ach.stars}) - {ach.info}")
            
            print(f"\nTotal Achievements: {len(player.achievements)}")
            
            # Check for specific high-value ones
            interesting = ["War Hero", "Games Champion", "Aggressive Capitalism", "Sweet Victory"]
            print("\n💎 Key Achievements Values:")
            for ach in player.achievements:
                if ach.name in interesting:
                    print(f" - {ach.name}: {ach.value}")
        else:
            print("No 'achievements' attribute found on Player object.")
            
    await client.close()

if __name__ == "__main__":
    asyncio.run(inspect_achievements())
