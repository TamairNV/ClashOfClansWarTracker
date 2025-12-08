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
        print("🏰 Fetching Clan Capital Raid Log...")
        
        # Fetch last 5 raid weekends to ensure we capture ongoing + recent history
        raid_log = await client.get_raid_log(Config.CLAN_TAG, limit=5)
        
        for raid in raid_log:
            # We use start_time as a unique ID string
            # coc.py Timestamp object usually has a .time attribute returning a datetime
            raid_id = f"raid_{raid.start_time.time.strftime('%Y%m%d')}"
            
            # Debug: what is raid.attack_log?
            # It seems to be a list of RaidClan objects (districts)? 
            # Or raid.total_attacks is a direct property?
            # Let's check direct properties first.
            
            # From CoC API docs, RaidLogEntry has: state, start_time, end_time, total_loot, members, attack_log, defense_log.
            # attack_log is a list of clans we attacked? No, it's usually detailed info.
            # Let's try to get aggregate info if available, otherwise sum it up.
            
            total_attacks = raid.total_attacks if hasattr(raid, 'total_attacks') else 0
            destroyed_count = raid.destroyed_district_count if hasattr(raid, 'destroyed_district_count') else 0
            
            raid_data = {
                'id': raid_id,
                'state': raid.state, # 'ongoing' or 'ended'
                'start_time': raid.start_time.time,
                'end_time': raid.end_time.time,
                'total_loot': raid.total_loot,
                'total_attacks': total_attacks, 
                'districts_destroyed': destroyed_count,
                # Medals aren't explicitly in RaidLogEntry usually, calculated client side?
                # Only individual members might have medals?
                'medals': 0 
            }
            db.update_raid_weekend(raid_data)
            print(f"✅ Updated Raid {raid_id} (State: {raid.state})")
            
            # Members
            for member in raid.members:
                member_data = {
                    'tag': member.tag,
                    'name': member.name,
                    'attacks': member.attack_count,
                    'capital_resources_looted': member.capital_resources_looted,
                    # Bonus medals? Only available if we calculate or if detailed API gives it.
                    # Standard API raid log member entry: attacks, attack_limit, 
                    # capital_resources_looted, bonus_capital_gold...
                    'medals_bonus': 0 
                }
                db.update_raid_member(raid_id, member_data)
                
    except Exception as e:
        print(f"❌ Error in Capital Tracker: {e}")
    finally:
        await client.close()
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
