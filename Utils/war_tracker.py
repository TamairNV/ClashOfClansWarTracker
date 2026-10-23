import asyncio
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import coc
from config import Config
from sqlManager import SQLManager
import datetime


async def check_past_wars(client, db):

    # 1. Identify Target Wars
    print("🔍 Checking for wars needing result updates...")
    sql = """
        SELECT * FROM wars 
        WHERE (state = 'warEnded' AND result IS NULL)
        OR (state = 'inWar' AND end_time < UTC_TIMESTAMP())
        ORDER BY start_time DESC LIMIT 5
    """
    targets = db.fetch_all(sql)
    
    if not targets:
        print("   -> No pending wars found.")
        return

    print(f"   -> Found {len(targets)} wars to verify.")

    try:
        group = await client.get_league_group(Config.CLAN_TAG)
    except coc.NotFound:
        print("   -> No active CWL group found.")
        group = None
    except Exception as e:
        print(f"   -> Error fetching league group: {e}")
        group = None


    def process_war_result(coc_war, db_war):

        if coc_war.clan.tag == Config.CLAN_TAG:
            our_clan = coc_war.clan
            enemy_clan = coc_war.opponent
        else:
            our_clan = coc_war.opponent
            enemy_clan = coc_war.clan
            
        # Calculate Result
        if our_clan.stars > enemy_clan.stars:
            res = 'win'
        elif our_clan.stars < enemy_clan.stars:
            res = 'lose'
        else:
            if our_clan.destruction > enemy_clan.destruction:
                res = 'win'
            elif our_clan.destruction < enemy_clan.destruction:
                res = 'lose'
            else:
                res = 'draw'

        print(f"Updating War vs {enemy_clan.name}: Result={res}")
        

        
        sql_update = "UPDATE wars SET result=%s, state='warEnded' WHERE war_id=%s"
        db.execute(sql_update, (res, db_war['war_id']))
        
    # 3. Match and Update
    for db_war in targets:
        # CWL Check
        found = False
        if group:
            async for war in group.get_wars_for_clan(Config.CLAN_TAG):
                if war.opponent.tag == db_war['opponent_tag']:

                    war_end = war.end_time.time.replace(tzinfo=None)

                    
                    if abs((war_end - db_war['end_time']).total_seconds()) < 7200:
                         if war.state == 'warEnded':
                             process_war_result(war, db_war)
                             found = True
                             break
            if found: continue
            
        # Regular War Check from Log
        if not found:
            try:
                war_log = await client.get_war_log(Config.CLAN_TAG, limit=20)
                for log_entry in war_log:
                    if log_entry.opponent and log_entry.opponent.tag == db_war['opponent_tag']:  # CWL log entries have no opponent
                        war_end = log_entry.end_time.time.replace(tzinfo=None)
                        if abs((war_end - db_war['end_time']).total_seconds()) < 86400: # 1 day tolerance
                            process_war_result(log_entry, db_war)
                            found = True
                            break
            except Exception as e:
                print(f"   -> Error checking war log: {e}")

        # Fallback: work the result out from what we stored during the war
        if not found:
            result_from_db(db, db_war)


def result_from_db(db, db_war):
    if not db_war['end_time'] or db_war['end_time'] > datetime.datetime.utcnow() - datetime.timedelta(hours=1):
        return
    war_id = db_war['war_id']
    ours = db.fetch_one("SELECT COALESCE(SUM(stars),0) AS stars, COALESCE(AVG(destruction),0) AS dest, COUNT(*) AS n FROM war_opponents WHERE war_id=%s", (war_id,))
    theirs = db.fetch_one("SELECT COALESCE(SUM(defense_stars),0) AS stars, COUNT(*) AS n FROM war_performance WHERE war_id=%s", (war_id,))
    if not theirs['n'] or ours['n'] < theirs['n']:
        return  # enemy line-up incomplete (early wars only stored part of it)
    their_dest = db.fetch_one("""
        SELECT COALESCE(SUM(best),0) AS total FROM (
            SELECT MAX(destruction_percentage) AS best FROM war_defenses WHERE war_id=%s GROUP BY defender_tag
        ) d""", (war_id,))['total'] / theirs['n']

    # Older defence rows were partly overwritten, so their_dest is only a lower bound.
    if ours['stars'] != theirs['stars']:
        res = 'win' if ours['stars'] > theirs['stars'] else 'lose'
    elif ours['dest'] >= 99.99:
        res = 'draw'  # equal stars and we hit 100%, so they did too
    elif ours['dest'] < their_dest:
        res = 'lose'
    else:
        print(f"   -> War {war_id} vs {db_war['opponent_name']}: tied on stars, can't tell result from stored data")
        return
    print(f"   -> War {war_id} vs {db_war['opponent_name']}: result from stored data = {res}")
    db.execute("UPDATE wars SET result=%s WHERE war_id=%s", (res, war_id))

async def main():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    client = coc.Client()

    try:
        await client.login(Config.COC_EMAIL, Config.COC_PASSWORD)

        print("🧹 Checking for stale wars...")
        stale_wars = db.get_stale_wars()
        for stale in stale_wars:
            print(f"Found stale war vs {stale['opponent_name']} (ID: {stale['war_id']}). Force closing...")
            db.force_close_war(stale['war_id'])
            print(f"War {stale['war_id']} marked as ended.")
            
        print(f"Checking Current War for {Config.CLAN_TAG}...")
        war = await client.get_current_war(Config.CLAN_TAG)

        raw_state = str(war.state)
        state_map = {"In War": "inWar", "inWar": "inWar", "Preparation": "preparation", "preparation": "preparation",
                     "War Ended": "warEnded", "warEnded": "warEnded"}
        clean_state = state_map.get(raw_state, raw_state)

        if clean_state in ['inWar', 'warEnded', 'preparation']:
            print(f"Processing War vs {war.opponent.name} (State: {clean_state})...")
            war_type = 'regular' if war.type == 'random' else war.type
            start_time = war.start_time.time if war.start_time else None
            end_time = war.end_time.time if war.end_time else None

            if not start_time: return

            # Calculate Result Logic
            result = None
            if clean_state == 'warEnded':
                if war.clan.stars > war.opponent.stars:
                    result = 'win'
                elif war.clan.stars < war.opponent.stars:
                    result = 'lose'
                else:
                     if war.clan.destruction > war.opponent.destruction:
                         result = 'win'
                     elif war.clan.destruction < war.opponent.destruction:
                         result = 'lose'
                     else:
                         result = 'draw'

            war_data = {'opponent_name': war.opponent.name, 'opponent_tag': war.opponent.tag, 'type': war_type,
                        'state': clean_state, 'start_time': start_time, 'end_time': end_time, 'result': result}
            war_id = db.update_war(war_data)

            if not war_id: return

            for member in war.clan.members:
                attacks_used = len(member.attacks)
                # Update Summary
                total_stars = sum(a.stars for a in member.attacks)
                avg_destruction = sum(a.destruction for a in member.attacks) / attacks_used if attacks_used > 0 else 0
                defense_stars = member.best_opponent_attack.stars if member.best_opponent_attack else 0
                player_data = {'tag': member.tag, 'town_hall': member.town_hall, 'stars': total_stars,
                               'destruction': avg_destruction, 'attacks_used': attacks_used,
                               'defense_stars': defense_stars}
                db.update_war_performance(war_id, player_data)

                # Update Individual Attacks (Granular)
                for i, attack in enumerate(member.attacks, 1):

                    army_json = []
                    if hasattr(attack, 'units') and attack.units:
                        for unit in attack.units:
                            army_json.append({'name': unit.name, 'level': unit.level})
                    
                    # 2. Parse Hero Equipment
                    equipment_json = []
                    if hasattr(attack, 'hero_equipment'):
                         for equip in attack.hero_equipment:
                             equipment_json.append({'name': equip.name, 'level': equip.level})

                    import json
                    attack_data = {
                        'stars': attack.stars,
                        'destruction': attack.destruction,
                        'duration': attack.duration, 
                        'army_composition': json.dumps(army_json),
                        'hero_equipment': json.dumps(equipment_json),
                        'order': i,
                        'defender_tag': attack.defender_tag,
                        'defender_th': attack.defender.town_hall if attack.defender else 0
                    }
                    db.update_war_attack(war_id, member.tag, attack_data)


            for enemy in war.opponent.members:
                for i, attack in enumerate(enemy.attacks, 1):

                    if attack.defender_tag:

                        enemy_army = []
                        if hasattr(attack, 'units'):
                            for unit in attack.units:
                                enemy_army.append({'name': unit.name, 'level': unit.level})
                        
                        enemy_equip = []
                        if hasattr(attack, 'hero_equipment'):
                             for equip in attack.hero_equipment:
                                 enemy_equip.append({'name': equip.name, 'level': equip.level})
                        
                        import json
                        defense_data = {
                            'attacker_tag': enemy.tag,
                            'attacker_name': enemy.name,
                            'stars': attack.stars,
                            'destruction': attack.destruction,
                            'duration': attack.duration,
                            'order': attack.order,
                            'army_composition': json.dumps(enemy_army),
                            'hero_equipment': json.dumps(enemy_equip)
                        }

                        db.update_war_defense(war_id, attack.defender_tag, defense_data)

                stars_surrendered = enemy.best_opponent_attack.stars if enemy.best_opponent_attack else 0
                destruction_surrendered = enemy.best_opponent_attack.destruction if enemy.best_opponent_attack else 0
                

                enemy_data = {'tag': enemy.tag, 'map_position': enemy.map_position, 'town_hall': enemy.town_hall,
                              'stars': stars_surrendered, 'destruction': destruction_surrendered}
                db.update_war_opponent(war_id, enemy_data)

            print(f"Updated stats for {len(war.clan.members)} players and opponents.")
        else:
            print(f"War State: {raw_state} (Not tracking)")


        await check_past_wars(client, db)

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.close()
        db.close()


if __name__ == "__main__":
    asyncio.run(main())