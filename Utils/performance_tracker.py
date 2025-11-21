from config import Config
from sqlManager import SQLManager


def calculate_trust_score(player_th, history):
    """
    The Algorithm (Updated for Strategic Value):
    - Reliability (50%): Consistency is king.
    - Skill (30%): Star performance.
    - Power (20%): Town Hall level (Higher TH = More value).
    - Penalties: High THs get hammered for missing attacks.
    """

    # 1. Power Score (20% of total)
    # We assume TH17 is max. A TH17 gets full 100 points for this category.
    # A TH9 gets ~50 points. This gives high players a natural boost.
    MAX_TH = 17
    power_score = (player_th / MAX_TH) * 100

    if not history:
        # New players get a neutral reliability/skill score (50)
        # but still get their Power Score.
        return round((50 * 0.8) + (power_score * 0.2), 1)

    # 2. Aggregate Data
    total_wars = len(history)
    total_possible_attacks = total_wars * 2

    attacks_made = sum(row['attacks_used'] for row in history)
    total_stars = sum(row['stars'] for row in history)

    # 3. Reliability Score (0-100)
    reliability_score = (attacks_made / total_possible_attacks) * 100

    # 4. Skill Score (0-100)
    # Avg stars per war (max 6)
    avg_stars = total_stars / total_wars
    skill_score = (avg_stars / 6) * 100

    # 5. Final Weighted Score
    # Reliability (50%) + Skill (30%) + Power (20%)
    final_score = (reliability_score * 0.50) + (skill_score * 0.30) + (power_score * 0.20)

    # 6. The "Elite Flake" Penalty
    # If you are TH13+ and missed an attack, you lose massive points.
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
    ranked_roster = []

    for player in players:
        # Get last 10 wars
        history = db.get_player_history(player['player_tag'], limit=10)

        score = calculate_trust_score(player['town_hall_level'], history)

        # Save to DB
        db.update_trust_score(player['player_tag'], score)

        ranked_roster.append({
            'name': player['name'],
            'th': player['town_hall_level'],
            'score': score,
            'wars': len(history)
        })

    # Sort by Score
    ranked_roster.sort(key=lambda x: x['score'], reverse=True)

    print("\n🏆 CLAN WAR DRAFT LIST 🏆")
    print(f"{'Rank':<5} {'Name':<15} {'TH':<5} {'Score':<10} {'Status'}")
    print("-" * 50)

    for i, p in enumerate(ranked_roster, 1):
        status = "✅ WAR"
        if p['score'] < 40:
            status = "❌ BENCH"
        elif p['score'] < 70:
            status = "⚠️ RISKY"

        if p['wars'] == 0: status = "🆕 NEW"

        print(f"#{i:<4} {p['name']:<15} {p['th']:<5} {p['score']:<10} {status}")

    db.close()


if __name__ == "__main__":
    main()