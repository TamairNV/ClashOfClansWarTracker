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
        print("🌍 Fetching War Log from API...")
        
        # We need to find wars in our DB that match wars in the log
        # The unique key is usually (opponent_tag, end_time) roughly
        
        try:
            war_log = await client.get_war_log(Config.CLAN_TAG)
        except coc.PrivateWarLog:
            print("❌ War Log is private! Cannot fetch historical results.")
            return

        print(f"📜 Found {len(war_log)} entries in war log.")
        
        # Get wars with missing results
        missing_wars = db.fetch_all("SELECT war_id, opponent_tag, opponent_name, result FROM wars WHERE result IS NULL OR result = 'NONE'")
        
        if not missing_wars:
            print("✅ No missing results in DB.")
        
        for db_war in missing_wars:
            print(f"Propcessing missing result for War ID {db_war['war_id']} vs {db_war['opponent_name']}...")
            
            match = None
            for log_entry in war_log:
                # Compare opponent tag (normalized)
                # Some API returns might have partial data?
                if not log_entry.opponent: continue
                
                if log_entry.opponent.tag == db_war['opponent_tag']:
                    match = log_entry
                    break
            
            if match:
                result = str(match.result).lower() # 'win', 'lose', 'tie'
                if result == 'tie': result = 'draw'
                
                print(f"   MATCH FOUND in War Log! Result: {result}")
                
                # Update DB
                db.execute("UPDATE wars SET result=%s WHERE war_id=%s", (result, db_war['war_id']))
                print("   Saved.")
            else:
                # Try CWL Lookup
                print("   ⚠️ Not found in standard log. Checking CWL data...")
                # Only check if we haven't fetched CWL group yet to save API calls
                # But for simplicity in this script, we might just assume current season.
                
                try:
                    group = await client.get_league_group(Config.CLAN_TAG)
                    found_cwl = False
                    
                    # Iterate through all rounds
                    for round_idx, cwl_round in enumerate(group.rounds):
                        if not cwl_round or cwl_round[0] == "#0": continue # Status unstarted
                        
                        # cwl_round is a list of war_tags (strings)
                        for war_tag in cwl_round:
                            if war_tag == "#0": continue
                            
                            try:
                                cwl_war = await client.get_league_war(war_tag)
                            except: 
                                continue
                            
                            # Debug: See who we found
                            # print(f"DEBUG: Checked {cwl_war.clan.name} vs {cwl_war.opponent.name}")
                            
                            found = False
                            if cwl_war.clan.tag == Config.CLAN_TAG and cwl_war.opponent.tag == db_war['opponent_tag']:
                                found = True
                            elif cwl_war.opponent.tag == Config.CLAN_TAG and cwl_war.clan.tag == db_war['opponent_tag']:
                                # Swap logic if we are listed as opponent
                                temp = cwl_war.clan
                                cwl_war.clan = cwl_war.opponent
                                cwl_war.opponent = temp
                                found = True
                            
                            if found:
                                print(f"   🎯 FOUND MATCH! {cwl_war.clan.name} vs {cwl_war.opponent.name}")
                                # MATCH!
                                if cwl_war.state == 'warEnded':
                                    if cwl_war.clan.stars > cwl_war.opponent.stars: result = 'win'
                                    elif cwl_war.clan.stars < cwl_war.opponent.stars: result = 'lose'
                                    elif cwl_war.clan.destruction > cwl_war.opponent.destruction: result = 'win' # CWL rule?
                                    else: result = 'lose' # Hard to draw in CWL compared to regular? Actually destruction matters.
                                    # Regular war: Stars -> Dest %. CWL: Stars -> Dest %. Same rules.
                                    
                                    if cwl_war.clan.stars == cwl_war.opponent.stars:
                                        if cwl_war.clan.destruction > cwl_war.opponent.destruction: result = 'win'
                                        elif cwl_war.clan.destruction < cwl_war.opponent.destruction: result = 'lose'
                                        else: result = 'draw'

                                    print(f"   CWL MATCH FOUND! Result: {result}")
                                    db.execute("UPDATE wars SET result=%s WHERE war_id=%s", (result, db_war['war_id']))
                                    found_cwl = True
                                    break
                            elif cwl_war.opponent.tag == Config.CLAN_TAG and cwl_war.clan.tag == db_war['opponent_tag']:
                                # We are 'opponent' in this object? (Unlikely with get_league_war logic but possible)
                                # Usually client.get_league_war returns generic war object.
                                # Let's assume the above checks cover "Us vs Them".
                                pass
                        
                        if found_cwl: break
                    
                    if not found_cwl:
                         print("   ❌ Not found in current CWL season either.")
                         
                except coc.NotFound:
                    print("   ❌ Clan not in CWL.")
                except Exception as e:
                    print(f"   ❌ CWL Error: {e}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.close()
        db.close()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
