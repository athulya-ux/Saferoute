// ========================================================
// SafeRoute - Feature 6: Emergency SOS & Audible Siren
// ========================================================

let audioContext = null;
let sirenOscillator = null;
let sirenGain = null;
let isSirenPlaying = false;
let sirenInterval = null;

function triggerEmergencySOS() {
    const lat = userLocation ? userLocation.lat : 12.9716;
    const lng = userLocation ? userLocation.lng : 77.5946;
    const userId = window.currentUser ? window.currentUser.id : 1;

    // Haptic feedback
    if (navigator.vibrate) {
        navigator.vibrate([500, 250, 500, 250, 500]);
    }

    const payload = {
        user_id: userId,
        latitude: lat,
        longitude: lng,
        battery_level: '92%',
        notes: 'SOS Button Triggered by User'
    };

    fetch('/api/emergency/trigger_sos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            // Also broadcast via socket if available
            if (socket) {
                socket.emit('sos_broadcast_event', {
                    latitude: lat,
                    longitude: lng,
                    user_handle: window.currentUser ? window.currentUser.anonymous_handle : 'SafeTraveler'
                });
            }

            alert(`🚨 EMERGENCY SOS DISPATCHED!\n\nLive GPS location (${lat.toFixed(4)}, ${lng.toFixed(4)}) sent to ${data.dispatched_alerts.length} emergency contacts.\n\nHelpline 112 & 1091 alerted.`);
            
            // Auto-start siren option
            if (!isSirenPlaying) {
                if (confirm('Do you want to sound the loud emergency siren alarm?')) {
                    toggleAudioSiren();
                }
            }
        }
    })
    .catch(err => {
        alert('Emergency SOS triggered. Call 112 directly if network is down.');
    });
}

// WEB AUDIO API SIREN SYNTHESIZER
function toggleAudioSiren() {
    const btn = document.getElementById('btnSiren');

    if (isSirenPlaying) {
        stopSiren();
        btn.classList.remove('playing');
        btn.innerHTML = `<i class="fa-solid fa-play"></i> Sound Alarm`;
    } else {
        startSiren();
        btn.classList.add('playing');
        btn.innerHTML = `<i class="fa-solid fa-stop"></i> STOP ALARM`;
    }
}

function startSiren() {
    try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        audioContext = new AudioContext();

        sirenGain = audioContext.createGain();
        sirenGain.gain.setValueAtTime(0.3, audioContext.currentTime);
        sirenGain.connect(audioContext.destination);

        sirenOscillator = audioContext.createOscillator();
        sirenOscillator.type = 'sawtooth';
        sirenOscillator.connect(sirenGain);
        sirenOscillator.start();

        let highPitch = false;
        sirenInterval = setInterval(() => {
            if (!audioContext) return;
            const freq = highPitch ? 1100 : 750;
            sirenOscillator.frequency.setTargetAtTime(freq, audioContext.currentTime, 0.1);
            highPitch = !highPitch;
        }, 350);

        isSirenPlaying = true;
    } catch (e) {
        console.error('AudioContext siren failed:', e);
    }
}

function stopSiren() {
    if (sirenInterval) clearInterval(sirenInterval);
    if (sirenOscillator) {
        try {
            sirenOscillator.stop();
            sirenOscillator.disconnect();
        } catch (e) {}
    }
    if (audioContext) {
        try {
            audioContext.close();
        } catch (e) {}
    }
    isSirenPlaying = false;
}

// EMERGENCY CONTACTS
function fetchEmergencyContacts() {
    const userId = window.currentUser ? window.currentUser.id : 1;
    fetch(`/api/emergency/contacts?user_id=${userId}`)
        .then(res => res.json())
        .then(data => {
            const list = data.contacts || [];
            document.getElementById('contactsCount').textContent = list.length;
            renderEmergencyContacts(list);
        })
        .catch(err => console.error('Error fetching contacts:', err));
}

function renderEmergencyContacts(contacts) {
    const container = document.getElementById('emergencyContactsList');
    if (!container) return;
    container.innerHTML = '';

    if (contacts.length === 0) {
        container.innerHTML = `<p style="font-size: 12px; color: #64748b; padding: 6px 0;">No emergency contacts added yet. Click above to add your primary SOS contacts.</p>`;
        return;
    }

    contacts.forEach(c => {
        const card = document.createElement('div');
        card.className = 'contact-card';
        card.innerHTML = `
            <div>
                <strong style="font-size: 0.85rem; color: #0f172a;">${c.contact_name}</strong>
                ${c.is_primary ? `<span style="background: #fee2e2; color: #991b1b; padding: 1px 6px; border-radius: 10px; font-size: 10px; font-weight: bold; margin-left: 4px;">Primary</span>` : ''}
                <div style="font-size: 0.72rem; color: #64748b;">${c.relationship} • ${c.phone_number}</div>
            </div>
            <div>
                <button onclick="deleteEmergencyContact(${c.id})" style="background: transparent; border: none; color: #dc2626; cursor: pointer; padding: 4px;">
                    <i class="fa-solid fa-trash-can"></i>
                </button>
            </div>
        `;
        container.appendChild(card);
    });
}

function openAddContactModal() {
    openModal('addContactModal');
}

function saveEmergencyContact(e) {
    e.preventDefault();
    const name = document.getElementById('contactNameInput').value;
    const phone = document.getElementById('contactPhoneInput').value;
    const relation = document.getElementById('contactRelationSelect').value;
    const isPrimary = document.getElementById('contactIsPrimary').checked;
    const userId = window.currentUser ? window.currentUser.id : 1;

    fetch('/api/emergency/contacts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: userId,
            contact_name: name,
            phone_number: phone,
            relationship: relation,
            is_primary: isPrimary
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            closeModal('addContactModal');
            document.getElementById('addContactForm').reset();
            fetchEmergencyContacts();
            alert('Emergency contact added successfully.');
        }
    });
}

function deleteEmergencyContact(id) {
    if (!confirm('Remove this emergency contact?')) return;
    const userId = window.currentUser ? window.currentUser.id : 1;

    fetch(`/api/emergency/contacts/${id}?user_id=${userId}`, {
        method: 'DELETE'
    })
    .then(res => res.json())
    .then(data => {
        fetchEmergencyContacts();
    });
}
