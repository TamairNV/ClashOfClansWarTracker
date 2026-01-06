-- Clash of Clans War Tracker Schema Export
-- Database: clash_manager

-- Table structure for table `player_activity_log`
DROP TABLE IF EXISTS `player_activity_log`;
CREATE TABLE `player_activity_log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `player_tag` varchar(15) DEFAULT NULL,
  `activity_type` varchar(20) DEFAULT NULL,
  `timestamp` datetime DEFAULT current_timestamp(),
  `value` int(11) DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `player_tag` (`player_tag`),
  CONSTRAINT `player_activity_log_ibfk_1` FOREIGN KEY (`player_tag`) REFERENCES `players` (`player_tag`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1107 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Table structure for table `players`
DROP TABLE IF EXISTS `players`;
CREATE TABLE `players` (
  `player_tag` varchar(15) NOT NULL,
  `name` varchar(50) NOT NULL,
  `town_hall_level` int(11) NOT NULL,
  `is_in_clan` tinyint(1) DEFAULT 1,
  `last_known_donations` int(11) DEFAULT 0,
  `last_known_received` int(11) DEFAULT 0,
  `last_active_time` datetime DEFAULT current_timestamp(),
  `first_seen_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `trust_score` float DEFAULT 0,
  `role` varchar(50) DEFAULT 'Member',
  `discord_id` varchar(50) DEFAULT NULL,
  `guessed_timezone` varchar(50) DEFAULT NULL,
  `guessed_country` varchar(50) DEFAULT NULL,
  `timezone_confidence` float DEFAULT 0,
  `favorite_time_label` varchar(50) DEFAULT NULL,
  `activity_score` float DEFAULT 0,
  `builder_base_trophies` int(11) DEFAULT 0,
  `achievements` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`achievements`)),
  PRIMARY KEY (`player_tag`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Table structure for table `raid_members`
DROP TABLE IF EXISTS `raid_members`;
CREATE TABLE `raid_members` (
  `raid_id` varchar(20) NOT NULL,
  `player_tag` varchar(20) NOT NULL,
  `name` varchar(50) DEFAULT NULL,
  `attacks_count` int(11) DEFAULT NULL,
  `loot_looted` int(11) DEFAULT NULL,
  `medals_bonus` int(11) DEFAULT NULL,
  PRIMARY KEY (`raid_id`,`player_tag`),
  CONSTRAINT `raid_members_ibfk_1` FOREIGN KEY (`raid_id`) REFERENCES `raid_weekends` (`raid_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table structure for table `raid_weekends`
DROP TABLE IF EXISTS `raid_weekends`;
CREATE TABLE `raid_weekends` (
  `raid_id` varchar(20) NOT NULL,
  `state` varchar(20) DEFAULT NULL,
  `start_time` datetime DEFAULT NULL,
  `end_time` datetime DEFAULT NULL,
  `total_loot` int(11) DEFAULT NULL,
  `total_attacks` int(11) DEFAULT NULL,
  `districts_destroyed` int(11) DEFAULT NULL,
  `medals_earned` int(11) DEFAULT NULL,
  PRIMARY KEY (`raid_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table structure for table `war_attacks`
DROP TABLE IF EXISTS `war_attacks`;
CREATE TABLE `war_attacks` (
  `attack_id` int(11) NOT NULL AUTO_INCREMENT,
  `war_id` int(11) NOT NULL,
  `player_tag` varchar(15) NOT NULL,
  `stars` int(11) DEFAULT 0,
  `destruction` float DEFAULT 0,
  `duration` int(11) DEFAULT 0,
  `army_composition` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`army_composition`)),
  `attack_order` int(11) DEFAULT 1,
  `defender_tag` varchar(15) DEFAULT NULL,
  `defender_th` int(11) DEFAULT NULL,
  `hero_equipment` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`hero_equipment`)),
  PRIMARY KEY (`attack_id`),
  KEY `war_id` (`war_id`),
  KEY `player_tag` (`player_tag`),
  CONSTRAINT `war_attacks_ibfk_1` FOREIGN KEY (`war_id`) REFERENCES `wars` (`war_id`) ON DELETE CASCADE,
  CONSTRAINT `war_attacks_ibfk_2` FOREIGN KEY (`player_tag`) REFERENCES `players` (`player_tag`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=279 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Table structure for table `war_defenses`
DROP TABLE IF EXISTS `war_defenses`;
CREATE TABLE `war_defenses` (
  `defense_id` int(11) NOT NULL AUTO_INCREMENT,
  `war_id` int(11) DEFAULT NULL,
  `defender_tag` varchar(20) DEFAULT NULL,
  `attacker_tag` varchar(20) DEFAULT NULL,
  `attacker_name` varchar(50) DEFAULT NULL,
  `stars` int(11) DEFAULT NULL,
  `destruction_percentage` float DEFAULT NULL,
  `duration_seconds` int(11) DEFAULT NULL,
  `attack_order` int(11) DEFAULT NULL,
  `army_composition` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`army_composition`)),
  `hero_equipment` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`hero_equipment`)),
  PRIMARY KEY (`defense_id`),
  UNIQUE KEY `unique_defense` (`war_id`,`defender_tag`,`attack_order`),
  CONSTRAINT `war_defenses_ibfk_1` FOREIGN KEY (`war_id`) REFERENCES `wars` (`war_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=484 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table structure for table `war_opponents`
DROP TABLE IF EXISTS `war_opponents`;
CREATE TABLE `war_opponents` (
  `opponent_tag` varchar(15) NOT NULL,
  `war_id` int(11) NOT NULL,
  `map_position` int(11) DEFAULT NULL,
  `town_hall_level` int(11) DEFAULT NULL,
  `stars` int(11) DEFAULT 0,
  `destruction` float DEFAULT 0,
  PRIMARY KEY (`war_id`,`opponent_tag`),
  CONSTRAINT `war_opponents_ibfk_1` FOREIGN KEY (`war_id`) REFERENCES `wars` (`war_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Table structure for table `war_performance`
DROP TABLE IF EXISTS `war_performance`;
CREATE TABLE `war_performance` (
  `performance_id` int(11) NOT NULL AUTO_INCREMENT,
  `war_id` int(11) DEFAULT NULL,
  `player_tag` varchar(15) DEFAULT NULL,
  `town_hall_at_time` int(11) DEFAULT NULL,
  `stars` int(11) DEFAULT 0,
  `destruction_percentage` float DEFAULT 0,
  `attacks_used` int(11) DEFAULT 0,
  `attack_1_time` datetime DEFAULT NULL,
  `attack_2_time` datetime DEFAULT NULL,
  `defense_stars` int(11) DEFAULT 0,
  PRIMARY KEY (`performance_id`),
  UNIQUE KEY `unique_player_war` (`war_id`,`player_tag`),
  KEY `player_tag` (`player_tag`),
  CONSTRAINT `war_performance_ibfk_1` FOREIGN KEY (`war_id`) REFERENCES `wars` (`war_id`) ON DELETE CASCADE,
  CONSTRAINT `war_performance_ibfk_2` FOREIGN KEY (`player_tag`) REFERENCES `players` (`player_tag`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=53121 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Table structure for table `wars`
DROP TABLE IF EXISTS `wars`;
CREATE TABLE `wars` (
  `war_id` int(11) NOT NULL AUTO_INCREMENT,
  `opponent_name` varchar(50) DEFAULT NULL,
  `opponent_tag` varchar(15) DEFAULT NULL,
  `war_type` enum('regular','cwl','friendly') DEFAULT 'regular',
  `state` varchar(20) DEFAULT NULL,
  `start_time` datetime DEFAULT NULL,
  `end_time` datetime DEFAULT NULL,
  `result` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`war_id`),
  UNIQUE KEY `unique_war` (`opponent_tag`,`start_time`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

