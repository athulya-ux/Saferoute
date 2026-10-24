# SafeRoute - Women-Only Route Safety Platform

**SafeRoute** is a responsive, mobile-first web application designed to empower women with real-time safety scores, community-verified hazard warnings, well-lit pedestrian routing, mutual-consent walking companions, and a one-tap emergency response.

---

## 🌟 Tech Stack

- **Frontend:** HTML5, CSS3, JavaScript (ES6+), [Leaflet.js](https://leafletjs.com/) with OpenStreetMap (OSM) CartoDB tiles.
- **Backend:** Python Flask (Blueprints architecture, CORS enabled).
- **Live Ephemeral Chat:** Flask-SocketIO (WebSockets / Long-Polling fallback).
- **Database:** MySQL 8.0+ / MariaDB (PyMySQL connector) with automatic fallback to zero-config SQLite for instant local execution.
- **Routing & Geodata:** OpenStreetMap Overpass API (police stations, hospitals, bus stops, street lights) & OSRM (Open Source Routing Machine).

---

## 📁 Folder Structure

```
safety/
├── .env.example              # Sample environment configuration
├── README.md                 # Complete documentation & setup guide
├── requirements.txt          # Python dependencies
├── run.py                    # Application launcher with SocketIO runner
├── config.py                 # Configuration settings (MySQL / SQLite, scoring weights)
├── database/
│   ├── db.py                 # Unified database query engine (MySQL with SQLite fallback)
│   ├── schema.sql            # Full MySQL production schema (10 tables)
│   ├── schema_sqlite.sql     # SQLite equivalent schema (10 tables)
│   └── seed_data.py          # Sample street lights, help points, incidents & demo users
├── api/
│   ├── routes_api.py         # Feature 1: Route options & 0-100 safety score calculation
│   ├── incidents_api.py      # Feature 2: Street lights, crowd zones, 30-day incident reports
│   ├── help_points_api.py    # Feature 3: 5km police/hospital/bus, bus schedules, cab deep links
│   ├── auth_api.py           # Feature 4: Phone OTP, self-declaration, WebAuthn/passkey, privacy
│   ├── walk_together_api.py  # Feature 5: 1km radar with distance fuzzing, block/report
│   ├── emergency_api.py      # Feature 6: SOS GPS broadcast, siren, 10s countdown, contacts
│   └── anti_tamper_api.py    # Feature 7: Power-off & SIM removal guard, duress PIN & police alert
├── sockets/
│   └── chat_socket.py        # Live in-app SocketIO chat & real-time walk request alerts
├── static/
│   ├── css/
│   │   └── styles.css        # Responsive mobile-first stylesheet & animations
│   └── js/
│       ├── app.js            # App coordinator, tabs & multi-user URL handling
│       ├── map.js            # Leaflet map manager, polylines & custom SVG icons
│       ├── routes.js         # Route calculation & safety breakdown cards
│       ├── incidents.js      # Incident reporting, +1 confirmations & 30-day lifecycle
│       ├── help.js           # 5km help points, bus timings & Uber/Ola cab links
│       ├── walk.js           # Walk together 2-women mutual request & live chat
│       ├── emergency.js      # Giant SOS button, audio siren & helpline dialing
│       ├── tamper.js         # Power-off & SIM removal interceptor, PIN keypad & police dispatch
│       └── auth.js           # Verification, passkey linking & zero-biometric purge
└── templates/
    └── index.html            # Mobile-first single-page web app with bottom navigation
```

---

## 🛡️ Key Features Overview

### 1. 2-Women Mutual Agreement & Live Ephemeral Chat (Feature 5)
- **1 km Radar:** Scans for verified women travelers within 1 km. Only approximate fuzzed distances (*~350m*) and anonymous handles (*SafeTraveler #412*) are shared. Exact GPS coordinates are never revealed.
- **Mutual Consent Request Flow:**
  1. Woman A clicks **"Request"** on Woman B's profile.
  2. Woman B receives an instant real-time pop-up notification with Woman A's handle and distance.
  3. Woman B clicks **"Accept & Walk Together"** (or Decline).
  4. Upon mutual acceptance, the **in-app live chat drawer opens on both devices**.
  5. Both women chat in real-time via Socket.IO without sharing phone numbers, real names, or personal identities.
- **Trip Conclusion & Safety:** An **"End Trip"** button auto-closes the session, sets visibility to private, and purges messages. A **"Block & Report"** button immediately terminates connections.
- **How to Test 2 Users on One Machine:**
  - Click the **"2-Women Test"** button in the top navigation bar, or open:
    - Tab 1: `http://localhost:5000/?user=1` (Aarti Sharma - *SafeTraveler #412*)
    - Tab 2: `http://localhost:5000/?user=2` (Pooja Verma - *NightCompanion #809*)

---

### 2. Anti-Tamper & Power-Off / SIM Removal Protection (Feature 7)
- **Prevents Forced Shutdown:** If an attacker attempts to power off the phone, close the web app, or eject the SIM card / disable mobile data, the device is immediately placed into **Full-Screen Lockdown Mode**.
- **10-Second Keypad Authorization:**
  - A prominent security dialog appears: *"UNAUTHORIZED POWER-OFF INTERCEPTED"*.
  - Requires the user to enter their secret 4-digit **Safety Key** (Default: `7799`).
- **Automatic Police (112) & Emergency Contacts Alert:**
  - If the countdown hits 0 or an invalid key is entered, the app immediately:
    1. Sends live GPS coordinates & Google Maps link to all saved emergency contacts via SMS alert.
    2. Issues an automated priority dispatch alert to the **Police Emergency Control Room (112)** and **Women Helpline (1091)** with a unique dispatch reference (e.g. `POL-ALERT-556463`).
    3. Sounds a loud, high-decibel audio siren alarm to draw public attention.
- **Duress Panic PIN (`9911`):**
  - If coerced by an attacker to unlock the device, the victim can enter the **Duress PIN (`9911`)**.
  - The screen displays a normal shutdown message to deceive the attacker, but **silently dispatches the Police (112) and emergency contacts with high-priority code "COERCED SHUTDOWN"**.
- **Interactive Testing in UI:**
  - In the **SOS** tab, use the **"Test Power-Off Shield"** or **"Test SIM Ejection Shield"** buttons to simulate attacker actions and view the lockdown flow.

---

### 3. Safe Routes (0–100 Safety Scoring Engine)
- **Alternative Routes:** Displays 2–3 route options between origin and destination with duration, distance, and safety classification.
- **Weighted Safety Formula ($0 - 100$):**
  $$\text{Safety Score} = \text{Lighting} \,(30) + \text{Crowd} \,(25) + \text{Help Points} \,(25) - \text{Time Penalty} \,(0\text{ to }15) - \text{Incidents} \,(0\text{ to }45)$$
- **Transparent Breakdown:** Click *"Why this score?"* to inspect light density per km, crowd footfall level by time of day, and nearby police posts.
- **Safest Route Marking:** The highest scoring route is automatically highlighted in emerald green with a ⭐ Safest Route badge.

---

### 4. Street Lights, Crowd Info & 30-Day Incident Reports
- **Street Light Tracking:** Displays working, dim, and broken street lights along corridors (OSM Overpass + community submissions).
- **Crowd Schedule:** Visual schedule indicating footfall patterns across Morning, Afternoon, Evening, and Night.
- **Incident Reports with 30-Day Lifecycle:** Dark street, harassment, accident, and unsafe blind spot reports auto-expire after 30 days and feature a **+1 Confirm** button to increase community trust.

---

### 5. Nearby Help Points (5 km) & Cab Booking
- **5 km Help Perimeter:** Police stations, 24/7 emergency hospitals, and transit hubs (Overpass OSM API + high-reliability database fallback).
- **Transit & Bus Schedules:** Shows upcoming bus arrivals, frequency, and women-safety features (*Pink CCTV bus*, *Reserved front rows*, *Pink pass*).
- **"Book a Cab" Deep Links:** One-tap deep links to **Uber**, **Ola Cabs**, and **Pink Women Cabs** with coordinates prefilled.
- **Unsafe Route Warning:** If a route scores $<60$, a **10-second cancellable trip countdown** appears before broadcasting live trip sharing.

---

### 6. Women-Only Verification & Passkeys
- **Phone OTP Sign-Up:** Rate-limited with automatic 15-minute account lock after 5 consecutive failed attempts.
- **Affirmative Self-Declaration:** Solemn confirmation of being a woman seeking safe transit.
- **Zero-Biometric Policy:** Optional selfie verification runs face liveness verification in memory and **permanently purges the image immediately** upon approval.
- **WebAuthn Passkeys:** Links device fingerprint or Face ID using the W3C WebAuthn standard so biometrics remain strictly on the user's device.
- **Right to be Forgotten:** Full account deletion endpoint (`DELETE /api/auth/delete_account`) purges all personal data, contacts, and logs.

---

## 🗄️ Database Tables (MySQL / SQLite)

| Table | Purpose |
|---|---|
| `users` | Credentials, phone, anonymous handle, passkey credentials, tamper security keys (`tamper_security_key`, `duress_security_key`), radar toggle |
| `emergency_contacts` | Saved SOS contacts (name, phone, relationship, primary flag) |
| `route_requests` | Log of route searches, coordinates, selected route index, and score |
| `incident_reports` | Dark street, harassment, accident, unsafe spots (with 30-day `expires_at` and `confirmation_count`) |
| `street_lights` | Latitude, longitude, status (`working`, `dim`, `broken`), and source |
| `help_points` | Police stations, hospitals, bus stops within 5km radius with contact numbers |
| `walk_requests` | Mutual consent walk companion requests, approximate distance, and session status |
| `chat_messages` | Ephemeral chat messages tied to active walk requests |
| `blocks_reports` | Blocked users and safety reports to prevent unwanted requests |
| `tamper_alerts` | Log of unauthorized power-off, SIM ejection, and duress PIN alerts with police dispatch reference |

---

## 🚀 Running the Application

### 1. Start Server
```powershell
cd safety
python run.py
```
Open your browser at:
👉 **`http://localhost:5000`**

### 2. Run Test Suites
```powershell
# Test All Core Features
python test_api.py

# Test 2-Women Walk Agreement & Anti-Tamper Protection
python test_tamper_and_walk.py
```
