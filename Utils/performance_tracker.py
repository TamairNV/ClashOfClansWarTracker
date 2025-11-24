
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config
from sqlManager import SQLManager


def calculate_trust_score(player_th, history):
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
    # ==========================================

    # 1. Power Score Calculation
    power_score = (player_th / MAX_TH) * 100

    # Handle players with NO history
    if not history:
        # Assume average (50) for skill/reliability, use actual power
        # Logic: (50 * 80%) + (Power * 20%)
        base_weight = W_RELIABILITY + W_SKILL
        return round((50 * base_weight) + (power_score * W_POWER), 1)

    # 2. Aggregate Data
    total_wars = len(history)
    total_possible_attacks = total_wars * 2
    attacks_made = sum(row['attacks_used'] for row in history)
    total_stars = sum(row['stars'] for row in history)

    # 3. Reliability Score (0-100)
    reliability_score = (attacks_made / total_possible_attacks) * 100

    # 4. Skill Score (0-100)
    avg_stars = total_stars / total_wars
    skill_score = (avg_stars / 6) * 100

    # 5. Final Weighted Score
    final_score = (reliability_score * W_RELIABILITY) + \
                  (skill_score * W_SKILL) + \
                  (power_score * W_POWER)

    # --- SPECIAL RULES ---

    # New Player Boost (Protect good recruits from low sample size)
    if total_wars <= NEW_PLAYER_WARS and attacks_made == total_possible_attacks:
        final_score = max(final_score, NEW_PLAYER_BOOST)

    # Elite Flake Penalty (Punish high THs who miss attacks)
    if player_th >= HIGH_TH_THRESHOLD:
        missed_attacks = total_possible_attacks - attacks_made
        if missed_attacks > 0:
            penalty = missed_attacks * PENALTY_PER_MISS
            final_score -= penalty

    return round(max(0, min(100, final_score)), 1)


def main():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    print("📊 Calculating Player Performance...")
    players = db.get_all_active_players()

    for player in players:
        history = db.get_player_history(player['player_tag'], limit=10)
        score = calculate_trust_score(player['town_hall_level'], history)
        db.update_trust_score(player['player_tag'], score)
        print(f"Updated {player['name']}: {score}")

    db.close()


if __name__ == "__main__":
    main()