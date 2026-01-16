from flask import Blueprint, render_template, request
from config import Config
from Utils.sqlManager import SQLManager
from Utils.war_strategy import get_war_recommendations

main = Blueprint('main', __name__)


def get_status(player, wars_played):
    if not player['is_in_clan']: return "LEFT", "status-left"
    score = player.get('trust_score') or 50
    if wars_played == 0: return "NEW", "status-new"
    if score >= 80:
        return "ROSTER", "status-war"
    elif score >= 50:
        return "RISKY", "status-risky"
    else:
        return "BENCH", "status-bench"


@main.route('/')
def index():
    return render_template('index.html')


@main.route('/roster')
def roster():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    players = db.get_full_roster_including_leavers()
    roster_data = []

    for p in players:
        history = db.get_player_history(p['player_tag'], limit=10)
        total_wars = len(history)
        attacks_used = sum(w['attacks_used'] for w in history)
        
        attacks_possible = 0
        for w in history:
            w_type = w.get('war_type', 'regular')
            if w_type and w_type.lower() == 'cwl':
                attacks_possible += 1
            else:
                attacks_possible += 2
                
        participation = f"{attacks_used}/{attacks_possible}" if total_wars > 0 else "N/A"

        status_text, status_class = get_status(p, total_wars)
        clean_tag = p['player_tag'].replace("#", "")
        deep_link = f"/player/{clean_tag}"

        roster_data.append({
            'name': p['name'], 'th': p['town_hall_level'], 'tag': p['player_tag'],
            'score': round(p.get('trust_score', 50), 1),
            'participation': participation,
            'donated': p.get('last_known_donations', 0),
            'received': p.get('last_known_received', 0),
            'activity_score': p.get('activity_score', 0),
            'total_wars': total_wars, 'status': status_text, 'status_class': status_class,
            'link': deep_link, 'is_in_clan': p['is_in_clan']
        })
    db.close()
    
    # Sorting Logic
    sort_by = request.args.get('sort', 'trust') # Default to Trust Score
    
    if sort_by == 'th':
        roster_data.sort(key=lambda x: (x['is_in_clan'], x['th'], x['score']), reverse=True)
    elif sort_by == 'donations':
        roster_data.sort(key=lambda x: (x['is_in_clan'], x['donated']), reverse=True)
    elif sort_by == 'activity':
        roster_data.sort(key=lambda x: (x['is_in_clan'], x['activity_score']), reverse=True)
    else: # 'trust' or default
        roster_data.sort(key=lambda x: (x['is_in_clan'], x['score']), reverse=True)

    return render_template('roster.html', players=roster_data, current_sort=sort_by)


@main.route('/war')
def war_room():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    active_war = db.get_active_war()
    if not active_war:
        return render_template('war_room.html', active=False)

    our_team, enemy_team = db.get_full_war_map(active_war['war_id'])
    
    # Calculate Context
    import datetime
    now = datetime.datetime.utcnow()
    # active_war['end_time'] is likely a datetime object from SQLManager or string. 
    # SQLManager usually returns datetime. Let's assume it is.
    # If it's a string, we might need parsing. But based on previous files, it seems to be datetime.
    
    hours_left = 24
    if active_war.get('end_time'):
        end_time = active_war['end_time']
        if isinstance(end_time, str):
             # Fallback if string (though it shouldn't be with mysql connector usually)
             try:
                 end_time = datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
             except:
                 pass
        
        if isinstance(end_time, datetime.datetime):
            diff = end_time - now
            hours_left = diff.total_seconds() / 3600

    war_context = {
        'hours_left': hours_left,
        'score_diff': 0,
        'war_type': active_war.get('war_type', 'regular')
    }

    # Calculate Triple Rate for each player
    for p in our_team:
        triples = p.get('total_triples', 0)
        attacks = p.get('total_attacks', 0)
        p['triple_rate'] = triples / attacks if attacks > 0 else 0.30 # Default to 30% if no data

    recommendations = get_war_recommendations(our_team, enemy_team, war_context)
    db.close()

    return render_template('war_room.html', active=True, war_info=active_war, strategies=recommendations)


@main.route('/player/<path:tag>')
def player_profile(tag):
    # Ensure tag has hash
    if not tag.startswith('#'):
        tag = f"#{tag}"
    
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    player = db.get_player(tag)
    
    if not player:
        return "Player not found", 404

    # Fetch Data
    war_stats = db.get_player_war_stats(tag)
    activity_log = db.get_player_activity_history(tag, limit=250)
    history = db.get_player_history(tag, limit=100, include_active=True)
    
    db.close()
    
    # Fetch granular attacks
    raw_attacks = db.get_player_attacks(tag)
    
    # Organize attacks by war_id for easy lookup in the template
    attacks_by_war = {}
    for attack in raw_attacks:
        war_id = attack['war_id']
        if war_id not in attacks_by_war:
            attacks_by_war[war_id] = []
        attacks_by_war[war_id].append(attack)

    # Process Activity Data for Chart
    # 1. Activity Clock (Hours)
    activity_hours = [0] * 24
    
    # 2. Donation History (Date -> Value)
    donation_dates = []
    donation_values = []
    
    for log in activity_log:
        # Clock
        hour = log['timestamp'].hour
        activity_hours[hour] += 1
        
        # Donation History (Only if it's a donation event)
        if log['activity_type'] == 'donation' and log.get('value'):
            donation_dates.append(log['timestamp'].strftime('%m-%d'))
            donation_values.append(log['value'])

    # Reverse to show oldest to newest
    donation_dates.reverse()
    donation_values.reverse()

    # 3. War Performance Trend
    war_dates = []
    war_stars = []
    war_destruction = []
    
    # History is already sorted DESC (newest first), so reverse for chart
    for war in reversed(history):
        war_dates.append(war['start_time'].strftime('%m-%d'))
        war_stars.append(war['stars'])
        war_destruction.append(war['destruction_percentage'])

    return render_template('player_profile.html', 
                           player=player, 
                           war_stats=war_stats, 
                           activity_hours=activity_hours,
                           history=history,
                           attacks_by_war=attacks_by_war,
                           donation_dates=donation_dates,
                           donation_values=donation_values,
                           war_dates=war_dates,
                           war_stars=war_stars,
                           war_destruction=war_destruction)


@main.route('/stats')
def clan_stats():
    db = SQLManager(Config.DB_HOST, Config.DB_USER, Config.DB_PASSWORD, Config.DB_NAME)
    
    # 1. War History & Trend
    history = db.get_clan_war_history_stats(limit=20)
    
    # Process for Trend Chart (Reverse to show oldest -> newest)
    trend_dates = []
    trend_stars = []
    trend_dest = []
    
    for war in reversed(history):
        trend_dates.append(war['start_time'].strftime('%m-%d'))
        # Use Avg Stars (rounded) for smoother trend across CWL/Regular
        val = war['avg_stars'] or 0
        trend_stars.append(float(round(val, 2)))
        trend_dest.append(float(war['avg_destruction'] or 0))
        
    # 2. Activity Clock
    activity_data = db.get_clan_activity_distribution()
    
    # 3. Win/Loss Ratio
    win_loss = db.get_clan_win_loss_ratio(limit=50)
    
    db.close()
    
    return render_template('clan_stats.html',
                           history=history,
                           trend_dates=trend_dates,
                           trend_stars=trend_stars,
                           trend_dest=trend_dest,
                           activity_data=activity_data,
                           win_loss=win_loss)