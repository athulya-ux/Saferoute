-- ========================================================
-- SafeRoute: Women-Only Route Safety Platform Database Schema
-- Compatible with MySQL 8.0+ / MariaDB 10.4+
-- ========================================================

CREATE DATABASE IF NOT EXISTS saferoute_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE saferoute_db;

-- 1. USERS TABLE
-- Stores women-only verified users with anonymous handle, passkey & privacy settings
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    phone VARCHAR(20) NOT NULL UNIQUE,
    full_name VARCHAR(100) NOT NULL,
    anonymous_handle VARCHAR(50) NOT NULL UNIQUE,
    verified_woman_declared BOOLEAN DEFAULT FALSE,
    verification_status ENUM('unverified', 'pending', 'verified') DEFAULT 'unverified',
    selfie_verified_at DATETIME NULL,
    passkey_credential_id VARCHAR(255) NULL,
    passkey_public_key TEXT NULL,
    passkey_sign_count INT DEFAULT 0,
    failed_otp_attempts INT DEFAULT 0,
    is_locked BOOLEAN DEFAULT FALSE,
    locked_until DATETIME NULL,
    consent_location BOOLEAN DEFAULT FALSE,
    is_walk_together_opted_in BOOLEAN DEFAULT FALSE,
    last_location_lat DECIMAL(10, 7) NULL,
    last_location_lng DECIMAL(10, 7) NULL,
    last_location_updated DATETIME NULL,
    tamper_security_key VARCHAR(100) DEFAULT '7799',
    duress_security_key VARCHAR(100) DEFAULT '9911',
    anti_tamper_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_phone (phone),
    INDEX idx_walk_optin (is_walk_together_opted_in, last_location_updated)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. EMERGENCY CONTACTS TABLE
-- Emergency SOS contacts for each user
CREATE TABLE IF NOT EXISTS emergency_contacts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    contact_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    relationship VARCHAR(50) DEFAULT 'Emergency Contact',
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_contact (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. ROUTE REQUESTS TABLE
-- History of route queries and selected safety scores
CREATE TABLE IF NOT EXISTS route_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    start_name VARCHAR(255) NOT NULL,
    start_lat DECIMAL(10, 7) NOT NULL,
    start_lng DECIMAL(10, 7) NOT NULL,
    dest_name VARCHAR(255) NOT NULL,
    dest_lat DECIMAL(10, 7) NOT NULL,
    dest_lng DECIMAL(10, 7) NOT NULL,
    selected_route_index INT DEFAULT 0,
    safety_score INT NOT NULL,
    time_of_day ENUM('morning', 'afternoon', 'evening', 'night') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_route_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. INCIDENT REPORTS TABLE
-- Reports of dark streets, harassment, accidents, unsafe spots (expires after 30 days)
CREATE TABLE IF NOT EXISTS incident_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    reporter_user_id INT NULL,
    incident_type ENUM('dark_street', 'accident', 'harassment', 'unsafe_spot') NOT NULL,
    description TEXT NULL,
    latitude DECIMAL(10, 7) NOT NULL,
    longitude DECIMAL(10, 7) NOT NULL,
    address VARCHAR(255) NULL,
    severity ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
    confirmation_count INT DEFAULT 1,
    status ENUM('active', 'expired', 'dismissed') DEFAULT 'active',
    expires_at DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reporter_user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_incident_loc (latitude, longitude),
    INDEX idx_incident_status (status, expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. STREET LIGHTS TABLE
-- Street light coordinates from OSM Overpass & crowd-sourced user reports
CREATE TABLE IF NOT EXISTS street_lights (
    id INT AUTO_INCREMENT PRIMARY KEY,
    latitude DECIMAL(10, 7) NOT NULL,
    longitude DECIMAL(10, 7) NOT NULL,
    status ENUM('working', 'dim', 'broken') DEFAULT 'working',
    source ENUM('osm', 'user_report') DEFAULT 'osm',
    confirmed_count INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_lights_loc (latitude, longitude)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. HELP POINTS TABLE
-- Police stations, hospitals, 24/7 clinics, bus stops, transit hubs within reach
CREATE TABLE IF NOT EXISTS help_points (
    id INT AUTO_INCREMENT PRIMARY KEY,
    point_type ENUM('police', 'hospital', 'bus_stop') NOT NULL,
    name VARCHAR(150) NOT NULL,
    latitude DECIMAL(10, 7) NOT NULL,
    longitude DECIMAL(10, 7) NOT NULL,
    phone VARCHAR(50) NULL,
    address VARCHAR(255) NULL,
    operating_hours VARCHAR(100) DEFAULT '24/7',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_helppoint_type (point_type),
    INDEX idx_helppoint_loc (latitude, longitude)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. WALK REQUESTS TABLE
-- Mutual-consent walk-together requests between verified women travelers (within 1 km)
CREATE TABLE IF NOT EXISTS walk_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    requester_id INT NOT NULL,
    recipient_id INT NOT NULL,
    status ENUM('pending', 'accepted', 'rejected', 'completed', 'cancelled') DEFAULT 'pending',
    requester_approx_dist_m INT NOT NULL,
    trip_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME NULL,
    FOREIGN KEY (requester_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (recipient_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_walk_pair (requester_id, recipient_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. CHAT MESSAGES TABLE
-- Ephemeral in-app chat for active walk-together trips (purged upon trip completion)
CREATE TABLE IF NOT EXISTS chat_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    walk_request_id INT NOT NULL,
    sender_id INT NOT NULL,
    message_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (walk_request_id) REFERENCES walk_requests(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_chat_walk (walk_request_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. BLOCKS & REPORTS TABLE
-- Trust and safety table for blocking users or reporting abusive behavior
CREATE TABLE IF NOT EXISTS blocks_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    reporter_id INT NOT NULL,
    reported_user_id INT NOT NULL,
    report_type ENUM('block', 'harassment', 'fake_profile', 'inappropriate_behavior') NOT NULL,
    reason TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reporter_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (reported_user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_blocks_reporter (reporter_id, reported_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 10. TAMPER & ANTI-POWER-OFF ALERTS TABLE
-- Dispatches emergency alerts if a forced shutdown, SIM ejection, or tamper PIN failure occurs
CREATE TABLE IF NOT EXISTS tamper_alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    alert_type ENUM('poweroff_attempt', 'sim_eject_offline', 'failed_tamper_pin', 'duress_pin_entered') NOT NULL,
    latitude DECIMAL(10, 7) NOT NULL,
    longitude DECIMAL(10, 7) NOT NULL,
    notes TEXT NULL,
    police_dispatched BOOLEAN DEFAULT TRUE,
    contacts_notified_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_tamper_user (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
