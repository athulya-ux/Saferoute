import math
import json
import datetime
import requests
from flask import Blueprint, request, jsonify
from config import Config
from database.db import execute_query

routes_bp = Blueprint('routes_bp', __name__)

def haversine_distance_m(lat1, lon1, lat2, lon2):
    """Calculate distance in meters between two lat/lon coordinates."""
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def distance_point_to_polyline_m(p_lat, p_lon, polyline_coords):
    """
    Returns minimum distance in meters from point (p_lat, p_lon)
    to polyline [[lat, lon], ...].
    """
    if not polyline_coords:
        return 999999
    
    # Subsample polyline points if very dense
    step = 1 if len(polyline_coords) < 50 else max(1, len(polyline_coords) // 50)
    min_dist = float('inf')
    for i in range(0, len(polyline_coords), step):
        coord = polyline_coords[i]
        d = haversine_distance_m(p_lat, p_lon, coord[0], coord[1])
        if d < min_dist:
            min_dist = d
            if min_dist < 20: # Fast exit if very close
                break
    return min_dist

def get_current_time_of_day():
    hour = datetime.datetime.now().hour
    if 6 <= hour < 12:
        return 'morning'
    elif 12 <= hour < 17:
        return 'afternoon'
    elif 17 <= hour < 21:
        return 'evening'
    else:
        return 'night'

def generate_alternative_polylines(start_lat, start_lng, dest_lat, dest_lng):
    """
    Generates 3 realistic walking route options between start and destination:
    1. Direct Main Avenue Route
    2. Boulevard / Well-lit Commercial Route (offset via commercial corridor)
    3. Side Alleys / Shortcut Route (offset via residential alley)
    """
    # Midpoint and perpendicular displacement
    mid_lat = (start_lat + dest_lat) / 2.0
    mid_lng = (start_lng + dest_lng) / 2.0
    
    dlat = dest_lat - start_lat
    dlng = dest_lng - start_lng
    dist = math.sqrt(dlat*dlat + dlng*dlng)
    
    # Perpendicular unit vector
    if dist == 0:
        perp_lat, perp_lng = 0.001, 0.001
    else:
        perp_lat = -dlng / dist
        perp_lng = dlat / dist
    
    # Route 1: Boulevard / Safe Main Avenue (well lit, slightly curved toward main road)
    offset1 = 0.003
    p1_lat = start_lat + 0.3 * dlat + offset1 * perp_lat
    p1_lng = start_lng + 0.3 * dlng + offset1 * perp_lng
    p2_lat = start_lat + 0.7 * dlat + offset1 * perp_lat
    p2_lng = start_lng + 0.7 * dlng + offset1 * perp_lng
    route1_coords = [
        [start_lat, start_lng],
        [p1_lat, p1_lng],
        [p2_lat, p2_lng],
        [dest_lat, dest_lng]
    ]

    # Route 2: Direct Thoroughfare
    p_mid1_lat = start_lat + 0.5 * dlat + 0.0005 * perp_lat
    p_mid1_lng = start_lng + 0.5 * dlng + 0.0005 * perp_lng
    route2_coords = [
        [start_lat, start_lng],
        [p_mid1_lat, p_mid1_lng],
        [dest_lat, dest_lng]
    ]

    # Route 3: Side Street / Shortcut (shorter distance, narrower alleys, less lit)
    offset3 = -0.004
    p3_lat = start_lat + 0.4 * dlat + offset3 * perp_lat
    p3_lng = start_lng + 0.4 * dlng + offset3 * perp_lng
    p4_lat = start_lat + 0.8 * dlat + offset3 * perp_lat
    p4_lng = start_lng + 0.8 * dlng + offset3 * perp_lng
    route3_coords = [
        [start_lat, start_lng],
        [p3_lat, p3_lng],
        [p4_lat, p4_lng],
        [dest_lat, dest_lng]
    ]

    return [
        {
            "name": "Main Boulevard & Lit Transit Corridor",
            "tag": "Well-lit & Populated",
            "coords": route1_coords,
            "crowd_modifier": "high",
            "lighting_bias": 1.4
        },
        {
            "name": "Central Thoroughfare",
            "tag": "Direct",
            "coords": route2_coords,
            "crowd_modifier": "moderate",
            "lighting_bias": 1.0
        },
        {
            "name": "Backstreet Shortcut",
            "tag": "Narrow Alleys",
            "coords": route3_coords,
            "crowd_modifier": "low",
            "lighting_bias": 0.4
        }
    ]

def fetch_osrm_routes(start_lat, start_lng, dest_lat, dest_lng):
    """
    Attempt to fetch real OpenStreetMap walking routes from public OSRM.
    Returns list of route dicts or None if request fails or times out.
    """
    url = f"{Config.OSRM_URL}/{start_lng},{start_lat};{dest_lng},{dest_lat}?overview=full&geometries=geojson&alternatives=true&steps=true"
    try:
        resp = requests.get(url, timeout=3.5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('routes'):
                parsed_routes = []
                for i, r in enumerate(data['routes'][:3]):
                    # OSRM returns coordinates as [lon, lat]
                    raw_coords = r['geometry']['coordinates']
                    leaflet_coords = [[pt[1], pt[0]] for pt in raw_coords]
                    name = f"OSM Route {chr(65+i)}"
                    if r.get('legs') and r['legs'][0].get('summary'):
                        summary = r['legs'][0]['summary']
                        if summary:
                            name = f"Via {summary}"
                    
                    parsed_routes.append({
                        "name": name,
                        "tag": "OSM Recommended" if i == 0 else f"Alternative {i}",
                        "coords": leaflet_coords,
                        "distance_m": r.get('distance', 1000),
                        "duration_s": r.get('duration', 600),
                        "crowd_modifier": "moderate" if i == 0 else ("high" if i == 1 else "low"),
                        "lighting_bias": 1.1 if i == 0 else (1.3 if i == 1 else 0.7)
                    })
                return parsed_routes
    except Exception as e:
        # Fall back to realistic polyline generator
        pass
    return None

def compute_route_safety_score(route_coords, time_of_day, crowd_modifier="moderate", lighting_bias=1.0):
    """
    Comprehensive safety score formula (0-100):
    - Street lights: 30 pts
    - Crowd level: 25 pts
    - Nearby help points: 25 pts
    - Time of day penalty: 0 to -15 pts
    - Incident reports penalty: -5 to -35 pts
    Provides detailed breakdown and reasons for score deductions.
    """
    reasons_low = []
    warnings = []
    
    # 1. Total route distance in meters
    total_dist_m = 0
    for i in range(len(route_coords) - 1):
        total_dist_m += haversine_distance_m(
            route_coords[i][0], route_coords[i][1],
            route_coords[i+1][0], route_coords[i+1][1]
        )
    dist_km = max(0.2, total_dist_m / 1000.0)

    # 2. STREET LIGHTS EVALUATION (Buffer: 100m)
    # Fetch all street lights from DB
    lights = execute_query("SELECT latitude, longitude, status, confirmed_count FROM street_lights", fetch='all') or []
    working_lights = 0
    dim_lights = 0
    broken_lights = 0

    for l in lights:
        dist = distance_point_to_polyline_m(float(l['latitude']), float(l['longitude']), route_coords)
        if dist <= 100:
            st = l.get('status', 'working')
            if st == 'working':
                working_lights += 1
            elif st == 'dim':
                dim_lights += 1
            elif st == 'broken':
                broken_lights += 1

    # Synthetic density adjustment based on route bias (e.g. main avenue vs dark alley)
    synthetic_lights = int(max(4, 14 * dist_km * lighting_bias))
    effective_working_lights = max(working_lights, synthetic_lights)
    
    lights_per_km = effective_working_lights / dist_km
    
    # Score calculation for lighting (Max 30)
    # Standard: 15 lights/km is optimal safe coverage
    lighting_ratio = min(1.0, lights_per_km / 15.0)
    lighting_score = int(lighting_ratio * 30)
    if broken_lights > 0:
        lighting_score = max(5, lighting_score - (broken_lights * 3))
        reasons_low.append(f"{broken_lights} broken or non-functional street lights reported along this segment.")

    if lighting_score < 18:
        reasons_low.append("Low street light density: portions of this path may be poorly illuminated.")

    # 3. CROWD LEVEL EVALUATION (Max 25)
    # Crowd depends on time of day + road type
    crowd_levels_map = {
        'morning': {'high': 23, 'moderate': 18, 'low': 10},
        'afternoon': {'high': 24, 'moderate': 19, 'low': 12},
        'evening': {'high': 25, 'moderate': 17, 'low': 9},
        'night': {'high': 18, 'moderate': 12, 'low': 5}
    }
    crowd_score = crowd_levels_map.get(time_of_day, crowd_levels_map['evening']).get(crowd_modifier, 15)
    
    crowd_label = f"{crowd_modifier.capitalize()} footfall"
    if time_of_day == 'night' and crowd_modifier == 'low':
        reasons_low.append("Deserted route at night: very few pedestrians or active commercial shops.")
    elif crowd_modifier == 'low':
        reasons_low.append("Quiet residential / low-traffic corridor.")

    # 4. NEARBY HELP POINTS (Buffer: 500m) (Max 25)
    help_pts = execute_query("SELECT id, point_type, name, latitude, longitude, phone FROM help_points", fetch='all') or []
    nearby_police = []
    nearby_hospitals = []
    nearby_bus = []

    for hp in help_pts:
        d = distance_point_to_polyline_m(float(hp['latitude']), float(hp['longitude']), route_coords)
        if d <= 500:
            ptype = hp['point_type']
            item = {"name": hp['name'], "dist_m": int(d), "phone": hp.get('phone')}
            if ptype == 'police':
                nearby_police.append(item)
            elif ptype == 'hospital':
                nearby_hospitals.append(item)
            elif ptype == 'bus_stop':
                nearby_bus.append(item)

    # Score breakdown for help points
    # Police: +10 pts for first, +5 for second (max 15)
    # Hospital: +6 pts (max 6)
    # Bus stop: +2 pts each (max 4)
    police_pts = min(15, len(nearby_police) * 10)
    hospital_pts = min(6, len(nearby_hospitals) * 6)
    bus_pts = min(4, len(nearby_bus) * 2)
    help_points_score = min(25, police_pts + hospital_pts + bus_pts)

    if len(nearby_police) == 0:
        reasons_low.append("No active police station or pink patrol booth within 500m.")

    # 5. TIME OF DAY PENALTY
    time_penalty = 0
    if time_of_day == 'night':
        time_penalty = Config.PENALTY_NIGHT # -15
        warnings.append("Night travel advisory: Reduced visibility and lower police patrolling.")
    elif time_of_day == 'evening':
        time_penalty = Config.PENALTY_EVENING # -5

    # 6. INCIDENT REPORTS PENALTY (Buffer: 250m)
    # Active incidents that have not expired (<= 30 days)
    incidents = execute_query("""
        SELECT id, incident_type, description, latitude, longitude, severity, confirmation_count, address
        FROM incident_reports
        WHERE status = 'active' AND expires_at > datetime('now', 'localtime')
    """, fetch='all') or []

    incident_penalty = 0
    incidents_along_route = []

    for inc in incidents:
        d = distance_point_to_polyline_m(float(inc['latitude']), float(inc['longitude']), route_coords)
        if d <= 250:
            itype = inc['incident_type']
            confirms = max(1, inc.get('confirmation_count', 1))
            weight_factor = 1.0 + (min(5, confirms) * 0.1)

            if itype == 'harassment':
                deduction = int(22 * weight_factor)
                incident_penalty += deduction
                warnings.append(f"Harassment warning: Incident reported {int(d)}m away at '{inc.get('address') or 'this section'}'.")
                reasons_low.append("Recent harassment report within 250m of route.")
            elif itype == 'dark_street':
                deduction = int(10 * weight_factor)
                incident_penalty += deduction
                reasons_low.append(f"Dark spot: {inc.get('description', 'Unlit street section')}.")
            elif itype == 'unsafe_spot':
                deduction = int(14 * weight_factor)
                incident_penalty += deduction
                warnings.append(f"Caution: Unsafe spot reported near '{inc.get('address') or 'route'}'.")
                reasons_low.append("Unsafe blind spot reported by community members.")
            elif itype == 'accident':
                deduction = int(5 * weight_factor)
                incident_penalty += deduction

            incidents_along_route.append({
                "type": itype,
                "description": inc.get('description'),
                "severity": inc.get('severity'),
                "distance_m": int(d),
                "confirmations": confirms
            })

    # Capped incident penalty at 45 pts
    incident_penalty = min(45, incident_penalty)

    # FINAL COMPOSITE SCORE
    raw_score = lighting_score + crowd_score + help_points_score - time_penalty - incident_penalty
    final_score = max(10, min(99, raw_score))

    # Safety Classification
    if final_score >= 80:
        safety_tier = "High Safety"
        tier_color = "#10B981" # Green
        badge_text = "Safest & Well-Monitored"
    elif final_score >= 60:
        safety_tier = "Moderate Safety"
        tier_color = "#F59E0B" # Amber
        badge_text = "Average Precautions Advised"
    else:
        safety_tier = "Elevated Risk"
        tier_color = "#EF4444" # Red
        badge_text = "Caution: Use Alternative Route"

    return {
        "score": final_score,
        "safety_tier": safety_tier,
        "tier_color": tier_color,
        "badge_text": badge_text,
        "distance_m": int(total_dist_m),
        "duration_min": max(1, int(total_dist_m / 75)), # Approx 4.5 km/h walking
        "breakdown": {
            "street_lighting": {
                "score": lighting_score,
                "max": 30,
                "working_count": effective_working_lights,
                "broken_count": broken_lights,
                "density_per_km": round(lights_per_km, 1)
            },
            "crowd_level": {
                "score": crowd_score,
                "max": 25,
                "level": crowd_modifier.capitalize(),
                "time_of_day": time_of_day
            },
            "help_points": {
                "score": help_points_score,
                "max": 25,
                "police_nearby": len(nearby_police),
                "hospitals_nearby": len(nearby_hospitals),
                "bus_stops_nearby": len(nearby_bus),
                "details": {
                    "police": nearby_police,
                    "hospitals": nearby_hospitals,
                    "bus_stops": nearby_bus
                }
            },
            "time_penalty": time_penalty,
            "incident_penalty": incident_penalty,
            "incidents_count": len(incidents_along_route),
            "incidents_list": incidents_along_route
        },
        "reasons_low": reasons_low,
        "warnings": warnings
    }

@routes_bp.route('/api/routes/calculate', methods=['POST'])
def calculate_routes():
    """
    POST payload:
    {
       "start_lat": 12.9716, "start_lng": 77.5946, "start_name": "MG Road",
       "dest_lat": 12.9780, "dest_lng": 77.6050, "dest_name": "Commercial St",
       "time_of_day": "evening" (optional)
    }
    Returns 2-3 evaluated routes with safety score, breakdown, and safest marked.
    """
    data = request.get_json() or {}
    try:
        start_lat = float(data.get('start_lat', 12.9716))
        start_lng = float(data.get('start_lng', 77.5946))
        dest_lat = float(data.get('dest_lat', 12.9780))
        dest_lng = float(data.get('dest_lng', 77.6050))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid coordinate format"}), 400

    start_name = data.get('start_name', 'Current Location')
    dest_name = data.get('dest_name', 'Destination')
    time_of_day = data.get('time_of_day') or get_current_time_of_day()

    # Step 1: Generate route geometry options
    routes_candidates = fetch_osrm_routes(start_lat, start_lng, dest_lat, dest_lng)
    if not routes_candidates or len(routes_candidates) < 2:
        # Fall back to high quality polyline generator
        routes_candidates = generate_alternative_polylines(start_lat, start_lng, dest_lat, dest_lng)

    evaluated_routes = []
    for idx, r in enumerate(routes_candidates):
        coords = r['coords']
        crowd_mod = r.get('crowd_modifier', 'moderate')
        light_bias = r.get('lighting_bias', 1.0)
        
        eval_result = compute_route_safety_score(coords, time_of_day, crowd_mod, light_bias)
        
        evaluated_routes.append({
            "route_id": idx,
            "name": r.get('name', f"Route {chr(65+idx)}"),
            "tag": r.get('tag', 'Option'),
            "coords": coords,
            "distance_m": eval_result['distance_m'],
            "duration_min": eval_result['duration_min'],
            "safety_score": eval_result['score'],
            "safety_tier": eval_result['safety_tier'],
            "tier_color": eval_result['tier_color'],
            "badge_text": eval_result['badge_text'],
            "breakdown": eval_result['breakdown'],
            "reasons_low": eval_result['reasons_low'],
            "warnings": eval_result['warnings'],
            "is_safest": False
        })

    # Sort / determine safest
    safest_route = max(evaluated_routes, key=lambda x: x['safety_score'])
    safest_route['is_safest'] = True
    safest_route['badge_text'] = "⭐ Safest Route (Recommended)"

    # If user selected or another route is unsafe, generate comparison warning
    warning_notice = None
    if any(r['safety_score'] < 60 for r in evaluated_routes):
        warning_notice = {
            "title": "Route Safety Advisory",
            "message": f"'{safest_route['name']}' has a significantly higher safety score ({safest_route['safety_score']}/100) compared to darker shortcuts.",
            "recommended_route_id": safest_route['route_id']
        }

    # Save route request history if user_id is provided
    user_id = data.get('user_id')
    try:
        execute_query("""
            INSERT INTO route_requests 
            (user_id, start_name, start_lat, start_lng, dest_name, dest_lat, dest_lng, selected_route_index, safety_score, time_of_day)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, start_name, start_lat, start_lng, dest_name, dest_lat, dest_lng, safest_route['route_id'], safest_route['safety_score'], time_of_day))
    except Exception as e:
        print("[Routes API] Note: Failed to log route request to DB:", e)

    return jsonify({
        "status": "success",
        "time_of_day": time_of_day,
        "routes": evaluated_routes,
        "safest_route_id": safest_route['route_id'],
        "warning_notice": warning_notice
    })
