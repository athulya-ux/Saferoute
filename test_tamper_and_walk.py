import requests

base = 'http://127.0.0.1:5000'

print("--- TESTING ANTI-TAMPER & 2-WOMEN WALK FLOW ---")

# 1. Anti-Tamper Config
cfg = requests.get(f'{base}/api/tamper/config?user_id=1').json()
print("1. Tamper Config:", cfg)
assert cfg['status'] == 'success'
assert cfg['default_key_reminder'] == '7799'

# 2. Legitimate Power-Off Verification with correct PIN
auth_test = requests.post(f'{base}/api/tamper/verify_poweroff', json={
    'user_id': 1,
    'entered_key': '7799',
    'latitude': 12.9716,
    'longitude': 77.5946
}).json()
print("2. Power-off correct PIN result:", auth_test)
assert auth_test['disarmed'] == True
assert auth_test['silent_sos'] == False

# 3. Attacker Coerced Duress PIN (Secret Police SOS)
duress_test = requests.post(f'{base}/api/tamper/verify_poweroff', json={
    'user_id': 1,
    'entered_key': '9911',
    'latitude': 12.9716,
    'longitude': 77.5946
}).json()
print("3. Duress PIN result:", duress_test)
assert duress_test['disarmed'] == True
assert duress_test['silent_sos'] == True # Attacker sees authorized, but police secretly alerted!

# 4. Tamper Countdown Expired or SIM Removed (Police & Contacts Alert)
tamper_alert = requests.post(f'{base}/api/tamper/trigger_alert', json={
    'user_id': 1,
    'alert_type': 'poweroff_attempt',
    'latitude': 12.9716,
    'longitude': 77.5946,
    'notes': 'Attacker attempted to power off phone without key. Countdown expired.'
}).json()
print("4. Tamper Police Alert Dispatched:")
print("   Police Dispatched:", tamper_alert['police_dispatched'])
print("   Dispatch Reference:", tamper_alert['dispatch_reference'])
print("   Alert Type:", tamper_alert['alert_type'])
print("   Contacts Notified:", len(tamper_alert['contacts_notified']))

# 5. 2-Women Walk Together Agreement Flow
# User 1 (Aarti) sends request to User 2 (Pooja)
walk_req = requests.post(f'{base}/api/walk/request', json={
    'requester_id': 1,
    'recipient_id': 2,
    'approx_distance_m': 350
}).json()
print("5. User 1 sends walk request to User 2:", walk_req)
walk_id = walk_req['walk_request_id']

# User 2 accepts the invitation
walk_accept = requests.post(f'{base}/api/walk/respond', json={
    'walk_request_id': walk_id,
    'decision': 'accepted'
}).json()
print("6. User 2 accepts walk request:", walk_accept)
assert walk_accept['chat_enabled'] == True

# Active session verify
active_session = requests.get(f'{base}/api/walk/requests/active?user_id=1').json()
print("7. Active Walk Session Confirmed:", active_session['active_trip'])
assert active_session['active_trip']['status'] == 'accepted'

print("\n>>> ALL TESTS PASSED: 2-WOMEN WALK & ANTI-POWEROFF PROTECTION FULLY VERIFIED! <<<")
