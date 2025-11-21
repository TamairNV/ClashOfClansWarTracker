from flask import Blueprint, render_template
from config import Config
from Utils.sqlManager import SQLManager
from Utils.war_strategy import get_war_recommendations

main_bp = Blueprint('main', __name__)


def get_status(score, wars_played):
    # Status tags without emojis
    if wars_played == 0:
        return "NEW", "status-new"
    if score >= 80:
        return "ROSTER", "status-war"
    elif score >= 50:
        return "RISKY", "status-risky"
    else:
        return "BENCH", "status-bench"


@main_bp.route('/')
def roster():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)

    players = db.get_all_active_players()
    roster_data = []

    for p in players:
        # 1. War Stats
        history = db.get_player_history(p['player_tag'], limit=10)
        total_wars = len(history)

        attacks_used = sum(w['attacks_used'] for w in history)
        attacks_possible = total_wars * 2

        participation = f"{attacks_used}/{attacks_possible}" if total_wars > 0 else "N/A"

        # 2. Activity Stats (Donations)
        donated = p.get('last_known_donations', 0)
        received = p.get('last_known_received', 0)

        # 3. Score & Status
        score = p.get('trust_score', 50)
        status_text, status_class = get_status(score, total_wars)

        clean_tag = p['player_tag'].replace("#", "")
        deep_link = f"clashofclans://action=OpenPlayerProfile&tag=%23{clean_tag}"

        roster_data.append({
            'name': p['name'],
            'th': p['town_hall_level'],
            'tag': p['player_tag'],
            'score': round(score, 1),
            'participation': participation,
            'donated': donated,
            'received': received,
            'total_wars': total_wars,
            'status': status_text,
            'status_class': status_class,
            'link': deep_link
        })

    db.close()

    # Sort by Score Descending
    roster_data.sort(key=lambda x: x['score'], reverse=True)

    return render_template('roster.html', players=roster_data)


@main_bp.route('/war')
def war_room():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)

    active_war = db.get_active_war()
    if not active_war:
        return render_template('war_room.html', active=False)

    our_team, enemy_team = db.get_full_war_map(active_war['war_id'])

    recommendations = get_war_recommendations(our_team, enemy_team)

    db.close()

    return render_template('war_room.html',
                           active=True,
                           war_info=active_war,
                           strategies=recommendations)