import sqlite3

for path in ['safety/database/saferoute.sqlite', 'saferoute/database/saferoute.sqlite']:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute('PRAGMA table_info(users)')
    cols = [r[1] for r in cur.fetchall()]
    
    if 'tamper_security_key' not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN tamper_security_key TEXT DEFAULT '7799'")
    if 'duress_security_key' not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN duress_security_key TEXT DEFAULT '9911'")
    if 'anti_tamper_enabled' not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN anti_tamper_enabled INTEGER DEFAULT 1")
    
    cur.execute('''
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
        )
    ''')
    conn.commit()
    conn.close()
    print('Migrated:', path)
