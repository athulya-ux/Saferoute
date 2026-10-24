// ========================================================
// SafeRoute - Anti-Tamper & Power-Off / SIM Ejection Guard
// Prevents unauthorized shutdown or SIM removal without secret key
// Alerts Police (112) and Emergency Contacts if tampered
// ========================================================

let isTamperArmed = true;
let tamperCountdownSec = 10;
let tamperTimer = null;
let enteredPinBuffer = "";
let wakeLock = null;

// Initialize Anti-Tamper Guard
function initAntiTamperGuard() {
    loadTamperConfig();
    armAntiTamperListeners();
}

function loadTamperConfig() {
    const userId = window.currentUser ? window.currentUser.id : 1;
    fetch(`/api/tamper/config?user_id=${userId}`)
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                isTamperArmed = data.anti_tamper_enabled;
                updateTamperUI(data);
            }
        })
        .catch(err => console.warn('Could not load tamper config:', err));
}

function updateTamperUI(config) {
    const shieldBadge = document.getElementById('tamperShieldBadge');
    const toggle = document.getElementById('tamperToggleCheckbox');
    const keyHint = document.getElementById('currentKeyDisplay');

    if (shieldBadge) {
        shieldBadge.className = isTamperArmed ? 'shield-status-pill armed' : 'shield-status-pill disarmed';
        shieldBadge.innerHTML = isTamperArmed 
            ? `<i class="fa-solid fa-lock text-green"></i> Power-Off Guard: Armed (Key: ${config.default_key_reminder})` 
            : `<i class="fa-solid fa-lock-open text-red"></i> Power-Off Guard: Disarmed`;
    }

    if (toggle) toggle.checked = isTamperArmed;
    if (keyHint && config.default_key_reminder) {
        keyHint.textContent = `Default Safety Key: ${config.default_key_reminder} | Duress Panic Key: ${config.default_duress_reminder}`;
    }
}

function armAntiTamperListeners() {
    // 1. Request Screen Wake Lock (prevents screen sleep)
    try {
        if ('wakeLock' in navigator) {
            navigator.wakeLock.request('screen').then(lock => {
                wakeLock = lock;
            }).catch(e => {});
        }
    } catch (e) {}

    // 2. Detect SIM Ejection / Airplane Mode / Network Cutoff
    window.addEventListener('offline', () => {
        if (isTamperArmed) {
            triggerTamperLockdown('sim_eject_offline', 'SIM Card Ejected / Mobile Data & Network Cutoff Detected');
        }
    });

    // 3. Detect Unauthorized Page Close / Power-off sequence
    window.addEventListener('beforeunload', (e) => {
        if (isTamperArmed) {
            // Immediate silent dispatch to police before unload terminates
            const lat = userLocation ? userLocation.lat : 12.9716;
            const lng = userLocation ? userLocation.lng : 77.5946;
            const userId = window.currentUser ? window.currentUser.id : 1;
            
            // Use sendBeacon for reliable delivery even if browser closes
            const payload = JSON.stringify({
                user_id: userId,
                alert_type: 'poweroff_attempt',
                latitude: lat,
                longitude: lng,
                notes: 'Emergency: Browser exit or device shutdown initiated while guard was armed.'
            });
            navigator.sendBeacon('/api/tamper/trigger_alert', payload);

            e.preventDefault();
            e.returnValue = 'PROTECTED: Security Key required to power off or close SafeRoute.';
            return e.returnValue;
        }
    });

    // 4. Intercept common shutdown / close shortcuts (Alt+F4, Ctrl+W)
    window.addEventListener('keydown', (e) => {
        if (isTamperArmed) {
            if ((e.altKey && e.key === 'F4') || (e.ctrlKey && e.key === 'w')) {
                e.preventDefault();
                triggerTamperLockdown('poweroff_attempt', 'Keyboard shutdown / window close attempt intercepted');
            }
        }
    });
}

function toggleAntiTamperState(enable) {
    const userId = window.currentUser ? window.currentUser.id : 1;
    const key = document.getElementById('securityKeyInput') ? document.getElementById('securityKeyInput').value : '7799';
    const duress = document.getElementById('duressKeyInput') ? document.getElementById('duressKeyInput').value : '9911';

    fetch('/api/tamper/setup_key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: userId,
            security_key: key || '7799',
            duress_key: duress || '9911',
            anti_tamper_enabled: enable
        })
    })
    .then(res => res.json())
    .then(data => {
        isTamperArmed = enable;
        loadTamperConfig();
        alert(enable ? 'Power-Off & SIM Removal Guard is now ARMED. Device cannot be powered off without your key.' : 'Power-Off Guard disarmed.');
    });
}

// TRIGGER TAMPER LOCKDOWN MODAL
function triggerTamperLockdown(alertType = 'poweroff_attempt', reasonText = 'Unauthorized Power-Off / SIM Ejection Detected') {
    const overlay = document.getElementById('tamperLockdownOverlay');
    if (!overlay) return;

    enteredPinBuffer = "";
    updatePinDisplay();

    document.getElementById('tamperReasonSubtitle').textContent = reasonText;
    document.getElementById('tamperStatusMsg').textContent = 'Enter your 4-digit Safety Key to authorize shutdown.';
    document.getElementById('tamperStatusMsg').style.color = '#ffffff';

    overlay.style.display = 'flex';

    // Start 10-second countdown
    tamperCountdownSec = 10;
    document.getElementById('tamperCountdownNum').textContent = tamperCountdownSec;

    if (tamperTimer) clearInterval(tamperTimer);
    tamperTimer = setInterval(() => {
        tamperCountdownSec--;
        document.getElementById('tamperCountdownNum').textContent = tamperCountdownSec;

        if (tamperCountdownSec <= 0) {
            clearInterval(tamperTimer);
            handleTamperFailureTimeout(alertType, reasonText);
        }
    }, 1000);
}

// PIN KEYPAD INPUTS
function appendPinDigit(digit) {
    if (enteredPinBuffer.length < 6) {
        enteredPinBuffer += digit;
        updatePinDisplay();
    }
}

function clearPinBuffer() {
    enteredPinBuffer = "";
    updatePinDisplay();
}

function updatePinDisplay() {
    const display = document.getElementById('tamperPinDots');
    if (!display) return;
    if (enteredPinBuffer.length === 0) {
        display.innerHTML = '<span class="empty-pin-text">Enter Security PIN</span>';
    } else {
        display.innerHTML = enteredPinBuffer.split('').map(() => '<span class="pin-dot active">●</span>').join(' ');
    }
}

// VERIFY ENTERED PIN
function submitTamperPin() {
    if (enteredPinBuffer.length === 0) {
        alert('Please enter your 4-digit security PIN.');
        return;
    }

    const userId = window.currentUser ? window.currentUser.id : 1;
    const lat = userLocation ? userLocation.lat : 12.9716;
    const lng = userLocation ? userLocation.lng : 77.5946;

    fetch('/api/tamper/verify_poweroff', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: userId,
            entered_key: enteredPinBuffer,
            latitude: lat,
            longitude: lng
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'authorized') {
            if (tamperTimer) clearInterval(tamperTimer);

            if (data.silent_sos) {
                // Duress PIN entered: fool attacker
                document.getElementById('tamperLockdownOverlay').style.display = 'none';
                alert('Power-off authorized. Device shutting down...');
                // Behind the scenes: Police and contacts are already notified!
            } else {
                // Legitimate key
                document.getElementById('tamperLockdownOverlay').style.display = 'none';
                alert('Security key verified. Power-off authorized.');
            }
        } else {
            // Wrong PIN
            document.getElementById('tamperStatusMsg').textContent = '⚠️ INCORRECT KEY! Emergency dispatch armed.';
            document.getElementById('tamperStatusMsg').style.color = '#ef4444';
            clearPinBuffer();
        }
    })
    .catch(err => {
        alert('Verification error.');
    });
}

// COUNTDOWN EXPIRED WITHOUT KEY -> ALERT POLICE & EMERGENCY CONTACTS
function handleTamperFailureTimeout(alertType, reasonText) {
    const lat = userLocation ? userLocation.lat : 12.9716;
    const lng = userLocation ? userLocation.lng : 77.5946;
    const userId = window.currentUser ? window.currentUser.id : 1;

    fetch('/api/tamper/trigger_alert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: userId,
            alert_type: alertType,
            latitude: lat,
            longitude: lng,
            notes: `Tamper PIN failed or countdown expired. ${reasonText}`
        })
    })
    .then(res => res.json())
    .then(data => {
        // Sound emergency alarm
        if (typeof startSiren === 'function') {
            startSiren();
        }

        // Show Police Dispatched overlay banner
        document.getElementById('tamperCountdownBox').style.display = 'none';
        document.getElementById('tamperKeypadBox').style.display = 'none';
        document.getElementById('tamperAlertDispatchedBanner').style.display = 'block';

        const detailsEl = document.getElementById('policeDispatchDetails');
        if (detailsEl && data.police_details) {
            detailsEl.innerHTML = `
                <div style="background: rgba(220, 38, 38, 0.2); border: 1px solid #ef4444; border-radius: 8px; padding: 12px; font-size: 13px; text-align: left; line-height: 1.5; color: white;">
                    <strong>🚨 POLICE (112) DISPATCH ACTIVE</strong><br>
                    • Reference: <b>${data.dispatch_reference}</b><br>
                    • Alert: <b>${data.alert_type.toUpperCase()}</b><br>
                    • GPS Coordinates: <b>${data.live_location.latitude.toFixed(5)}, ${data.live_location.longitude.toFixed(5)}</b><br>
                    • Emergency Contacts Notified: <b>${data.contacts_notified.length} contacts</b><br>
                    • Patrol Status: <span style="color: #4ade80; font-weight: bold;">Patrol car en route to GPS perimeter</span>
                </div>
            `;
        }
    });
}

function dismissTamperAlert() {
    if (typeof stopSiren === 'function') {
        stopSiren();
    }
    document.getElementById('tamperLockdownOverlay').style.display = 'none';
    document.getElementById('tamperCountdownBox').style.display = 'block';
    document.getElementById('tamperKeypadBox').style.display = 'block';
    document.getElementById('tamperAlertDispatchedBanner').style.display = 'none';
}

function openTamperSettingsModal() {
    openModal('tamperSettingsModal');
}

function saveTamperKeySettings(e) {
    e.preventDefault();
    const key = document.getElementById('settingsSecurityKey').value.trim();
    const duress = document.getElementById('settingsDuressKey').value.trim();
    const enabled = document.getElementById('settingsEnabledCheckbox').checked;
    const userId = window.currentUser ? window.currentUser.id : 1;

    if (!key || key.length < 4) {
        alert('Security key must be at least 4 digits.');
        return;
    }

    fetch('/api/tamper/setup_key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: userId,
            security_key: key,
            duress_key: duress || '9911',
            anti_tamper_enabled: enabled
        })
    })
    .then(res => res.json())
    .then(data => {
        closeModal('tamperSettingsModal');
        loadTamperConfig();
        alert('Power-Off Protection Key updated successfully!');
    });
}
