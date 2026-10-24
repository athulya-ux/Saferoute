import datetime
from flask import Blueprint, request, jsonify
from database.db import execute_query

incidents_bp = Blueprint('incidents_bp', __name__)

@incidents_bp.route('/api/incidents', methods=['GET'])
def get_incidents():
    """
    Returns active, unexpired incident reports (dark_street, accident, harassment, unsafe_spot).
    Reports expire automatically after 30 days.
    """
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    radius_km = request.args.get('radius_km', default=10, type=float)

    # Cleanup expired reports
    execute_query("""
        UPDATE incident_reports 
        SET status = 'expired' 
        WHERE status = 'active' AND expires_at <= datetime('now', 'localtime')
    """)

    incidents = execute_query("""
        SELECT id, reporter_user_id, incident_type, description, latitude, longitude, 
               address, severity, confirmation_count, status, expires_at, created_at
        FROM incident_reports
        WHERE status = 'active'
        ORDER BY created_at DESC
    """, fetch='all') or []

    # Format output with human friendly expiry countdown
    now = datetime.datetime.now()
    results = []
    for inc in incidents:
        exp_dt = None
        days_left = 30
        if inc.get('expires_at'):
            try:
                if isinstance(inc['expires_at'], str):
                    exp_dt = datetime.datetime.fromisoformat(inc['expires_at'].replace('Z', ''))
                else:
                    exp_dt = inc['expires_at']
                days_left = max(0, (exp_dt - now).days)
            except Exception:
                pass
        
        inc['days_remaining'] = days_left
        results.append(inc)

    return jsonify({
        "status": "success",
        "count": len(results),
        "incidents": results
    })

@incidents_bp.route('/api/incidents/report', methods=['POST'])
def create_incident_report():
    """
    Submit a crowd-sourced safety report:
    incident_type: 'dark_street' | 'accident' | 'harassment' | 'unsafe_spot'
    latitude, longitude, address, description, severity
    Automatically sets 30-day expiration date.
    """
    data = request.get_json() or {}
    incident_type = data.get('incident_type')
    valid_types = ['dark_street', 'accident', 'harassment', 'unsafe_spot']
    
    if incident_type not in valid_types:
        return jsonify({"error": f"Invalid incident type. Must be one of: {', '.join(valid_types)}"}), 400

    try:
        latitude = float(data['latitude'])
        longitude = float(data['longitude'])
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "Valid latitude and longitude are required"}), 400

    description = data.get('description', '').strip()
    address = data.get('address', 'Pinned Location').strip()
    severity = data.get('severity', 'medium')
    reporter_id = data.get('user_id')

    # Expiry 30 days from now
    now = datetime.datetime.now()
    expires_at = (now + datetime.timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')

    report_id = execute_query("""
        INSERT INTO incident_reports 
        (reporter_user_id, incident_type, description, latitude, longitude, address, severity, confirmation_count, status, expires_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 1, 'active', %s)
    """, (reporter_id, incident_type, description, latitude, longitude, address, severity, expires_at))

    # If it's a dark street, also update/insert a street_light entry with status='broken'
    if incident_type == 'dark_street':
        execute_query("""
            INSERT INTO street_lights (latitude, longitude, status, source, confirmed_count)
            VALUES (%s, %s, 'broken', 'user_report', 1)
        """, (latitude, longitude))

    return jsonify({
        "status": "success",
        "message": "Safety incident successfully reported and shared with community.",
        "incident_id": report_id,
        "expires_in_days": 30
    }), 201

@incidents_bp.route('/api/incidents/<int:incident_id>/confirm', methods=['POST'])
def confirm_incident(incident_id):
    """
    Other women travelers confirm an active incident report (+1 to confirmation_count).
    Increases verification trust and weight.
    """
    incident = execute_query("SELECT id, confirmation_count, status FROM incident_reports WHERE id = %s", (incident_id,), fetch='one')
    if not incident:
        return jsonify({"error": "Incident report not found"}), 404

    execute_query("""
        UPDATE incident_reports 
        SET confirmation_count = confirmation_count + 1 
        WHERE id = %s
    """, (incident_id,))

    new_count = incident['confirmation_count'] + 1
    return jsonify({
        "status": "success",
        "message": "Thank you for confirming this safety warning. Your feedback protects fellow travelers.",
        "incident_id": incident_id,
        "new_confirmation_count": new_count
    })

@incidents_bp.route('/api/street_lights', methods=['GET'])
def get_street_lights():
    """Returns working, dim, and broken street lights for map rendering."""
    lights = execute_query("""
        SELECT id, latitude, longitude, status, source, confirmed_count, created_at
        FROM street_lights
        ORDER BY id DESC LIMIT 500
    """, fetch='all') or []

    stats = {
        "total": len(lights),
        "working": sum(1 for l in lights if l.get('status') == 'working'),
        "dim": sum(1 for l in lights if l.get('status') == 'dim'),
        "broken": sum(1 for l in lights if l.get('status') == 'broken')
    }

    return jsonify({
        "status": "success",
        "stats": stats,
        "street_lights": lights
    })

@incidents_bp.route('/api/street_lights/report', methods=['POST'])
def report_street_light():
    """User reports working/dim/broken street light."""
    data = request.get_json() or {}
    try:
        lat = float(data['latitude'])
        lng = float(data['longitude'])
        status = data.get('status', 'broken')
        if status not in ('working', 'dim', 'broken'):
            status = 'broken'
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "Latitude, longitude, and status are required"}), 400

    lid = execute_query("""
        INSERT INTO street_lights (latitude, longitude, status, source, confirmed_count)
        VALUES (%s, %s, %s, 'user_report', 1)
    """, (lat, lng, status))

    return jsonify({
        "status": "success",
        "message": f"Street light marked as {status}.",
        "id": lid
    }), 201

@incidents_bp.route('/api/crowd_zones', methods=['GET'])
def get_crowd_zones():
    """
    Returns crowd zones categorized by time of day:
    morning (06-12), afternoon (12-17), evening (17-21), night (21-06)
    """
    time_of_day = request.args.get('time_of_day')
    if not time_of_day:
        hour = datetime.datetime.now().hour
        if 6 <= hour < 12:
            time_of_day = 'morning'
        elif 12 <= hour < 17:
            time_of_day = 'afternoon'
        elif 17 <= hour < 21:
            time_of_day = 'evening'
        else:
            time_of_day = 'night'

    # Crowd zones with polygons/circles representing commercial corridors, markets, stations
    zones = [
        {
            "name": "Commercial Boulevard & Retail Market",
            "center": [12.9756, 77.6066],
            "radius_m": 450,
            "crowd_level": "High" if time_of_day in ('evening', 'afternoon') else ("Moderate" if time_of_day == 'morning' else "Low"),
            "safety_note": "Well-patrolled by pink police; high footfall till 10 PM.",
            "operating_hours": "09:00 AM - 10:30 PM"
        },
        {
            "name": "Central Railway & Bus Interchange",
            "center": [12.9770, 77.5720],
            "radius_m": 500,
            "crowd_level": "High", # High round the clock
            "safety_note": "24/7 active transit hub with CCTV cameras and security booth.",
            "operating_hours": "24/7"
        },
        {
            "name": "University Campus & Library Lane",
            "center": [12.9715, 77.5860],
            "radius_m": 400,
            "crowd_level": "High" if time_of_day in ('morning', 'afternoon') else "Low",
            "safety_note": "Bustling with students during the day; deserted after 8:30 PM.",
            "operating_hours": "07:00 AM - 08:30 PM"
        },
        {
            "name": "Tech Park Corridor & Metro Gate 2",
            "center": [12.9810, 77.6110],
            "radius_m": 350,
            "crowd_level": "High" if time_of_day in ('morning', 'evening') else "Moderate",
            "safety_note": "Security guards on duty; active cab stands and shuttle services.",
            "operating_hours": "06:00 AM - 11:30 PM"
        }
    ]

    return jsonify({
        "status": "success",
        "time_of_day": time_of_day,
        "zones": zones
    })
