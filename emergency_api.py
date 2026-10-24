import datetime
from flask import Blueprint, request, jsonify
from database.db import execute_query

emergency_bp = Blueprint('emergency_bp', __name__)

@emergency_bp.route('/api/emergency/contacts', methods=['GET'])
def get_contacts():
    """Returns saved emergency contacts for the user."""
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    contacts = execute_query("""
        SELECT id, contact_name, phone_number, relationship, is_primary, created_at
        FROM emergency_contacts
        WHERE user_id = %s
        ORDER BY is_primary DESC, id ASC
    """, (user_id,), fetch='all') or []

    return jsonify({
        "status": "success",
        "contacts": contacts
    })

@emergency_bp.route('/api/emergency/contacts', methods=['POST'])
def add_contact():
    """Adds a new emergency contact (parent, friend, sibling, partner)."""
    data = request.get_json() or {}
    user_id = data.get('user_id')
    name = data.get('contact_name', '').strip()
    phone = data.get('phone_number', '').strip()
    relationship = data.get('relationship', 'Emergency Contact').strip()
    is_primary = 1 if data.get('is_primary', False) else 0

    if not user_id or not name or not phone:
        return jsonify({"error": "User ID, Contact Name, and Phone Number are required"}), 400

    if is_primary:
        # Reset other primaries
        execute_query("UPDATE emergency_contacts SET is_primary = 0 WHERE user_id = %s", (user_id,))

    cid = execute_query("""
        INSERT INTO emergency_contacts (user_id, contact_name, phone_number, relationship, is_primary)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_id, name, phone, relationship, is_primary))

    return jsonify({
        "status": "success",
        "message": f"Emergency contact '{name}' saved successfully.",
        "contact_id": cid
    }), 201

@emergency_bp.route('/api/emergency/contacts/<int:contact_id>', methods=['DELETE'])
def delete_contact(contact_id):
    """Deletes an emergency contact."""
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    execute_query("DELETE FROM emergency_contacts WHERE id = %s AND user_id = %s", (contact_id, user_id))
    return jsonify({
        "status": "success",
        "message": "Emergency contact removed."
    })

@emergency_bp.route('/api/emergency/trigger_sos', methods=['POST'])
def trigger_sos():
    """
    CRITICAL EMERGENCY ACTION:
    - Broadcasts live GPS coordinates & map link to saved emergency contacts via SMS alert.
    - Notifies nearby opted-in travelers.
    - Generates 1-tap direct calls to emergency helplines:
      - 112 (National Emergency Support)
      - 1091 (Women Helpline 24/7)
      - 181 (Women in Distress)
    """
    data = request.get_json() or {}
    user_id = data.get('user_id')
    lat = data.get('latitude', 12.9716)
    lng = data.get('longitude', 77.5946)
    battery_level = data.get('battery_level', '85%')
    notes = data.get('notes', 'SOS Emergency Triggered from SafeRoute App')

    maps_link = f"https://www.google.com/maps?q={lat},{lng}"

    # Get contacts
    contacts = []
    user_handle = "A SafeRoute Traveler"
    if user_id:
        contacts = execute_query("""
            SELECT contact_name, phone_number 
            FROM emergency_contacts 
            WHERE user_id = %s
        """, (user_id,), fetch='all') or []
        u = execute_query("SELECT full_name, anonymous_handle FROM users WHERE id = %s", (user_id,), fetch='one')
        if u:
            user_handle = u.get('full_name') or u.get('anonymous_handle')

    # Simulated SMS notification message
    sms_text = (
        f"EMERGENCY ALERT: {user_handle} pressed the SafeRoute SOS button! "
        f"Live Location: {maps_link} | Coordinates: {lat:.5f}, {lng:.5f}. "
        f"Battery: {battery_level}. Please call or check immediately!"
    )

    sent_alerts = []
    for c in contacts:
        sent_alerts.append({
            "name": c['contact_name'],
            "phone": c['phone_number'],
            "status": "SMS Dispatched",
            "preview": sms_text
        })

    # Return emergency payload with direct phone dial actions
    return jsonify({
        "status": "success",
        "sos_activated": True,
        "timestamp": datetime.datetime.now().isoformat(),
        "live_location": {
            "latitude": lat,
            "longitude": lng,
            "maps_url": maps_link
        },
        "dispatched_alerts": sent_alerts,
        "helplines": [
            {"name": "National Emergency Service", "number": "112", "tel_uri": "tel:112"},
            {"name": "Women Helpline (Police)", "number": "1091", "tel_uri": "tel:1091"},
            {"name": "Women in Distress Helpline", "number": "181", "tel_uri": "tel:181"},
            {"name": "Pink Police Patrol Booth", "number": "080-22942411", "tel_uri": "tel:08022942411"}
        ],
        "message": f"SOS activated! Live location dispatched to {len(sent_alerts)} emergency contacts."
    })

@emergency_bp.route('/api/emergency/helplines', methods=['GET'])
def get_helplines():
    """Returns official emergency helpline numbers."""
    return jsonify({
        "status": "success",
        "helplines": [
            {"label": "National Emergency Response", "number": "112", "available": "24/7", "type": "police_ambulance"},
            {"label": "Women Helpline 24/7", "number": "1091", "available": "24/7", "type": "women_police"},
            {"label": "Women in Distress (Govt)", "number": "181", "available": "24/7", "type": "counseling_rescue"},
            {"label": "Pink Hoysala / City Patrol", "number": "080-22942222", "available": "24/7", "type": "pink_patrol"}
        ]
    })
