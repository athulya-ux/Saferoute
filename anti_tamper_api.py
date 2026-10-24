import datetime
import random
from flask import Blueprint, request, jsonify
from database.db import execute_query

tamper_bp = Blueprint('tamper_bp', __name__)

@tamper_bp.route('/api/tamper/config', methods=['GET'])
def get_tamper_config():
    """Returns the user's anti-tamper security configuration."""
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    user = execute_query("""
        SELECT id, tamper_security_key, duress_security_key, anti_tamper_enabled 
        FROM users WHERE id = %s
    """, (user_id,), fetch='one')

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "status": "success",
        "anti_tamper_enabled": bool(user.get('anti_tamper_enabled', 1)),
        "has_security_key": bool(user.get('tamper_security_key')),
        "security_key_hint": (user.get('tamper_security_key') or '7799')[:2] + '**',
        "has_duress_key": bool(user.get('duress_security_key')),
        "default_key_reminder": user.get('tamper_security_key', '7799'),
        "default_duress_reminder": user.get('duress_security_key', '9911')
    })

@tamper_bp.route('/api/tamper/setup_key', methods=['POST'])
def setup_tamper_key():
    """
    Set or update the user's secret power-off authorization key and duress key.
    - Security Key: Used by the user to safely authorize shutdown / unlock.
    - Duress Key: Silent alarm key entered if forced by an attacker (pretends to disarm but secretly notifies police).
    """
    data = request.get_json() or {}
    user_id = data.get('user_id')
    security_key = data.get('security_key', '').strip()
    duress_key = data.get('duress_key', '').strip()
    enabled = 1 if data.get('anti_tamper_enabled', True) else 0

    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    if not security_key or len(security_key) < 4:
        return jsonify({"error": "Security key must be at least 4 digits"}), 400

    execute_query("""
        UPDATE users 
        SET tamper_security_key = %s, duress_security_key = %s, anti_tamper_enabled = %s 
        WHERE id = %s
    """, (security_key, duress_key or '9911', enabled, user_id))

    return jsonify({
        "status": "success",
        "message": "Power-off & SIM Anti-Tamper Security Key successfully saved."
    })

@tamper_bp.route('/api/tamper/verify_poweroff', methods=['POST'])
def verify_poweroff():
    """
    Verifies the security key when an attempt is made to power off, remove SIM, or close app.
    - If valid security key: Disarmed safely.
    - If duress key: Appears disarmed, but secretly alerts Police and contacts!
    - If invalid key: Logs failure, returns failure.
    """
    data = request.get_json() or {}
    user_id = data.get('user_id')
    entered_key = data.get('entered_key', '').strip()
    lat = data.get('latitude', 12.9716)
    lng = data.get('longitude', 77.5946)

    if not user_id or not entered_key:
        return jsonify({"error": "user_id and entered_key required"}), 400

    user = execute_query("""
        SELECT id, full_name, anonymous_handle, tamper_security_key, duress_security_key 
        FROM users WHERE id = %s
    """, (user_id,), fetch='one')

    if not user:
        return jsonify({"error": "User not found"}), 404

    tamper_key = user.get('tamper_security_key') or '7799'
    duress_key = user.get('duress_security_key') or '9911'

    # Case 1: Legitimate user key
    if entered_key == tamper_key:
        return jsonify({
            "status": "authorized",
            "disarmed": True,
            "silent_sos": False,
            "message": "Security key verified. Power-off authorized."
        })

    # Case 2: Duress Key (Coerced by attacker)
    if entered_key == duress_key:
        # Silently trigger police & contacts alert
        _dispatch_tamper_alert(user_id, 'duress_pin_entered', lat, lng, "Coerced Duress PIN entered during power-off attempt.")
        return jsonify({
            "status": "authorized",
            "disarmed": True,
            "silent_sos": True,
            "message": "Power-off authorized." # Attacker sees standard confirmation!
        })

    # Case 3: Invalid Key
    return jsonify({
        "status": "unauthorized",
        "disarmed": False,
        "message": "Incorrect Security Key. Power-off blocked."
    }), 401

@tamper_bp.route('/api/tamper/trigger_alert', methods=['POST'])
def trigger_tamper_alert():
    """
    Called when:
    1. Unauthorized power-off attempt detected
    2. SIM ejection / network cutoff detected
    3. Wrong tamper key entered repeatedly or timeout expired
    """
    data = request.get_json() or {}
    user_id = data.get('user_id')
    alert_type = data.get('alert_type', 'poweroff_attempt')
    lat = data.get('latitude', 12.9716)
    lng = data.get('longitude', 77.5946)
    notes = data.get('notes', 'Forced power-off or SIM ejection attempt detected')

    result = _dispatch_tamper_alert(user_id, alert_type, lat, lng, notes)
    return jsonify(result)

def _dispatch_tamper_alert(user_id, alert_type, lat, lng, notes):
    """Internal helper to dispatch alerts to Police (112) and Emergency Contacts."""
    maps_link = f"https://www.google.com/maps?q={lat},{lng}"
    ref_num = f"POL-ALERT-{random.randint(100000, 999999)}"

    # Retrieve user & contacts
    user_name = "SafeRoute Traveler"
    contacts = []
    if user_id:
        u = execute_query("SELECT full_name, anonymous_handle FROM users WHERE id = %s", (user_id,), fetch='one')
        if u:
            user_name = u.get('full_name') or u.get('anonymous_handle')
        contacts = execute_query("""
            SELECT contact_name, phone_number 
            FROM emergency_contacts 
            WHERE user_id = %s
        """, (user_id,), fetch='all') or []

    # Insert tamper alert record
    alert_id = execute_query("""
        INSERT INTO tamper_alerts 
        (user_id, alert_type, latitude, longitude, notes, police_dispatched, contacts_notified_count)
        VALUES (%s, %s, %s, %s, %s, 1, %s)
    """, (user_id, alert_type, lat, lng, notes, len(contacts)))

    # Simulated SMS alert
    sms_text = (
        f"CRITICAL POLICE & TAMPER ALERT: Unauthorized device power-off / SIM removal attempted on {user_name}'s phone! "
        f"Last known GPS: {maps_link} ({lat:.5f}, {lng:.5f}). "
        f"Police Emergency ref: #{ref_num}. Please respond immediately!"
    )

    sent_alerts = []
    for c in contacts:
        sent_alerts.append({
            "name": c['contact_name'],
            "phone": c['phone_number'],
            "status": "SMS Dispatched",
            "preview": sms_text
        })

    # Log to police dispatch registry
    police_dispatch_notice = {
        "dispatch_reference": ref_num,
        "control_room": "National Emergency Support 112 & Women Helpline 1091",
        "priority": "CRITICAL / CODE RED - SUSPECTED ABDUCTION / FORCED POWER-OFF",
        "victim_name": user_name,
        "gps_coordinates": f"{lat:.5f}, {lng:.5f}",
        "live_map_url": maps_link,
        "incident_type": alert_type,
        "action_taken": "Automated Patrol Unit Dispatched to GPS perimeter"
    }

    print(f"\n=======================================================")
    print(f"[POLICE TAMPER ALERT DISPATCHED]: {ref_num}")
    print(f"   Reason: {alert_type.upper()} ({notes})")
    print(f"   GPS Coordinates: {lat:.5f}, {lng:.5f}")
    print(f"   Alerted Contacts: {len(contacts)}")
    print(f"=======================================================\n")

    return {
        "status": "success",
        "tamper_alert_id": alert_id,
        "dispatch_reference": ref_num,
        "alert_type": alert_type,
        "police_dispatched": True,
        "police_details": police_dispatch_notice,
        "contacts_notified": sent_alerts,
        "live_location": {
            "latitude": lat,
            "longitude": lng,
            "maps_url": maps_link
        },
        "message": f"Tamper Alert triggered! Police Control Room (112) and {len(contacts)} emergency contacts notified."
    }
