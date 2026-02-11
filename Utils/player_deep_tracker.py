import asyncio
import os
import sys
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import coc
from config import Config
from sqlManager import SQLManager

async def track_deep_stats():
    # 1. Init
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    client = coc.Client()
    
    try:
        await client.login(Config.COC_EMAIL, Config.COC_PASSWORD)
        print("🔍 Fetching Clan Member List...")
        clan = await client.get_clan(Config.CLAN_TAG)
        
        print(f"📊 Processing {len(clan.members)} members for Deep Stats (Achievements)...")
        
        for member in clan.members:
            try:
                # Fetch full player details
                player = await client.get_player(member.tag)
                
                # Parse Achievements
                achievements = []
                if hasattr(player, 'achievements'):
                    for ach in player.achievements:
                        achievements.append({
                            'name': ach.name,
                            'stars': ach.stars,
                            'value': ach.value,
                            'target': ach.target,
                            'info': ach.info,
                            'completion_info': ach.completion_info
                        })
                
                # Check Labels too
                labels = []
                if hasattr(player, 'labels'):
                     for label in player.labels:
                         labels.append({'name': label.name, 'id': label.id})
                

                # Update DB
                achievements_json = json.dumps(achievements)
                db.update_player_achievements(player.tag, achievements_json)
                
                # Also ensure builder trophies are synced here as a backup
                if hasattr(player, 'builder_base_trophies'):
                     pass
                     
            except Exception as e:
                print(f"⚠Error fetching {member.name}: {e}")
                
        print("Deep Stats Sync Complete.")
        
    except Exception as e:
        print(f"Global Error in Deep Tracker: {e}")
    finally:
        await client.close()
        db.close()

if __name__ == "__main__":
    asyncio.run(track_deep_stats())
