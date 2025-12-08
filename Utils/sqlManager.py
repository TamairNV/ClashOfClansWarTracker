import pymysql
from pymysql.cursors import DictCursor
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class SQLManager:
    def __init__(self, host, user, password, db_name):
        self.config = {
            'host': host,
            'user': user,
            'password': password,
            'database': db_name,
            'cursorclass': DictCursor,
            'autocommit': True
        }
        self.connection = None

    def connect(self):
        if self.connection is None or not self.connection.open:
            try:
                self.connection = pymysql.connect(**self.config)
            except pymysql.MySQLError as e:
                print(f"❌ Database Connection Error: {e}")
                raise

    def close(self):
        if self.connection and self.connection.open:
            self.connection.close()

    def execute(self, sql, params=None):
        self.connect()
        with self.connection.cursor() as cursor:
            try:
                cursor.execute(sql, params)
                return cursor.rowcount
            except pymysql.MySQLError as e:
                print(f"❌ Query Error: {e} \nSQL: {sql}")
                return 0

    def fetch_one(self, sql, params=None):
        self.connect()
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()

    def fetch_all(self, sql, params=None):
        self.connect()
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    # --- WAR METHODS ---

    def get_war(self, opponent_tag, start_time):
        sql = "SELECT * FROM wars WHERE opponent_tag = %s AND start_time = %s"
        return self.fetch_one(sql, (opponent_tag, start_time))

    def get_active_war(self):
        sql = "SELECT * FROM wars WHERE state IN ('inWar', 'preparation') ORDER BY start_time DESC LIMIT 1"
        return self.fetch_one(sql)

    def update_war(self, war_data):
        existing = self.get_war(war_data['opponent_tag'], war_data['start_time'])
        if existing:
            sql = "UPDATE wars SET state=%s, end_time=%s, opponent_name=%s WHERE war_id=%s"
            self.execute(sql, (war_data['state'], war_data['end_time'], war_data['opponent_name'], existing['war_id']))
            return existing['war_id']
        else:
            sql = "INSERT INTO wars (opponent_name, opponent_tag, war_type, state, start_time, end_time) VALUES (%s, %s, %s, %s, %s, %s)"
            self.execute(sql, (war_data['opponent_name'], war_data['opponent_tag'], war_data['type'], war_data['state'],
                               war_data['start_time'], war_data['end_time']))
            new_war = self.get_war(war_data['opponent_tag'], war_data['start_time'])
            return new_war['war_id'] if new_war else None

    def update_war_performance(self, war_id, player_data):
        sql = """
            INSERT INTO war_performance (war_id, player_tag, town_hall_at_time, stars, destruction_percentage, attacks_used, defense_stars)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE stars=VALUES(stars), destruction_percentage=VALUES(destruction_percentage), attacks_used=VALUES(attacks_used), defense_stars=VALUES(defense_stars)
        """
        self.execute(sql, (war_id, player_data['tag'], player_data['town_hall'], player_data['stars'],
                           player_data['destruction'], player_data['attacks_used'], player_data['defense_stars']))

    def update_war_opponent(self, war_id, enemy_data):
        sql = """
            INSERT INTO war_opponents (war_id, opponent_tag, map_position, town_hall_level, stars, destruction)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE stars=VALUES(stars), destruction=VALUES(destruction)
        """
        self.execute(sql, (war_id, enemy_data['tag'], enemy_data['map_position'], enemy_data['town_hall'],
                           enemy_data['stars'], enemy_data['destruction']))

    def get_stale_wars(self):
        """Fetches active wars that should have ended."""
        sql = "SELECT * FROM wars WHERE state IN ('inWar', 'preparation') AND end_time < NOW()"
        return self.fetch_all(sql)

    def force_close_war(self, war_id):
        """Forcefully marks a war as ended."""
        sql = "UPDATE wars SET state = 'warEnded' WHERE war_id = %s"
        self.execute(sql, (war_id,))

    # --- ANALYTICS ---

    def get_all_active_players(self):
        return self.fetch_all("SELECT * FROM players WHERE is_in_clan = TRUE")

    def get_full_roster_including_leavers(self):
        """Gets everyone, sorting active players first."""
        return self.fetch_all("SELECT * FROM players ORDER BY is_in_clan DESC, trust_score DESC")

    def get_player_history(self, player_tag, limit=5):
        # ONLY fetches ENDED wars to avoid active war penalties
        sql = """
            SELECT wp.*, w.start_time, w.war_type
            FROM war_performance wp
            JOIN wars w ON wp.war_id = w.war_id
            WHERE wp.player_tag = %s AND w.state = 'warEnded'
            ORDER BY w.start_time DESC LIMIT %s
        """
        return self.fetch_all(sql, (player_tag, limit))

    def update_trust_score(self, player_tag, score):
        self.execute("UPDATE players SET trust_score = %s WHERE player_tag = %s", (score, player_tag))

    def update_player_timezone(self, player_tag, timezone, country, confidence, favorite_time, activity_score):
        sql = """
        UPDATE players 
        SET guessed_timezone=%s, guessed_country=%s, timezone_confidence=%s, favorite_time_label=%s, activity_score=%s 
        WHERE player_tag=%s
        """
        self.execute(sql, (timezone, country, confidence, favorite_time, activity_score, player_tag))

    def get_player(self, player_tag):
        return self.fetch_one("SELECT * FROM players WHERE player_tag = %s", (player_tag,))

    def get_player_by_discord_id(self, discord_id):
        return self.fetch_one("SELECT * FROM players WHERE discord_id = %s", (discord_id,))

    def link_discord_user(self, player_tag, discord_id):
        self.execute("UPDATE players SET discord_id = %s WHERE player_tag = %s", (discord_id, player_tag))

    def update_player_roster(self, player_data):
        sql = """
        INSERT INTO players (player_tag, name, town_hall_level, role, is_in_clan, updated_at)
        VALUES (%s, %s, %s, %s, TRUE, NOW())
        ON DUPLICATE KEY UPDATE name=VALUES(name), town_hall_level=VALUES(town_hall_level), role=VALUES(role), is_in_clan=TRUE, updated_at=NOW()
        """
        self.execute(sql, (player_data.tag, player_data.name, player_data.town_hall, str(player_data.role)))

    def mark_player_left(self, player_tag):
        self.execute("UPDATE players SET is_in_clan = FALSE WHERE player_tag = %s", (player_tag,))

    def update_activity_heartbeat(self, player_tag, current_donations, current_received):
        db_player = self.get_player(player_tag)
        if not db_player: return
        last_donations = db_player.get('last_known_donations', 0)
        
        # Log activity if donations changed
        if current_donations > last_donations:
            self.log_player_activity(player_tag, 'donation', value=current_donations)
            self.execute(
                "UPDATE players SET last_known_donations=%s, last_known_received=%s, last_active_time=NOW() WHERE player_tag=%s",
                (current_donations, current_received, player_tag))
        elif current_donations < last_donations:
            # Season reset or left clan and came back? Just update without logging activity for now
            self.execute("UPDATE players SET last_known_donations=%s, last_known_received=%s WHERE player_tag=%s",
                         (current_donations, current_received, player_tag))

    def log_player_activity(self, player_tag, activity_type, value=0):
        """Logs a timestamped activity event for a player."""
        self.execute(
            "INSERT INTO player_activity_log (player_tag, activity_type, value, timestamp) VALUES (%s, %s, %s, NOW())",
            (player_tag, activity_type, value)
        )

    def get_player_activity_history(self, player_tag, limit=100):
        """Fetches recent activity logs for a player."""
        return self.fetch_all(
            "SELECT * FROM player_activity_log WHERE player_tag = %s ORDER BY timestamp DESC LIMIT %s",
            (player_tag, limit)
        )

    def update_war_attack(self, war_id, player_tag, attack_data):
        """Updates or inserts a single attack record."""
        # attack_data includes: stars, destruction, duration, army_composition, order, defender_tag, defender_th
        sql = """
            INSERT INTO war_attacks (war_id, player_tag, stars, destruction, duration, army_composition, attack_order, defender_tag, defender_th)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            stars = VALUES(stars),
            destruction = VALUES(destruction),
            duration = VALUES(duration),
            army_composition = VALUES(army_composition),
            defender_th = VALUES(defender_th);
        """
        
        check_sql = "SELECT attack_id FROM war_attacks WHERE war_id=%s AND player_tag=%s AND attack_order=%s"
        existing = self.fetch_one(check_sql, (war_id, player_tag, attack_data['order']))
        
        if existing:
            update_sql = """
                UPDATE war_attacks SET stars=%s, destruction=%s, duration=%s, army_composition=%s, defender_tag=%s, defender_th=%s
                WHERE attack_id=%s
            """
            self.execute(update_sql, (attack_data['stars'], attack_data['destruction'], attack_data.get('duration', 0), 
                                      attack_data.get('army_composition', '{}'), attack_data['defender_tag'], 
                                      attack_data['defender_th'], existing['attack_id']))
        else:
            self.execute(sql, (war_id, player_tag, attack_data['stars'], attack_data['destruction'], 
                               attack_data.get('duration', 0), attack_data.get('army_composition', '{}'),
                               attack_data['order'], attack_data['defender_tag'], attack_data['defender_th']))

    def get_player_attacks(self, player_tag, limit=50):
        """Fetches individual attack history for a player."""
        sql = """
            SELECT wa.*, w.start_time, w.opponent_name
            FROM war_attacks wa
            JOIN wars w ON wa.war_id = w.war_id
            WHERE wa.player_tag = %s
            ORDER BY w.start_time DESC, wa.attack_order ASC
            LIMIT %s
        """
        return self.fetch_all(sql, (player_tag, limit))

    def get_player_war_stats(self, player_tag):
        """Aggregates war statistics for a player, ONLY for ended wars."""
        # Heuristic for Triple Rate from historical war_performance data:
        # - 6 stars (2 attacks) -> 2 triples
        # - 4 or 5 stars (2 attacks) -> 1 triple (must be 3+1 or 3+2)
        # - 3 stars (1 attack) -> 1 triple
        # - 3 stars (2 attacks) -> Assume 0 triples (conservative, could be 2+1)
        sql = """
            SELECT 
                COUNT(*) as total_wars,
                SUM(wp.stars) as total_stars,
                AVG(wp.destruction_percentage) as avg_destruction,
                SUM(wp.attacks_used) as total_attacks,
                SUM(
                CASE 
                    WHEN LOWER(w.war_type) = 'cwl' THEN 1 - wp.attacks_used
                    ELSE 2 - wp.attacks_used
                END
            ) as missed_attacks,
            SUM(
                CASE 
                    WHEN wp.stars = 6 THEN 2
                    WHEN wp.stars IN (4, 5) THEN 1
                    WHEN wp.stars = 3 AND wp.attacks_used = 1 THEN 1
                    ELSE 0 
                END
            ) as estimated_triples
            FROM war_performance wp
            JOIN wars w ON wp.war_id = w.war_id
            WHERE wp.player_tag = %s AND w.state = 'warEnded'
        """
        return self.fetch_one(sql, (player_tag,))

    # --- STRATEGY DATA ---

    def get_full_war_map(self, war_id):
        our_team = self.fetch_all("""
            SELECT 
                p.name, 
                wp.town_hall_at_time as th, 
                wp.attacks_used, 
                wp.player_tag, 
                p.trust_score as score,
                (SELECT COUNT(*) FROM war_attacks wa WHERE wa.player_tag = p.player_tag AND wa.stars = 3) as total_triples,
                (SELECT COUNT(*) FROM war_attacks wa WHERE wa.player_tag = p.player_tag) as total_attacks
            FROM war_performance wp
            JOIN players p ON wp.player_tag = p.player_tag
            WHERE wp.war_id = %s
            ORDER BY wp.town_hall_at_time DESC
        """, (war_id,))

        enemy_team = self.fetch_all("""
            SELECT * FROM war_opponents 
            WHERE war_id = %s 
            ORDER BY map_position ASC
        """, (war_id,))

        return our_team, enemy_team