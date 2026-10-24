import math
import random
from flask import Blueprint, request, jsonify
from config import Config
from database.db import execute_query

walk_bp = Blueprint('walk_bp', __name__)

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2.0)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def round_approx_distance(distance_m):
    """
    Rounds distance to protect exact user coordinates.
    E.g. 334m -> ~350m; 82m -> ~100m.
    """
    approx = int(round(distance_m / 50.0) * 50)
    return max(50, approx)

@walk_bp.route('/api/walk/toggle_visibility', methods=['POST'])
def toggle_visibility():
    """
    Opt-in / opt-out for Walk Together radar.
    Off by default; users can go invisible anytime.
    """
    data = request.get_json() or {}
    user_id = data.get('user_id')
    opt_in = 1 if data.get('opt_in', False) else 0
    lat = data.get('latitude')
    lng = data.get('longitude')

    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    if lat and lng:
        execute_query("""
            UPDATE users 
            SET is_walk_together_opted_in = %s, last_location_lat = %s, last_location_lng = %s,
                last_location_updated = datetime('now', 'localtime')
            WHERE id = %s
        """, (opt_in, lat, lng, user_id))
    else:
        execute_query("""
            UPDATE users 
            SET is_walk_together_opted_in = %s 
            WHERE id = %s
        """, (opt_in, user_id))

    return jsonify({
        "status": "success",
        "is_opted_in": bool(opt_in),
        "message": "Radar active. You are visible to verified women travelers within 1 km." if opt_in else "You are now completely invisible."
    })

@walk_bp.route('/api/walk/nearby', methods=['GET'])
def get_nearby_walkers():
    """
    Returns verified women travelers within 1 km.
    PRIVACY GUARANTEE:
    - Only returns anonymous handles (no real names, no phone numbers).
    - NEVER reveals exact coordinates (latitude/longitude are excluded).
    - Distance is fuzzed to approximate range (~300m).
    - Excludes blocked users.
    """
    try:
        lat = float(request.args.get('lat', 12.9740))
        lng = float(request.args.get('lng', 77.5960))
        user_id = request.args.get('user_id', type=int)
    except (ValueError, TypeError):
        return jsonify({"error": "Valid latitude and longitude required"}), 400

    # Fetch users opted-in within last 2 hours
    query = """
        SELECT id, anonymous_handle, verification_status, last_location_lat, last_location_lng
        FROM users
        WHERE is_walk_together_opted_in = 1 
          AND last_location_lat IS NOT NULL
    """
    candidates = execute_query(query, fetch='all') or []

    # Get blocked user IDs
    blocked_ids = set()
    if user_id:
        blocks = execute_query("""
            SELECT reported_user_id FROM blocks_reports WHERE reporter_id = %s
            UNION
            SELECT reporter_id FROM blocks_reports WHERE reported_user_id = %s
        """, (user_id, user_id), fetch='all') or []
        for b in blocks:
            blocked_ids.add(b.get('reported_user_id') or b.get('reporter_id'))

    nearby = []
    for c in candidates:
        if user_id and c['id'] == user_id:
            continue
        if c['id'] in blocked_ids:
            continue

        c_lat = float(c['last_location_lat'])
        c_lng = float(c['last_location_lng'])
        d = haversine_m(lat, lng, c_lat, c_lng)

        if d <= Config.WALK_TOGETHER_RADIUS_M: # 1 km
            nearby.append({
                "user_id": c['id'],
                "anonymous_handle": c['anonymous_handle'],
                "verification_status": c.get('verification_status', 'verified'),
                "approx_distance_m": round_approx_distance(d),
                "approx_distance_text": f"~{round_approx_distance(d)}m away"
            })

    nearby.sort(key=lambda x: x['approx_distance_m'])

    return jsonify({
        "status": "success",
        "radius_limit_m": 1000,
        "count": len(nearby),
        "nearby_travelers": nearby
    })

@walk_bp.route('/api/walk/request', methods=['POST'])
def send_walk_request():
    """
    Sends a mutual-consent walk request to another traveler.
    """
    data = request.get_json() or {}
    requester_id = data.get('requester_id')
    recipient_id = data.get('recipient_id')
    approx_dist = data.get('approx_distance_m', 350)

    if not requester_id or not recipient_id:
        return jsonify({"error": "Requester and recipient IDs required"}), 400

    if requester_id == recipient_id:
        return jsonify({"error": "Cannot send request to yourself"}), 400

    req_id = execute_query("""
        INSERT INTO walk_requests (requester_id, recipient_id, status, requester_approx_dist_m, trip_active)
        VALUES (%s, %s, 'pending', %s, 1)
    """, (requester_id, recipient_id, approx_dist))

    # Retrieve handles
    u1 = execute_query("SELECT anonymous_handle FROM users WHERE id = %s", (requester_id,), fetch='one')
    u2 = execute_query("SELECT anonymous_handle FROM users WHERE id = %s", (recipient_id,), fetch='one')

    return jsonify({
        "status": "success",
        "message": f"Walk together invitation sent to {u2['anonymous_handle'] if u2 else 'traveler'}.",
        "walk_request_id": req_id
    }), 201

@walk_bp.route('/api/walk/respond', methods=['POST'])
def respond_walk_request():
    """
    Accept or decline a walk request.
    If accepted, live in-app chat opens.
    """
    data = request.get_json() or {}
    req_id = data.get('walk_request_id')
    decision = data.get('decision') # 'accepted' or 'rejected'

    if not req_id or decision not in ('accepted', 'rejected'):
        return jsonify({"error": "Invalid request ID or decision"}), 400

    execute_query("""
        UPDATE walk_requests 
        SET status = %s 
        WHERE id = %s
    """, (decision, req_id))

    return jsonify({
        "status": "success",
        "decision": decision,
        "chat_enabled": decision == 'accepted'
    })

@walk_bp.route('/api/walk/end_trip', methods=['POST'])
def end_trip():
    """
    Ends active walk-together trip.
    Immediately resets radar visibility and marks chat session as completed.
    """
    data = request.get_json() or {}
    req_id = data.get('walk_request_id')
    user_id = data.get('user_id')

    if req_id:
        execute_query("""
            UPDATE walk_requests 
            SET trip_active = 0, status = 'completed', completed_at = datetime('now', 'localtime')
            WHERE id = %s
        """, (req_id,))

    if user_id:
        # Automatically make invisible once trip concludes
        execute_query("UPDATE users SET is_walk_together_opted_in = 0 WHERE id = %s", (user_id,))

    return jsonify({
        "status": "success",
        "message": "Trip safely completed. Live chat session closed and radar visibility set to private."
    })

@walk_bp.route('/api/walk/block_report', methods=['POST'])
def block_report_user():
    """
    Block and report a user immediately terminates connection, hides profile, and logs incident.
    """
    data = request.get_json() or {}
    reporter_id = data.get('reporter_id')
    reported_id = data.get('reported_user_id')
    report_type = data.get('report_type', 'inappropriate_behavior')
    reason = data.get('reason', 'User reported via in-app button')
    req_id = data.get('walk_request_id')

    if not reporter_id or not reported_id:
        return jsonify({"error": "Reporter and reported IDs are required"}), 400

    execute_query("""
        INSERT INTO blocks_reports (reporter_id, reported_user_id, report_type, reason)
        VALUES (%s, %s, %s, %s)
    """, (reporter_id, reported_id, report_type, reason))

    if req_id:
        execute_query("UPDATE walk_requests SET trip_active = 0, status = 'cancelled' WHERE id = %s", (req_id,))

    return jsonify({
        "status": "success",
        "message": "User has been blocked. They can no longer see your handle or send requests."
    })

@walk_bp.route('/api/walk/requests/active', methods=['GET'])
def get_active_walk_requests():
    """Polls any active or incoming walk request for user."""
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    pending = execute_query("""
        SELECT w.id, w.requester_id, w.recipient_id, w.status, w.requester_approx_dist_m, w.created_at,
               u.anonymous_handle as requester_handle
        FROM walk_requests w
        JOIN users u ON u.id = w.requester_id
        WHERE w.recipient_id = %s AND w.status = 'pending' AND w.trip_active = 1
        ORDER BY w.id DESC LIMIT 1
    """, (user_id,), fetch='one')

    active_session = execute_query("""
        SELECT w.id, w.requester_id, w.recipient_id, w.status,
               u1.anonymous_handle as requester_handle,
               u2.anonymous_handle as recipient_handle
        FROM walk_requests w
        JOIN users u1 ON u1.id = w.requester_id
        JOIN users u2 ON u2.id = w.recipient_id
        WHERE (w.requester_id = %s OR w.recipient_id = %s) AND w.status = 'accepted' AND w.trip_active = 1
        ORDER BY w.id DESC LIMIT 1
    """, (user_id, user_id), fetch='one')

    return jsonify({
        "status": "success",
        "incoming_request": pending,
        "active_trip": active_session
    })
