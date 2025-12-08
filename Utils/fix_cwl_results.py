
import asyncio
import coc
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from Utils.sqlManager import SQLManager

async def fix_results():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    client = coc.Client()
    
    try:
        print("🔑 Logging in to CoC API...")
        await client.login(Config.COC_EMAIL, Config.COC_PASSWORD)
        
        print(f"📜 Fetching War Log for {Config.CLAN_TAG}...")
        war_log = await client.get_war_log(Config.CLAN_TAG, limit=50) # Fetch more to be safe
        
        print(f"Processing {len(war_log)} log entries...")
        
        updated_count = 0
        
        for war in war_log:
            # Map result
            api_result = getattr(war, 'result', None)
            if not api_result:
                continue
                
            clean_result = 'draw' if api_result == 'tie' else str(api_result).lower()
            
            # Update DB using end_time match (fuzzy 2 hours to be safe)
            # MySQL TIMESTAMPDIFF(UNIT, start, end)
            sql = """
                UPDATE wars 
                SET result = %s 
                WHERE opponent_tag = %s 
                AND ABS(TIMESTAMPDIFF(MINUTE, end_time, %s)) < 120
            """
            
            # We use distinct fetch to see if it actually matches anything
            # But execute returns rows affected usually?
            # PyMySQL cursor.rowcount
            
            # Since sqlManager.execute doesn't return rowcount easily (wraps it), 
            # we'll just run it.
            
            try:
                # We need to access the internal cursor execution to get rowcount if we care, 
                # but let's just assume it works.
                end_time_dt = war.end_time.time
                
                if updated_count < 15:
                    print(f"DEBUG: Log entry #{updated_count+1}: {war.opponent.name} (Tag: {war.opponent.tag}, Result: {api_result})")

                db.execute(sql, (clean_result, war.opponent.tag, end_time_dt))
                updated_count += 1
            except Exception as e:
                print(f"Failed to update {war.opponent.name}: {e}")

        print(f"✅ Processed {updated_count} log entries.")

        # --- FIX CWL WARS ---
        print("🏆 Fetching CWL Group...")
        try:
            # Newer coc.py uses get_league_group
            group = await client.get_league_group(Config.CLAN_TAG)
        except AttributeError:
             print("Fallback: trying get_clan_war_league_group")
             group = await client.get_clan_war_league_group(Config.CLAN_TAG)
        except coc.NotFound:
            print("⚠️ No active CWL group found.")
            return

        print(f"Found group for season {group.season}. State: {group.state}")
        
        cwl_count = 0
        async for war in group.get_wars_for_clan(Config.CLAN_TAG):
            if war.state != 'warEnded':
                continue
                
            # Calculate Result
            # coc.py War object doesn't always have .result for CWL, convert standard logic
            # Note: war.clan is always the clan we searched for (us) in get_wars_for_clan?
            # Let's verify tags just in case.
            
            # Identify us vs them
            if war.clan.tag == Config.CLAN_TAG:
                our_stars = war.clan.stars
                our_dest = war.clan.destruction
                enemy_stars = war.opponent.stars
                enemy_dest = war.opponent.destruction
            else:
                our_stars = war.opponent.stars
                our_dest = war.opponent.destruction
                enemy_stars = war.clan.stars
                enemy_dest = war.clan.destruction

            if our_stars > enemy_stars:
                res = 'win'
            elif our_stars < enemy_stars:
                res = 'lose'
            else:
                res = 'win' if our_dest > enemy_dest else ('lose' if our_dest < enemy_dest else 'draw')
            
            end_time_dt = war.end_time.time
            print(f"DEBUG: CWL War vs {war.opponent.name}: ({our_stars}-{enemy_stars}) => {res}")
            
            sql = """
                UPDATE wars 
                SET result = %s 
                WHERE opponent_tag = %s 
                AND ABS(TIMESTAMPDIFF(MINUTE, end_time, %s)) < 180
            """
            # Increased fuzzy match to 180 mins (3 hours) just in case
            
            db.execute(sql, (res, war.opponent.tag, end_time_dt))
            cwl_count += 1
            
        print(f"✅ Processed {cwl_count} CWL wars.")
        
        # Global Cleanup
        print("🧹 normalizing results case...")
        db.execute("UPDATE wars SET result = LOWER(result) WHERE result IS NOT NULL")
        print("✅ normalization complete.")

    except Exception as e:

        import traceback
        traceback.print_exc()
        print(f"❌ Error: {e}")
    finally:
        await client.close()
        db.close()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(fix_results())
