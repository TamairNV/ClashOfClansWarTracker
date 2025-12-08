import asyncio
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import coc
from config import Config

async def audit():
    client = coc.Client()
    await client.login(Config.COC_EMAIL, Config.COC_PASSWORD)
    
    print("🔍 Fetching Clan Data...")
    clan = await client.get_clan(Config.CLAN_TAG)
    
    print("\n--- CLAN OBJECT ATTRIBUTES (vs what we store) ---")
    ignored_clan_attrs = []
    # Major attributes to check
    check_list = ['capital_league', 'capital_points', 'chat_language', 'clan_capital', 
                  'description', 'labels', 'location', 'member_count', 'points', 'required_trophies', 
                  'war_league', 'war_log_public', 'war_win_streak']
    
    for attr in check_list:
        val = getattr(clan, attr, 'N/A')
        print(f"{attr}: {val}")

    print("\n--- MEMBER OBJECT ATTRIBUTES (vs what we store) ---")
    member = clan.members[0]
    # We store: tag, name, role, th, exp, trophies, donations...
    # checking for obscure ones
    member_checks = ['builder_base_trophies', 'clan_rank', 'league.name', 'labels', 'versus_trophies', 'war_preference']
    for attr in member_checks:
        # nested checks
        if '.' in attr:
            base, sub = attr.split('.')
            val = getattr(getattr(member, base, None), sub, 'N/A')
        else:
            val = getattr(member, attr, 'N/A')
        print(f"{attr}: {val}")

    print("\n--- CLAN CAPITAL (Raid Weekends) ---")
    # We suspect we don't store this.
    try:
        raid_log = await client.get_raid_log(Config.CLAN_TAG, limit=1)
        if raid_log:
            print("✅ Raid Log Available (We DO NOT store this yet!)")
            print(f"Sample Raid: {raid_log[0].start_time} - Loot: {raid_log[0].total_loot}")
        else:
            print("❌ No Raid Log found")
    except Exception as e:
        print(f"⚠️ Raid Log Error: {e}")
        
    print("\n--- CLAN GAMES ---")
    # API doesn't always expose current clan games points per player easily unless active.
    # Usually unrelated to war tracker.

    await client.close()

if __name__ == "__main__":
    asyncio.run(audit())
