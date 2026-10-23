"""War insights: trend + benchmark analytics for the /insights and /compare pages.

Two sources:
  * clash_manager - our clan's detailed war log (wars, war_attacks, war_defenses, war_performance)
  * clash_db      - the harvester's multi-clan data. Its tables contain the same war many
                    times over (one ClanWar row per poll), so everything here is de-duplicated
                    by (clan pair, startTime) before use.
"""
import datetime
import math
import time
from collections import defaultdict

import pymysql
from pymysql.cursors import DictCursor

from config import Config

HARVEST_DB = "clash_db"

TRACKED_CLANS = [
    "#9PGQPGL", "#8GGPQLPU", "#22RUUC2JC", "#29U9C0GLC", "#2LGGP2G82", "#2RG22YYLL",
    "#2YQQQ0JUP", "#2LJJJ9LQ0", "#2QUY89R2", "#2Y8G98UPU", "#2G2VRCRPQ", "#8U9802J0",
    "#8RGY9RCC", "#RVJUG0Y2", "#G20GG9LJ", "#G2G2JULR", "#2GPLUCRLR", "#JVUJR2QC",
    "#2GLC0G2JR", "#22G0JJR8", "#2RVGUQ0R2", "#JCCYQPYL", "#2Y09JUL9R", "#CPVJYJQV",
    "#2G28J89UQ", "#8GR2GRJR", "#2CC0CJVC", "#2YVJU0GCU",
]

_cache = {}


def _cached(key, ttl):
    def deco(fn):
        def wrapper():
            hit = _cache.get(key)
            if hit and time.time() - hit[0] < ttl:
                return hit[1]
            value = fn()
            _cache[key] = (time.time(), value)
            return value
        return wrapper
    return deco


def _connect(db_name):
    return pymysql.connect(host=Config.DB_HOST, user=Config.DB_USER, password=Config.DB_PASSWORD,
                           database=db_name, cursorclass=DictCursor, autocommit=True)


def _query(conn, sql, args=None):
    with conn.cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchall()


def _pct(part, whole):
    return round(100.0 * part / whole, 1) if whole else None


def _avg(values):
    return round(sum(values) / len(values), 2) if values else None


def _std(values):
    if len(values) < 2:
        return None
    m = sum(values) / len(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def _attack_summary(stars):
    """stars: list of ints -> dict of count / avg / triple% / zero%."""
    n = len(stars)
    return {
        'attacks': n,
        'avg_stars': _avg(stars),
        'triple_rate': _pct(sum(1 for s in stars if s == 3), n),
        'fail_rate': _pct(sum(1 for s in stars if s <= 1), n),
    }


# ---------------------------------------------------------------------------
# Our clan (clash_manager)
# ---------------------------------------------------------------------------

def _decide(our_stars, their_stars, our_dest, their_dest):
    if our_stars != their_stars:
        return 'win' if our_stars > their_stars else 'lose'
    if abs(our_dest - their_dest) > 0.01:
        return 'win' if our_dest > their_dest else 'lose'
    return 'draw'


@_cached('clan_insights', ttl=600)
def clan_insights():
    conn = _connect(Config.DB_NAME)
    try:
        wars = _query(conn, """
            SELECT war_id, war_type, state, start_time, end_time, result, opponent_name
            FROM wars WHERE state = 'warEnded' AND war_type IN ('regular', 'cwl')
            ORDER BY start_time""")
        attacks = _query(conn, """
            SELECT a.war_id, a.player_tag, a.stars, a.destruction, a.duration, a.attack_order,
                   a.defender_tag, a.defender_th, p.town_hall_at_time AS attacker_th
            FROM war_attacks a
            LEFT JOIN war_performance p ON p.war_id = a.war_id AND p.player_tag = a.player_tag""")
        perf = _query(conn, """
            SELECT war_id, player_tag, town_hall_at_time, attacks_used, defense_stars FROM war_performance""")
        players = {p['player_tag']: p for p in _query(conn, """
            SELECT player_tag, name, town_hall_level, is_in_clan FROM players""")}
        opponents = _query(conn, "SELECT war_id, town_hall_level, stars, destruction FROM war_opponents")
    finally:
        conn.close()

    war_by_id = {w['war_id']: w for w in wars}
    atk_by_war = defaultdict(list)
    for a in attacks:
        if a['war_id'] in war_by_id:
            atk_by_war[a['war_id']].append(a)
    perf_by_war = defaultdict(list)
    for p in perf:
        if p['war_id'] in war_by_id:
            perf_by_war[p['war_id']].append(p)
    opp_by_war = defaultdict(list)
    for o in opponents:
        opp_by_war[o['war_id']].append(o)

    # --- per war score. war_opponents holds our best hit on each enemy base and
    # war_performance.defense_stars the best enemy hit on each of ours; war_defenses is
    # incomplete so it is not used for totals. ---
    war_rows = []
    for w in wars:
        atks, roster, opps = atk_by_war[w['war_id']], perf_by_war[w['war_id']], opp_by_war[w['war_id']]
        size = len(roster)
        if not size or not atks:
            continue
        our_stars = sum(o['stars'] or 0 for o in opps)
        their_stars = sum(p['defense_stars'] or 0 for p in roster)
        our_dest = sum(o['destruction'] or 0 for o in opps) / len(opps) if opps else 0
        result = w['result']
        if not result and our_stars != their_stars:
            result = 'win' if our_stars > their_stars else 'lose'
        per_player = 1 if w['war_type'] == 'cwl' else 2
        possible = size * per_player
        our_ths = [p['town_hall_at_time'] for p in roster if p['town_hall_at_time']]
        opp_ths = [o['town_hall_level'] for o in opps if o['town_hall_level']]
        used = sum(min(p['attacks_used'] or 0, per_player) for p in roster)
        war_rows.append({
            'war_id': w['war_id'], 'date': w['start_time'], 'type': w['war_type'], 'size': size,
            'opponent': w['opponent_name'],
            'our_stars': our_stars, 'their_stars': their_stars,
            'our_dest': round(our_dest, 1), 'result': result,
            'attacks_used': used, 'attacks_possible': possible,
            'triples': sum(1 for a in atks if a['stars'] == 3), 'attack_count': len(atks),
            'star_sum': sum(a['stars'] for a in atks),
            'our_avg_th': _avg(our_ths), 'opp_avg_th': _avg(opp_ths),
        })

    # --- KPIs ---
    used = sum(r['attacks_used'] for r in war_rows)
    possible = sum(r['attacks_possible'] for r in war_rows)
    all_stars = [a['stars'] for wid in war_by_id for a in atk_by_war[wid]]
    kpis = {
        'wars': len(war_rows),
        'win_rate': _pct(sum(1 for r in war_rows if r['result'] == 'win'), len(war_rows)),
        'wins': sum(1 for r in war_rows if r['result'] == 'win'),
        'draws': sum(1 for r in war_rows if r['result'] == 'draw'),
        'losses': sum(1 for r in war_rows if r['result'] == 'lose'),
        'usage': _pct(used, possible),
        **_attack_summary(all_stars),
    }

    # --- monthly trend ---
    months = defaultdict(list)
    for r in war_rows:
        months[r['date'].strftime('%Y-%m')].append(r)
    trend = []
    for m in sorted(months):
        rs = months[m]
        n_atk = sum(r['attack_count'] for r in rs)
        trend.append({
            'month': m, 'wars': len(rs),
            'win_rate': _pct(sum(1 for r in rs if r['result'] == 'win'), len(rs)),
            'draw_rate': _pct(sum(1 for r in rs if r['result'] == 'draw'), len(rs)),
            'triple_rate': _pct(sum(r['triples'] for r in rs), n_atk),
            'avg_stars': round(sum(r['star_sum'] for r in rs) / n_atk, 2) if n_atk else None,
            'usage': _pct(sum(r['attacks_used'] for r in rs), sum(r['attacks_possible'] for r in rs)),
        })

    # --- war type split ---
    by_type = {}
    for t in ('regular', 'cwl'):
        rs = [r for r in war_rows if r['type'] == t]
        stars = [a['stars'] for r in rs for a in atk_by_war[r['war_id']]]
        by_type[t] = {
            'wars': len(rs),
            'win_rate': _pct(sum(1 for r in rs if r['result'] == 'win'), len(rs)),
            'draw_rate': _pct(sum(1 for r in rs if r['result'] == 'draw'), len(rs)),
            'usage': _pct(sum(r['attacks_used'] for r in rs), sum(r['attacks_possible'] for r in rs)),
            **_attack_summary(stars),
        }

    # --- hit up / hit down (attacker TH - defender TH) ---
    scored = [a for wid in war_by_id for a in atk_by_war[wid] if a['attacker_th'] and a['defender_th']]
    th_diff = _th_diff_table([(a['attacker_th'], a['defender_th'], a['stars']) for a in scored])
    th_matrix = _th_matrix([(a['attacker_th'], a['defender_th'], a['stars']) for a in scored])

    # --- first vs second hit ---
    order_split = {}
    for o in (1, 2):
        order_split[o] = _attack_summary([a['stars'] for a in scored if a['attack_order'] == o])

    # --- attack duration vs outcome ---
    buckets = [(0, 60, '<1 min'), (60, 120, '1-2 min'), (120, 150, '2-2.5 min'), (150, 181, '2.5-3 min')]
    duration = []
    for lo, hi, label in buckets:
        s = [a['stars'] for a in scored if a['duration'] is not None and lo <= a['duration'] < hi]
        duration.append({'label': label, **_attack_summary(s)})

    # --- players: form, consistency, reliability ---
    recent_ids = {r['war_id'] for r in war_rows[-12:]}
    p_stars, p_recent, p_used, p_possible, p_wars = (defaultdict(list), defaultdict(list),
                                                     defaultdict(int), defaultdict(int), defaultdict(int))
    for r in war_rows:
        per_player = 1 if r['type'] == 'cwl' else 2
        for p in perf_by_war[r['war_id']]:
            p_used[p['player_tag']] += min(p['attacks_used'] or 0, per_player)
            p_possible[p['player_tag']] += per_player
            p_wars[p['player_tag']] += 1
        for a in atk_by_war[r['war_id']]:
            p_stars[a['player_tag']].append(a['stars'])
            if r['war_id'] in recent_ids:
                p_recent[a['player_tag']].append(a['stars'])
    player_rows = []
    for tag, stars in p_stars.items():
        info = players.get(tag)
        if not info or not info['is_in_clan'] or len(stars) < 10:
            continue
        overall = _attack_summary(stars)
        recent = _attack_summary(p_recent[tag]) if len(p_recent[tag]) >= 4 else None
        sd = _std(stars)
        player_rows.append({
            'tag': tag, 'link': '/player/' + tag.replace('#', ''), 'name': info['name'],
            'th': info['town_hall_level'], 'wars': p_wars[tag],
            'usage': _pct(p_used[tag], p_possible[tag]),
            **overall,
            'recent_triple': recent['triple_rate'] if recent else None,
            'form': round(recent['triple_rate'] - overall['triple_rate'], 1) if recent else None,
            # 0-100: how tightly a player's results cluster (100 = same result every hit)
            'consistency': round(100 * (1 - min(sd / 1.5, 1)), 0) if sd is not None else None,
        })
    player_rows.sort(key=lambda p: (p['avg_stars'] or 0), reverse=True)

    # --- defenders: best enemy hit conceded per war ---
    d_stars = defaultdict(list)
    for r in war_rows:
        for p in perf_by_war[r['war_id']]:
            if p['defense_stars'] is not None:
                d_stars[p['player_tag']].append(p['defense_stars'])
    defenders = []
    for tag, stars in d_stars.items():
        info = players.get(tag)
        if not info or not info['is_in_clan'] or len(stars) < 8:
            continue
        defenders.append({'name': info['name'], 'th': info['town_hall_level'],
                          'link': '/player/' + tag.replace('#', ''),
                          'defenses': len(stars), 'avg_conceded': _avg(stars),
                          'held': _pct(sum(1 for s in stars if s < 3), len(stars))})
    defenders.sort(key=lambda d: d['avg_conceded'])

    # --- matchup strength: TH gap vs win rate ---
    strength = defaultdict(lambda: {'wars': 0, 'wins': 0})
    for r in war_rows:
        if r['our_avg_th'] is None or r['opp_avg_th'] is None:
            continue
        gap = r['our_avg_th'] - r['opp_avg_th']
        label = ('Opponent much stronger (>0.5 TH)' if gap < -0.5 else
                 'Opponent slightly stronger' if gap < -0.1 else
                 'Even' if gap <= 0.1 else
                 'We are slightly stronger' if gap <= 0.5 else 'We are much stronger (>0.5 TH)')
        strength[label]['wars'] += 1
        strength[label]['wins'] += r['result'] == 'win'
    order = ['Opponent much stronger (>0.5 TH)', 'Opponent slightly stronger', 'Even',
             'We are slightly stronger', 'We are much stronger (>0.5 TH)']
    matchup = [{'label': k, 'wars': strength[k]['wars'],
                'win_rate': _pct(strength[k]['wins'], strength[k]['wars'])} for k in order if strength[k]['wars']]

    cutoff = war_rows[-1]['date'] - datetime.timedelta(days=90) if war_rows else None
    recent_war_ids = {r['war_id'] for r in war_rows if cutoff and r['date'] >= cutoff}
    recent_th_rows = [(a['attacker_th'], a['defender_th'], a['stars']) for a in scored
                      if a['war_id'] in recent_war_ids]

    return {
        'recent_th_rows': recent_th_rows,
        'kpis': kpis, 'trend': trend, 'by_type': by_type, 'th_diff': th_diff, 'th_matrix': th_matrix,
        'order_split': order_split, 'duration': duration, 'players': player_rows,
        'defenders': defenders[:10], 'matchup': matchup, 'wars': war_rows,
        'first_war': war_rows[0]['date'] if war_rows else None,
    }


def _th_diff_table(rows):
    """rows: (attacker_th, defender_th, stars) -> list for hit-up/hit-down chart."""
    groups = defaultdict(list)
    for ath, dth, stars in rows:
        diff = max(-2, min(2, ath - dth))
        groups[diff].append(stars)
    labels = {-2: 'Hit up 2+', -1: 'Hit up 1', 0: 'Same TH', 1: 'Hit down 1', 2: 'Hit down 2+'}
    return [{'diff': d, 'label': labels[d], **_attack_summary(groups[d])} for d in sorted(groups)]


def _vs_expected(rows, expected):
    diffs = [s - expected[(a, d)] for a, d, s in rows if (a, d) in expected]
    return round(sum(diffs) / len(diffs), 3) if len(diffs) >= 20 else None


def _th_matrix(rows, min_attacks=8):
    cells = defaultdict(list)
    for ath, dth, stars in rows:
        cells[(ath, dth)].append(stars)
    ths = sorted({k[0] for k in cells} | {k[1] for k in cells}, reverse=True)
    ths = [t for t in ths if t >= 12]
    grid = []
    for ath in ths:
        row = []
        for dth in ths:
            s = cells.get((ath, dth), [])
            row.append(_attack_summary(s) if len(s) >= min_attacks else None)
        if any(row):
            grid.append({'th': ath, 'cells': row})
    return {'ths': ths, 'rows': grid, 'min_attacks': min_attacks}


# ---------------------------------------------------------------------------
# Benchmarks across the harvested clans (clash_db)
# ---------------------------------------------------------------------------

@_cached('benchmarks', ttl=6 * 3600)
def benchmarks():
    conn = _connect(HARVEST_DB)
    try:
        # One canonical id per real war (the harvester re-inserted each war on every poll).
        _query(conn, "DROP TEMPORARY TABLE IF EXISTS wmap")
        _query(conn, """
            CREATE TEMPORARY TABLE wmap (warID INT PRIMARY KEY, canon INT, KEY(canon)) AS
            SELECT cw.warID, k.canon FROM ClanWar cw
            JOIN (SELECT LEAST(clanTag1, clanTag2) a, GREATEST(clanTag1, clanTag2) b, startTime st,
                         MIN(warID) canon
                  FROM ClanWar GROUP BY a, b, st) k
              ON LEAST(cw.clanTag1, cw.clanTag2) = k.a AND GREATEST(cw.clanTag1, cw.clanTag2) = k.b
             AND cw.startTime = k.st""")
        wars = _query(conn, """
            SELECT cw.warID AS canon, cw.clanTag1, cw.clanTag2, cw.teamSize, cw.startTime
            FROM ClanWar cw WHERE cw.warID IN (SELECT DISTINCT canon FROM wmap)""")
        results = _query(conn, """
            SELECT m.canon, r.clanTag, MAX(r.totalStars) stars, MAX(r.totalDestruction) dest
            FROM WarResults r JOIN wmap m USING (warID) GROUP BY m.canon, r.clanTag""")
        roster = _query(conn, """
            SELECT m.canon, p.playerTag, MAX(p.clanTag) clanTag, MAX(p.townHallLevel) th
            FROM WarPlayer p JOIN wmap m USING (warID) GROUP BY m.canon, p.playerTag""")
        attacks = _query(conn, """
            SELECT m.canon, a.attackerTag, a.defenderTag, MAX(a.stars) stars
            FROM Attack a JOIN wmap m USING (warID) GROUP BY m.canon, a.attackerTag, a.defenderTag""")
        names = {c['tag']: c['name'] for c in _query(conn, "SELECT tag, name FROM Clan")}
    finally:
        conn.close()

    tracked = set(TRACKED_CLANS)
    who = {(r['canon'], r['playerTag']): (r['clanTag'], r['th']) for r in roster}
    res = defaultdict(dict)
    for r in results:
        res[r['canon']][r['clanTag']] = r

    clans = {t: {'tag': t, 'name': names.get(t, t), 'wars': 0, 'wins': 0, 'scored': 0,
                 'stars': [], 'ths': [], 'th_rows': []} for t in tracked}
    dates = [w['startTime'] for w in wars]
    for w in wars:
        for side, other in ((w['clanTag1'], w['clanTag2']), (w['clanTag2'], w['clanTag1'])):
            if side not in tracked:
                continue
            c = clans[side]
            c['wars'] += 1
            mine, theirs = res[w['canon']].get(side), res[w['canon']].get(other)
            if mine and theirs and (mine['stars'] or theirs['stars']):
                c['scored'] += 1
                c['wins'] += _decide(mine['stars'], theirs['stars'],
                                     float(mine['dest'] or 0), float(theirs['dest'] or 0)) == 'win'

    for (canon, tag), (clan_tag, th) in who.items():
        if clan_tag in clans and th:
            clans[clan_tag]['ths'].append(th)

    all_rows = []
    for a in attacks:
        att = who.get((a['canon'], a['attackerTag']))
        dfn = who.get((a['canon'], a['defenderTag']))
        if not att:
            continue
        if att[0] in clans:
            clans[att[0]]['stars'].append(a['stars'])
        if dfn and att[1] and dfn[1]:
            all_rows.append((att[1], dfn[1], a['stars']))
            if att[0] in clans:
                clans[att[0]]['th_rows'].append((att[1], dfn[1], a['stars']))

    # Expected stars for an attack = average result of every harvested attack with the
    # same attacker/defender TH pair. "Stars vs expected" then compares clans fairly
    # even when one clan has lower town halls than another.
    pair = defaultdict(list)
    for ath, dth, s in all_rows:
        pair[(ath, dth)].append(s)
    expected = {k: sum(v) / len(v) for k, v in pair.items() if len(v) >= 20}

    table = []
    for c in clans.values():
        if len(c['stars']) < 30:
            continue
        table.append({
            'tag': c['tag'], 'name': c['name'], 'ours': c['tag'] == Config.CLAN_TAG,
            'wars': c['wars'], 'scored': c['scored'],
            'win_rate': _pct(c['wins'], c['scored']) if c['scored'] >= 3 else None,
            'avg_th': _avg(c['ths']),
            'vs_expected': _vs_expected(c['th_rows'], expected),
            **_attack_summary(c['stars']),
        })
    table.sort(key=lambda r: r['avg_stars'] or 0, reverse=True)
    for i, r in enumerate(table, 1):
        r['rank'] = i

    # Star rate at same-TH by TH level: does the clan out-hit others on equal footing?
    same_th = defaultdict(list)
    for ath, dth, s in all_rows:
        if ath == dth:
            same_th[ath].append(s)
    same_th_rows = [{'th': t, **_attack_summary(v)} for t, v in sorted(same_th.items(), reverse=True)
                    if len(v) >= 30 and t >= 12]

    ours_from_log = clan_insights()
    return {
        'expected': expected,
        'ours_recent_vs_expected': _vs_expected(
            [(a, d, st) for a, d, st in ours_from_log['recent_th_rows']], expected),
        'clans': table, 'th_diff': _th_diff_table(all_rows), 'same_th': same_th_rows,
        'unique_wars': len(wars), 'attacks': len(attacks),
        'from': min(dates) if dates else None, 'to': max(dates) if dates else None,
    }


def headlines(d, b):
    """Plain-English takeaways for the top of the insights page."""
    out = []
    t = [m for m in d['trend'] if m['wars'] >= 5]
    if len(t) >= 6:
        early = [m['triple_rate'] for m in t[:3]]
        late = [m['triple_rate'] for m in t[-3:]]
        e, l = sum(early) / 3, sum(late) / 3
        word = 'up' if l > e else 'down'
        out.append(f"Triple rate is {word} from {e:.0f}% ({t[0]['month']} to {t[2]['month']}) "
                   f"to {l:.0f}% over the last three months.")
    reg, cwl = d['by_type'].get('regular'), d['by_type'].get('cwl')
    if reg and cwl and reg['usage'] and cwl['usage']:
        out.append(f"{100 - reg['usage']:.0f}% of regular-war attacks go unused, against "
                   f"{100 - cwl['usage']:.0f}% in CWL. Missed hits are the easiest stars to win back.")
    ours = {r['diff']: r for r in d['th_diff']}
    theirs = {r['diff']: r for r in b['th_diff']}
    if -1 in ours and -1 in theirs:
        o, x = ours[-1]['triple_rate'], theirs[-1]['triple_rate']
        cmp = 'better' if o > x else 'worse'
        out.append(f"Hitting up one TH, we triple {o:.0f}% of the time vs {x:.0f}% across all tracked clans ({cmp}).")
    dur = {r['label']: r for r in d['duration']}
    if dur.get('2.5-3 min') and dur.get('2-2.5 min'):
        out.append(f"Attacks that run into the last 30 seconds triple {dur['2.5-3 min']['triple_rate']:.0f}% "
                   f"of the time, vs {dur['2-2.5 min']['triple_rate']:.0f}% for ones finished by 2:30.")
    hot = [p for p in d['players'] if p['form'] is not None]
    if hot:
        p = max(hot, key=lambda p: p['form'])
        if p['form'] > 5:
            out.append(f"Best current form: {p['name']}, tripling {p['recent_triple']:.0f}% in the last "
                       f"12 wars (+{p['form']:.0f} points on their average).")
    ours_row = next((c for c in b['clans'] if c['ours']), None)
    if ours_row and ours_row['vs_expected'] is not None:
        ranked = sorted([c for c in b['clans'] if c['vs_expected'] is not None],
                        key=lambda c: c['vs_expected'], reverse=True)
        rank = ranked.index(ours_row) + 1
        out.append(f"Adjusted for town hall, we ranked {_ordinal(rank)} of {len(ranked)} tracked clans "
                   f"in the harvester data. See Benchmarks.")
    return out


def _ordinal(n):
    suffix = 'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"
