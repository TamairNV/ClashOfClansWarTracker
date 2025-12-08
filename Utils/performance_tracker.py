import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from sqlManager import SQLManager
from timezone_guesser import TimezoneGuesser



from datetime import datetime, timedelta

def calculate_trust_score(player_th, history, last_active_time=None):
    # ==========================================
    # ⚙️ TWEAK VARIABLES HERE
    # ==========================================
    MAX_TH = 18  # Current Max Town Hall level

    # Weights (Must add up to 1.0)
    W_RELIABILITY = 0.50  # 50% - Showing up to attack
    W_SKILL = 0.15  # 30% - Getting stars
    W_POWER = 0.35  # 20% - Base strength (TH level)

    # Penalties & Boosts
    PENALTY_PER_MISS = 15  # Points lost per missed attack (for high THs)
    HIGH_TH_THRESHOLD = 14  # TH level where missing attacks gets punished

    NEW_PLAYER_WARS = 1  # How many wars count as "New"
    NEW_PLAYER_BOOST = 82.0  # Minimum score for a new player with 100% attendance
    
    # Activity Thresholds
    INACTIVE_DAYS = 7 # If inactive for > 7 days, massive penalty
    RECENTLY_ACTIVE_DAYS = 3 # If active within 3 days, safe from decay
    # ==========================================

    # 1. Power Score Calculation
    power_score = (player_th / MAX_TH) * 100

    # Handle players with NO history
    if not history:
        # Check activity for new/returning players
        if last_active_time:
            if isinstance(last_active_time, str):
                try:
                    last_active_time = datetime.strptime(last_active_time, '%Y-%m-%d %H:%M:%S')
                except:
                    pass
            
            if isinstance(last_active_time, datetime):
                days_inactive = (datetime.now() - last_active_time).days
                if days_inactive < RECENTLY_ACTIVE_DAYS:
                    # Active but no history -> Give them a chance (Roster/Risky)
                    # Base score around 60
                    return 60.0
        
        # Otherwise standard new player logic
        base_weight = W_RELIABILITY + W_SKILL
        return round((50 * base_weight) + (power_score * W_POWER), 1)

    # 2. Aggregate Data
    # RELIABILITY: Only check last 4 wars (User Request)
    recent_history = history[:4]
    
    total_possible_attacks = 0
    max_possible_stars = 0 # For skill, we use full history? Or recent? User said "reliability skewed".
    # Let's use full history for Skill (better sample size) and Recent for Reliability.
    
    # Calculate Reliability on Recent History
    recent_possible_attacks = 0
    recent_attacks_made = 0
    
    for row in recent_history:
        w_type = row.get('war_type', 'regular')
        if w_type and w_type.lower() == 'cwl':
            recent_possible_attacks += 1
        else:
            recent_possible_attacks += 2
        recent_attacks_made += row['attacks_used']
            
    # Calculate Skill on Full History (limit=10 passed in main)
    total_stars = sum(row['stars'] for row in history)
    full_max_possible_stars = 0
    for row in history:
        w_type = row.get('war_type', 'regular')
        if w_type and w_type.lower() == 'cwl':
            full_max_possible_stars += 3
        else:
            full_max_possible_stars += 6

    # 3. Reliability Score (0-100) - BASED ON LAST 4 WARS
    reliability_score = (recent_attacks_made / recent_possible_attacks) * 100 if recent_possible_attacks > 0 else 50

    # 4. Skill Score (0-100) - BASED ON LAST 10 WARS
    skill_score = (total_stars / full_max_possible_stars) * 100 if full_max_possible_stars > 0 else 0

    # 5. Final Weighted Score
    final_score = (reliability_score * W_RELIABILITY) + \
                  (skill_score * W_SKILL) + \
                  (power_score * W_POWER)

    # --- SPECIAL RULES ---

    # New Player Boost (Protect good recruits from low sample size)
    total_wars = len(history)
    if total_wars <= NEW_PLAYER_WARS and recent_attacks_made == recent_possible_attacks:
        final_score = max(final_score, NEW_PLAYER_BOOST)

    # Elite Flake Penalty (Punish high THs who miss attacks in recent history)
    if player_th >= HIGH_TH_THRESHOLD:
        missed_attacks = recent_possible_attacks - recent_attacks_made
        if missed_attacks > 0:
            penalty = missed_attacks * PENALTY_PER_MISS
            final_score -= penalty
            
    # --- ACTIVITY CHECK ---
    if last_active_time:
        if isinstance(last_active_time, str):
            try:
                last_active_time = datetime.strptime(last_active_time, '%Y-%m-%d %H:%M:%S')
            except:
                pass
                
        if isinstance(last_active_time, datetime):
            days_inactive = (datetime.now() - last_active_time).days
            
            if days_inactive > INACTIVE_DAYS:
                # Inactive > 7 days -> Bench them (Max score 40)
                final_score = min(final_score, 40.0)
            elif days_inactive < RECENTLY_ACTIVE_DAYS and reliability_score < 50:
                # Recently active but bad history? 
                # User said: "newly active players should be given a chance"
                # If they were inactive before (causing bad history) but are active NOW...
                # We boost them slightly to get them out of "Bench" if they are trying.
                final_score = max(final_score, 50.0)

    return round(max(0, min(100, final_score)), 1)


def main():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    print("📊 Calculating Player Performance & Location...")
    players = db.get_all_active_players()
    guesser = TimezoneGuesser()

    for player in players:
        # 1. Trust Score
        history = db.get_player_history(player['player_tag'], limit=10)
        score = calculate_trust_score(player['town_hall_level'], history, player.get('last_active_time'))
        db.update_trust_score(player['player_tag'], score)
        
        # 2. Timezone Guessing & Activity Score
        # Fetch activity log
        activity_log = db.get_player_activity_history(player['player_tag'], limit=100) # Increased limit for better accuracy
        timestamps = [row['timestamp'] for row in activity_log]
        
        # Activity Score: Simple frequency metric (events per day over last 7 days?)
        # Let's just use raw count of events in last 7 days
        recent_events = [t for t in timestamps if (datetime.now() - t).days < 7]
        activity_score = len(recent_events)
        
        tz, country, conf, time_label = guesser.guess_timezone(timestamps)
        if tz:
            db.update_player_timezone(player['player_tag'], tz, country, conf, time_label, activity_score)
            print(f"Updated {player['name']}: {score}, {country}, {time_label}, Act:{activity_score}")
        else:
             # Even if no timezone, save activity score
            db.update_player_timezone(player['player_tag'], None, None, 0, None, activity_score)
            print(f"Updated {player['name']}: {score} (No Loc), Act:{activity_score}")

    db.close()


if __name__ == "__main__":
    main()