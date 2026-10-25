"""Clan health from the harvester's player history (clash_db.PlayerSnapshot / ActivitySnapshot).

PlayerSnapshot has ~4M rows, so a full pass takes the better part of a minute. The result is
written to cache/history.json and rebuilt in a background thread when it is older than
CACHE_HOURS, so page loads never wait on it.
"""
import bisect
import json
import os
import threading
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta

import pymysql
import pymysql.cursors

from config import Config
from Utils.insights import HARVEST_DB, TRACKED_CLANS

CACHE_HOURS = 12
MAX_GAP = timedelta(days=2)
CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache', 'history.json')

_lock = threading.Lock()
_building = False


def get_history():
    """Returns (data or None, building) without ever blocking on a rebuild."""
    data = None
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                data = json.load(f)
        except (OSError, ValueError):
            data = None
    stale = data is None or time.time() - os.path.getmtime(CACHE_FILE) > CACHE_HOURS * 3600
    if stale:
        _start_rebuild()
    return data, _building


def _start_rebuild():
    global _building
    with _lock:
        if _building:
            return
        _building = True

    def run():
        global _building
        try:
            data = build_history()
            os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
            tmp = CACHE_FILE + '.tmp'
            with open(tmp, 'w') as f:
                json.dump(data, f, default=str)
            os.replace(tmp, CACHE_FILE)
        except Exception as e:
            print(f"!! History rebuild failed: {e}")
        finally:
            _building = False

    threading.Thread(target=run, daemon=True).start()


def _connect():
    return pymysql.connect(host=Config.DB_HOST, user=Config.DB_USER, password=Config.DB_PASSWORD,
                           database=HARVEST_DB, cursorclass=pymysql.cursors.SSCursor)


def _rank(rows, key, reverse=True):
    ranked = sorted([r for r in rows if r.get(key) is not None], key=lambda r: r[key], reverse=reverse)
    for i, r in enumerate(ranked, 1):
        r[key + '_rank'] = i


def build_history():
    tracked = set(TRACKED_CLANS)
    conn = _connect()
    try:
        names = {}
        with conn.cursor() as cur:
            cur.execute("SELECT tag, name FROM Clan")
            names = dict(cur.fetchall())

        # --- one pass over every snapshot, keeping only the rows where something changed ---
        stints = defaultdict(list)       # player -> [(start, end, clan)]
        clan_days = Counter()            # clan -> member-days observed
        gains = defaultdict(Counter)     # clan -> war_stars / donations / th_ups / capital
        weekly_stars = defaultdict(Counter)   # clan -> week -> war stars gained
        weekly_days = defaultdict(Counter)    # clan -> week -> member-days
        transfers = Counter()            # (from clan, to clan)
        leaves = Counter()
        joins = Counter()
        span = [None, None]
        seen_dates = set()

        def close(stint_list, start, end, clan):
            stint_list.append((start, end, clan))

        with conn.cursor() as cur:
            cur.execute("""
                SELECT playerTag, time, clanTag, townHallLevel, warStars, donations, clanCapitalContributions
                FROM PlayerSnapshot ORDER BY playerTag, time""")
            prev = None
            stint_start = None
            for tag, t, clan, th, stars, dons, cap in cur:
                if span[0] is None or t < span[0]:
                    span[0] = t
                if span[1] is None or t > span[1]:
                    span[1] = t
                if prev is None or prev[0] != tag:
                    seen_dates.add(t.date())
                    if prev is not None:
                        close(stints[prev[0]], stint_start, prev[1], prev[2])
                    prev, stint_start = (tag, t, clan, th, stars, dons, cap), t
                    continue
                _, pt, pclan, pth, pstars, pdons, pcap = prev
                seen_dates.add(t.date())
                if t - pt > MAX_GAP:
                    # The harvester was down (e.g. Mar-Oct 2026): don't count the gap as
                    # membership, and don't credit gains made while nobody was watching.
                    close(stints[tag], stint_start, pt, pclan)
                    stint_start = t
                    if clan != pclan and clan in tracked:
                        joins[clan] += 1
                elif clan != pclan:
                    close(stints[tag], stint_start, t, pclan)
                    stint_start = t
                    if pclan in tracked:
                        leaves[pclan] += 1
                    if clan in tracked:
                        joins[clan] += 1
                    if pclan and clan and (pclan in tracked or clan in tracked):
                        transfers[(pclan, clan)] += 1
                elif clan in tracked:
                    week = t.strftime('%G-W%V')
                    dt = (t - pt).total_seconds() / 86400
                    clan_days[clan] += dt
                    weekly_days[clan][week] += dt
                    g = gains[clan]
                    if stars and pstars and stars > pstars:
                        g['war_stars'] += stars - pstars
                        weekly_stars[clan][week] += stars - pstars
                    if dons is not None and pdons is not None:
                        # Donations reset each season; a drop means a new season started.
                        g['donations'] += dons - pdons if dons >= pdons else dons
                    if th and pth and th > pth:
                        g['th_ups'] += th - pth
                    if cap and pcap and cap > pcap:
                        g['capital'] += cap - pcap
                prev = (tag, t, clan, th, stars, dons, cap)
            if prev is not None:
                close(stints[prev[0]], stint_start, prev[1], prev[2])

        # --- activity pings, attributed to the clan the player was in at the time ---
        starts = {p: [s[0] for s in v] for p, v in stints.items()}
        active_days = defaultdict(set)   # (clan, player) -> dates
        hours = defaultdict(Counter)     # clan -> hour -> pings
        with conn.cursor() as cur:
            cur.execute("SELECT playerTag, time FROM ActivitySnapshot ORDER BY playerTag, time")
            last = None
            for tag, t in cur:
                if tag not in stints:
                    continue
                i = bisect.bisect_right(starts[tag], t) - 1
                if i < 0:
                    continue
                start, end, clan = stints[tag][i]
                if clan not in tracked or t > end + timedelta(hours=2):
                    continue
                # The old harvester logged the same action on every check for up to an hour,
                # so count at most one ping per player per hour.
                key = (tag, t.date(), t.hour)
                if key == last:
                    continue
                last = key
                hours[clan][t.hour] += 1
                active_days[(clan, tag)].add(t.date())
    finally:
        conn.close()

    # --- per clan summary ---
    member_obs_days = defaultdict(list)  # clan -> [(player, days in clan)]
    for tag, sts in stints.items():
        per_clan = Counter()
        for s, e, c in sts:
            if c in tracked:
                per_clan[c] += max((e - s).total_seconds() / 86400, 0)
        for c, d in per_clan.items():
            member_obs_days[c].append((tag, d))

    clans = []
    for c in tracked:
        days = clan_days[c]
        if days < 60:
            continue
        g = gains[c]
        members = [(p, d) for p, d in member_obs_days[c] if d >= 3]
        active_share = [min(len(active_days[(c, p)]) / d, 1.0) for p, d in members]
        observed = len(seen_dates) or 1
        roster = days / observed
        clans.append({
            'tag': c, 'name': names.get(c, c), 'ours': c == Config.CLAN_TAG,
            'roster': round(roster, 1),
            'war_stars_week': round(g['war_stars'] / days * 7, 2),
            'donations_day': round(g['donations'] / days, 1),
            'th_ups_month': round(g['th_ups'] / days * 30, 3),
            'capital_day': round(g['capital'] / days),
            'churn_month': round(100 * leaves[c] / roster / observed * 30, 1) if roster else None,
            'active_days': round(100 * sum(active_share) / len(active_share), 1) if active_share else None,
            'joins': joins[c], 'leaves': leaves[c],
        })
    for key in ('war_stars_week', 'donations_day', 'th_ups_month', 'capital_day', 'active_days'):
        _rank(clans, key)
    _rank(clans, 'churn_month', reverse=False)
    clans.sort(key=lambda r: r['war_stars_week'], reverse=True)

    # --- weekly war stars per member: ours vs the rest ---
    weeks = sorted({w for c in weekly_days for w in weekly_days[c]})
    weekly = []
    us = Config.CLAN_TAG
    for w in weeks:
        others = [c for c in tracked if c != us and weekly_days[c][w] >= 30]
        if weekly_days[us][w] < 30 or len(others) < 5:
            continue
        weekly.append({
            'week': w,
            'ours': round(weekly_stars[us][w] / weekly_days[us][w] * 7, 2),
            'field': round(sum(weekly_stars[c][w] for c in others) /
                           sum(weekly_days[c][w] for c in others) * 7, 2),
        })

    # --- activity by hour (share of each clan's pings) ---
    def share(counter):
        total = sum(counter.values()) or 1
        return [round(100 * counter.get(h, 0) / total, 2) for h in range(24)]
    field_hours = Counter()
    for c in tracked:
        if c != Config.CLAN_TAG:
            field_hours.update(hours[c])

    # --- transfers between tracked clans and the rest ---
    moves = []
    for (a, b), n in transfers.most_common():
        if a == b:
            continue
        moves.append({'from': names.get(a, a), 'to': names.get(b, b), 'count': n,
                      'from_tracked': a in tracked, 'to_tracked': b in tracked,
                      'ours': Config.CLAN_TAG in (a, b)})
    ours_in = [m for m in moves if m['ours'] and m['to'] == names.get(Config.CLAN_TAG)][:10]
    ours_out = [m for m in moves if m['ours'] and m['from'] == names.get(Config.CLAN_TAG)][:10]
    between = [m for m in moves if m['from_tracked'] and m['to_tracked']][:12]

    return {
        'built': datetime.now().isoformat(timespec='minutes'),
        'from': span[0].isoformat() if span[0] else None,
        'to': span[1].isoformat() if span[1] else None,
        'players': len(stints), 'days_observed': len(seen_dates),
        'clans': clans, 'weekly': weekly,
        'hours_ours': share(hours[Config.CLAN_TAG]), 'hours_field': share(field_hours),
        'ours_in': ours_in, 'ours_out': ours_out, 'between': between,
    }


METRICS = [
    # key, label, unit, higher is better
    ('war_stars_week', 'War stars per member per week', '', True),
    ('donations_day', 'Troops donated per member per day', '', True),
    ('active_days', 'Days members are active', '%', True),
    ('th_ups_month', 'TH upgrades per member per month', '', True),
    ('capital_day', 'Capital gold per member per day', '', True),
    ('churn_month', 'Members leaving per month', '%', False),
]


def health_headlines(d):
    ours = next((c for c in d['clans'] if c['ours']), None)
    if not ours:
        return []
    n = len(d['clans'])
    ranked = sorted(((ours.get(k + '_rank') or n, label) for k, label, _, _ in METRICS))
    best, worst = ranked[:2], ranked[-2:]
    out = [
        "Strongest against the other tracked clans: " +
        " and ".join(f"{label.lower()} ({_ordinal(r)} of {n})" for r, label in best) + ".",
        "Weakest: " + " and ".join(f"{label.lower()} ({_ordinal(r)} of {n})" for r, label in worst) + ".",
    ]
    field = [c for c in d['clans'] if not c['ours']]
    if field:
        avg_don = sum(c['donations_day'] for c in field) / len(field)
        out.append(f"Our members donate {ours['donations_day']:.0f} troops a day each, against "
                   f"{avg_don:.0f} for the average tracked clan.")
    if ours['churn_month'] is not None:
        stable = (ours.get('churn_month_rank') or n) <= n / 3
        out.append(f"{ours['leaves']} member(s) left while the harvester was watching, a churn of "
                   f"{ours['churn_month']}% a month" +
                   (", one of the most stable rosters." if stable else "."))
    return out


def _ordinal(n):
    suffix = 'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"
