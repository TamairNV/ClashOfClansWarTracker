from config import Config
from sqlManager import SQLManager
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def calculate_trust_score(player_th, history):
    MAX_TH = 18
    power_score = (player_th / MAX_TH) * 100

    if not history:
        return round((50 * 0.8) + (power_score * 0.2), 1)

    total_wars = len(history)
    total_possible_attacks = total_wars * 2
    attacks_made = sum(row['attacks_used'] for row in history)
    total_stars = sum(row['stars'] for row in history)

    reliability_score = (attacks_made / total_possible_attacks) * 100
    avg_stars = total_stars / total_wars
    skill_score = (avg_stars / 6) * 100

    final_score = (reliability_score * 0.50) + (skill_score * 0.30) + (power_score * 0.20)

    # New Player Boost
    if total_wars <= 5 and attacks_made == total_possible_attacks:
        final_score = max(final_score, 82.0)

    if player_th >= 13:
        missed_attacks = total_possible_attacks - attacks_made
        if missed_attacks > 0:
            penalty = missed_attacks * 15
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