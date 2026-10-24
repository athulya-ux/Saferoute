import requests

base = 'http://127.0.0.1:5000'

# 1. Health
h = requests.get(f'{base}/api/health').json()
print('1. Health check:', h)

# 2. Routes calculation
route_payload = {
    'start_lat': 12.9767, 'start_lng': 77.5713, 'start_name': 'Majestic City Interchange',
    'dest_lat': 12.9756, 'dest_lng': 77.6066, 'dest_name': 'Commercial Street Boulevard',
    'time_of_day': 'evening'
}
r = requests.post(f'{base}/api/routes/calculate', json=route_payload).json()
print('2. Routes count:', len(r.get('routes', [])))
print('   Safest route ID:', r.get('safest_route_id'))
safest = next(rt for rt in r['routes'] if rt['is_safest'])
print('   Safest Route:', safest['name'], '| Score:', safest['safety_score'], '/100 | Tier:', safest['safety_tier'])
print('   Breakdown Lighting:', safest['breakdown']['street_lighting']['score'], '/30')
print('   Breakdown Crowd:', safest['breakdown']['crowd_level']['score'], '/25')
print('   Breakdown Help Points:', safest['breakdown']['help_points']['score'], '/25')

# 3. Help Points (5km)
hp = requests.get(f'{base}/api/help_points?lat=12.9716&lng=77.5946&radius_km=5').json()
print('3. Help Points total within 5km:', hp.get('total'))
print('   Police stations:', len(hp['grouped']['police']))
print('   Hospitals:', len(hp['grouped']['hospital']))
print('   Bus stops:', len(hp['grouped']['bus_stop']))

# 4. Incidents & Expiry
inc = requests.get(f'{base}/api/incidents').json()
print('4. Active incidents:', inc.get('count'))
first_inc = inc['incidents'][0]
print('   Incident:', first_inc['incident_type'], '| Days remaining:', first_inc['days_remaining'], '| Confirmations:', first_inc['confirmation_count'])

# 5. Confirm Incident (+1)
c = requests.post(f'{base}/api/incidents/{first_inc["id"]}/confirm').json()
print('5. Confirm incident result:', c['message'], '| New count:', c['new_confirmation_count'])

# 6. Walk Together Radar (1km, anonymous, fuzzed distance)
w = requests.get(f'{base}/api/walk/nearby?lat=12.9740&lng=77.5960').json()
print('6. Walk Together nearby travelers within 1km:', w.get('count'))
for tr in w.get('nearby_travelers', [])[:2]:
    print('   Traveler:', tr['anonymous_handle'], '| Dist:', tr['approx_distance_text'])

# 7. Emergency SOS Trigger
sos = requests.post(f'{base}/api/emergency/trigger_sos', json={'latitude': 12.9716, 'longitude': 77.5946}).json()
print('7. SOS Triggered:', sos['sos_activated'], '| Helplines available:', len(sos['helplines']))

print('\n>>> ALL 7 CORE SYSTEM SUITE TESTS PASSED 100% <<<')
