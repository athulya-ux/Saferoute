import datetime
from database.db import execute_query

def seed_initial_data():
    """
    Populates sample real-world data for street lights, help points (police, hospitals, bus stops),
    incident reports, and mock opted-in travelers.
    Centering on an urban sample area (e.g. Bangalore / Central City / Delhi coordinates 12.9716, 77.5946),
    as well as generic relative coordinates suitable for any location.
    """
    # Check if already seeded
    existing_help = execute_query("SELECT COUNT(*) as cnt FROM help_points", fetch='one')
    if existing_help and existing_help['cnt'] > 0:
        return

    print("[Seed] Seeding sample help points, street lights, incidents, and demo users...")

    # 1. HELP POINTS (Police, Hospitals, Bus Stops)
    help_points = [
        # Police Stations
        ('police', 'Central Women Police Station', 12.9750, 77.5980, '080-22942222', 'Infantry Road, Central District', '24/7'),
        ('police', 'Cubbon Park Police Station', 12.9710, 77.5910, '080-22942544', 'Kasturba Road, Near High Court', '24/7'),
        ('police', 'Metro Transit Police Post', 12.9775, 77.5720, '112 / 1091', 'Majestic Metro Interchange', '24/7'),
        ('police', 'Brigade Road Pink Police Booth', 12.9735, 77.6075, '080-22942411', 'Brigade Road Junction', '24/7'),
        
        # Hospitals & 24/7 Clinics
        ('hospital', 'St. Martha\'s Women & Children Hospital', 12.9695, 77.5880, '080-22273381', 'Nrupathunga Road', '24/7 Emergency & Trauma'),
        ('hospital', 'Bowring & Lady Curzon Hospital', 12.9820, 77.6040, '080-25591362', 'Lady Curzon Road, Shivajinagar', '24/7 Emergency Care'),
        ('hospital', 'Victoria Hospital Emergency Trauma Centre', 12.9630, 77.5750, '080-26701150', 'Fort Road, Kalasipalyam', '24/7 Emergency & ICU'),
        ('hospital', 'Apollo 24/7 Care Clinic', 12.9780, 77.6150, '1860-500-1066', 'Old Airport Road Junction', '24/7 Pharmacy & First Aid'),
        
        # Bus Stops & Transit Terminals
        ('bus_stop', 'Majestic City Bus Stand Platform 1-12', 12.9767, 77.5713, '080-22952522', 'Subhash Nagar, Majestic', '04:30 AM - 11:30 PM'),
        ('bus_stop', 'Corporation Circle Bus Stop', 12.9675, 77.5895, None, 'K.G. Road / Hudson Circle', '05:00 AM - 11:00 PM'),
        ('bus_stop', 'MG Road Metro & City Bus Shelter', 12.9756, 77.6066, None, 'MG Road Boulevard', '05:30 AM - 11:45 PM'),
        ('bus_stop', 'Shivajinagar Bus Terminal', 12.9850, 77.6020, None, 'Russell Market Rd', '05:00 AM - 11:30 PM'),
        ('bus_stop', 'Richmond Circle Bus Stop', 12.9660, 77.5990, None, 'Richmond Road', '05:30 AM - 11:15 PM')
    ]

    for pt in help_points:
        execute_query("""
            INSERT INTO help_points (point_type, name, latitude, longitude, phone, address, operating_hours)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, pt)

    # 2. STREET LIGHTS (Clusters on main safe avenues and some dimmer spots)
    street_lights_coords = [
        # Well lit Brigade & MG Road stretch
        (12.9756, 77.6066, 'working', 'osm'),
        (12.9750, 77.6060, 'working', 'osm'),
        (12.9745, 77.6055, 'working', 'osm'),
        (12.9740, 77.6050, 'working', 'osm'),
        (12.9735, 77.6045, 'working', 'osm'),
        (12.9730, 77.6040, 'working', 'osm'),
        (12.9725, 77.6035, 'working', 'osm'),
        (12.9720, 77.6030, 'working', 'osm'),
        # Cubbon park periphery
        (12.9715, 77.5920, 'working', 'osm'),
        (12.9720, 77.5925, 'working', 'osm'),
        (12.9725, 77.5930, 'working', 'osm'),
        (12.9730, 77.5935, 'working', 'osm'),
        # Reported broken / dim street lights
        (12.9680, 77.5950, 'broken', 'user_report'),
        (12.9685, 77.5955, 'dim', 'user_report'),
        (12.9790, 77.5850, 'broken', 'user_report'),
        (12.9810, 77.5870, 'dim', 'user_report')
    ]

    for sl in street_lights_coords:
        execute_query("""
            INSERT INTO street_lights (latitude, longitude, status, source, confirmed_count)
            VALUES (%s, %s, %s, %s, 3)
        """, sl)

    # 3. INCIDENT REPORTS (Active with 30-day expiry)
    now = datetime.datetime.now()
    exp_25_days = (now + datetime.timedelta(days=25)).strftime('%Y-%m-%d %H:%M:%S')
    exp_20_days = (now + datetime.timedelta(days=20)).strftime('%Y-%m-%d %H:%M:%S')

    incidents = [
        ('dark_street', 'Street lamps non-functional for 200m alley behind subway. Poor visibility after 8 PM.', 
         12.9685, 77.5955, 'Crossroad 4, Lane behind Commercial St', 'high', 4, 'active', exp_25_days),
        ('harassment', 'Catcalling reported by multiple pedestrians near vacant construction lot.', 
         12.9795, 77.5865, 'Corner of 2nd Cross, Near Metro Pillar 140', 'critical', 6, 'active', exp_20_days),
        ('unsafe_spot', 'Isolated blind turn underpass with no CCTV coverage or security guard.', 
         12.9712, 77.5830, 'Old Railway Underpass, West Side', 'medium', 3, 'active', exp_25_days)
    ]

    for inc in incidents:
        execute_query("""
            INSERT INTO incident_reports 
            (incident_type, description, latitude, longitude, address, severity, confirmation_count, status, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, inc)

    # 4. DEMO VERIFIED USERS (For Walk Together radar testing)
    users = [
        ('+919876543210', 'Aarti Sharma', 'SafeTraveler #412', 1, 'verified', 1, 1, 12.9740, 77.5960),
        ('+919876543211', 'Pooja Verma', 'NightCompanion #809', 1, 'verified', 1, 1, 12.9725, 77.5945),
        ('+919876543212', 'Sneha Patel', 'CityWalker #305', 1, 'verified', 1, 1, 12.9760, 77.5975),
        ('+919876543213', 'Deepa Nair', 'CampusBuddy #921', 1, 'verified', 1, 0, 12.9800, 77.6000)
    ]

    for u in users:
        execute_query("""
            INSERT INTO users 
            (phone, full_name, anonymous_handle, verified_woman_declared, verification_status, 
             consent_location, is_walk_together_opted_in, last_location_lat, last_location_lng, last_location_updated)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, datetime('now', 'localtime'))
        """, u)

    print("[Seed] Seeding completed successfully.")
