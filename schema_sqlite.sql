-- ========================================================
-- SafeRoute: SQLite Schema (Identical structure to MySQL)
-- ========================================================

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    anonymous_handle TEXT NOT NULL UNIQUE,
    verified_woman_declared INTEGER DEFAULT 0,
    verification_status TEXT DEFAULT 'unverified',
    selfie_verified_at DATETIME NULL,
    passkey_credential_id TEXT NULL,
    passkey_public_key TEXT NULL,
    passkey_sign_count INTEGER DEFAULT 0,
    failed_otp_attempts INTEGER DEFAULT 0,
    is_locked INTEGER DEFAULT 0,
    locked_until DATETIME NULL,
    consent_location INTEGER DEFAULT 0,
    is_walk_together_opted_in INTEGER DEFAULT 0,
    last_location_lat REAL NULL,
    last_location_lng REAL NULL,
    last_location_updated DATETIME NULL,
    tamper_security_key TEXT DEFAULT '7799',
    duress_security_key TEXT DEFAULT '9911',
    anti_tamper_enabled INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS emergency_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    contact_name TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    relationship TEXT DEFAULT 'Emergency Contact',
    is_primary INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS route_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NULL,
    start_name TEXT NOT NULL,
    start_lat REAL NOT NULL,
    start_lng REAL NOT NULL,
    dest_name TEXT NOT NULL,
    dest_lat REAL NOT NULL,
    dest_lng REAL NOT NULL,
    selected_route_index INTEGER DEFAULT 0,
    safety_score INTEGER NOT NULL,
    time_of_day TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS incident_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reporter_user_id INTEGER NULL,
    incident_type TEXT NOT NULL,
    description TEXT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    address TEXT NULL,
    severity TEXT DEFAULT 'medium',
    confirmation_count INTEGER DEFAULT 1,
    status TEXT DEFAULT 'active',
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reporter_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS street_lights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    status TEXT DEFAULT 'working',
    source TEXT DEFAULT 'osm',
    confirmed_count INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS help_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    point_type TEXT NOT NULL,
    name TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    phone TEXT NULL,
    address TEXT NULL,
    operating_hours TEXT DEFAULT '24/7',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS walk_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requester_id INTEGER NOT NULL,
    recipient_id INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',
    requester_approx_dist_m INTEGER NOT NULL,
    trip_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME NULL,
    FOREIGN KEY (requester_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (recipient_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    walk_request_id INTEGER NOT NULL,
    sender_id INTEGER NOT NULL,
    message_text TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (walk_request_id) REFERENCES walk_requests(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS blocks_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reporter_id INTEGER NOT NULL,
    reported_user_id INTEGER NOT NULL,
    report_type TEXT NOT NULL,
    reason TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reporter_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (reported_user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tamper_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NULL,
    alert_type TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    notes TEXT NULL,
    police_dispatched INTEGER DEFAULT 1,
    contacts_notified_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
CREATE INDEX IF NOT EXISTS idx_incident_loc ON incident_reports(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_lights_loc ON street_lights(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_helppoint_loc ON help_points(latitude, longitude);
