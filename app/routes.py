from flask import Blueprint, render_template
from config import Config
from Utils.sqlManager import SQLManager
from Utils.war_strategy import get_war_recommendations

main = Blueprint('main', __name__)


def get_status(player, wars_played):
    if not player['is_in_clan']: return "LEFT", "status-left"
    score = player.get('trust_score', 50)
    if wars_played == 0: return "NEW", "status-new"
    if score >= 80:
        return "ROSTER", "status-war"
    elif score >= 50:
        return "RISKY", "status-risky"
    else:
        return "BENCH", "status-bench"


@main.route('/')
def roster():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    players = db.get_full_roster_including_leavers()
    roster_data = []

    for p in players:
        history = db.get_player_history(p['player_tag'], limit=10)
        total_wars = len(history)
        attacks_used = sum(w['attacks_used'] for w in history)
        attacks_possible = total_wars * 2
        participation = f"{attacks_used}/{attacks_possible}" if total_wars > 0 else "N/A"

        status_text, status_class = get_status(p, total_wars)
        clean_tag = p['player_tag'].replace("#", "")
        deep_link = f"clashofclans://action=OpenPlayerProfile&tag=%23{clean_tag}"

        roster_data.append({
            'name': p['name'], 'th': p['town_hall_level'], 'tag': p['player_tag'],
            'score': round(p.get('trust_score', 50), 1),
            'participation': participation,
            'donated': p.get('last_known_donations', 0),
            'received': p.get('last_known_received', 0),
            'total_wars': total_wars, 'status': status_text, 'status_class': status_class,
            'link': deep_link, 'is_in_clan': p['is_in_clan']
        })
    db.close()
    roster_data.sort(key=lambda x: (x['is_in_clan'], x['score']), reverse=True)
    return render_template('roster.html', players=roster_data)


@main.route('/war')
def war_room():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    active_war = db.get_active_war()
    if not active_war:
        return render_template('war_room.html', active=False)

    our_team, enemy_team = db.get_full_war_map(active_war['war_id'])
    recommendations = get_war_recommendations(our_team, enemy_team)
    db.close()

    return render_template('war_room.html', active=True, war_info=active_war, strategies=recommendations)