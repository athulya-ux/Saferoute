// ========================================================
// SafeRoute - Feature 5: Walk Together Radar & Live 2-Women Chat
// Mutual-consent only between 2 verified women travelers
// ========================================================

let socket = null;
let activeWalkRequestId = null;
let currentChatPartner = null;
let radarInterval = null;
let pendingIncomingWalk = null;

function initSocketConnection() {
    if (socket) return;
    try {
        socket = io();

        socket.on('connect', () => {
            const userId = window.currentUser ? window.currentUser.id : 1;
            socket.emit('join_user_channel', { user_id: userId });
        });

        // 1. INCOMING WALK INVITATION (Recipient receives real-time alert)
        socket.on('incoming_walk_request', (data) => {
            pendingIncomingWalk = data;
            showIncomingWalkModal(data);
        });

        // 2. WALK REQUEST DECISION (Both users notified when mutually accepted)
        socket.on('walk_decision_received', (data) => {
            const myId = window.currentUser ? window.currentUser.id : 1;
            if (data.decision === 'accepted') {
                const partnerHandle = (myId === data.requester_id) ? data.recipient_handle : data.requester_handle;
                closeModal('incomingWalkModal');
                openTab('walk');
                openLiveChatSession(data.walk_request_id, partnerHandle);
                alert(`🤝 Walk Together match confirmed with ${partnerHandle}! Live ephemeral chat is now open.`);
            } else if (data.decision === 'rejected') {
                closeModal('incomingWalkModal');
                if (myId === data.requester_id) {
                    alert(`The walk request was declined by the traveler.`);
                }
            }
        });

        // 3. CHAT HISTORY
        socket.on('chat_history', (data) => {
            const box = document.getElementById('chatMessagesBox');
            box.innerHTML = `
                <div class="chat-system-bubble">
                    <i class="fa-solid fa-lock"></i> End-to-end anonymous transit chat. Real names and phone numbers are never shared. Messages expire when trip ends.
                </div>
            `;
            if (data.messages) {
                data.messages.forEach(msg => {
                    appendChatMessage(msg.anonymous_handle || msg.sender_handle, msg.message_text, msg.sender_id === (window.currentUser ? window.currentUser.id : 0));
                });
            }
        });

        // 4. NEW MESSAGE ARRIVAL
        socket.on('new_message', (msg) => {
            appendChatMessage(msg.sender_handle, msg.text, msg.sender_id === (window.currentUser ? window.currentUser.id : 0));
        });

        // 5. EMERGENCY BROADCASTS
        socket.on('incoming_sos_alert', (data) => {
            alert(`⚠️ EMERGENCY ALERT: Nearby traveler triggered SOS at (${data.latitude.toFixed(3)}, ${data.longitude.toFixed(3)}). Emergency services dispatched.`);
        });

        socket.on('incoming_tamper_alert', (data) => {
            alert(`🚨 TAMPER WARNING: Emergency shutdown alert from traveler at (${data.latitude.toFixed(3)}, ${data.longitude.toFixed(3)}). Police notified.`);
        });
    } catch (e) {
        console.warn('Socket.IO initialization error:', e);
    }
}

function toggleWalkRadar(isOptedIn) {
    const statusLabel = document.getElementById('radarStatusLabel');
    const scannerBox = document.getElementById('radarScannerBox');

    statusLabel.textContent = isOptedIn ? 'Visible (1km)' : 'Invisible';
    scannerBox.style.display = isOptedIn ? 'block' : 'none';

    const userId = window.currentUser ? window.currentUser.id : 1;
    const lat = userLocation ? userLocation.lat : 12.9740;
    const lng = userLocation ? userLocation.lng : 12.9760;

    fetch('/api/walk/toggle_visibility', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: userId,
            opt_in: isOptedIn,
            latitude: lat,
            longitude: lng
        })
    })
    .then(res => res.json())
    .then(data => {
        if (isOptedIn) {
            scanNearbyWalkers();
            if (!radarInterval) {
                radarInterval = setInterval(scanNearbyWalkers, 8000);
            }
        } else {
            if (radarInterval) clearInterval(radarInterval);
            document.getElementById('nearbyTravelersList').innerHTML = '';
            document.getElementById('nearbyCount').textContent = '0';
        }
    })
    .catch(err => console.error('Radar toggle error:', err));
}

function scanNearbyWalkers() {
    const userId = window.currentUser ? window.currentUser.id : 1;
    const lat = userLocation ? userLocation.lat : 12.9740;
    const lng = userLocation ? userLocation.lng : 77.5960;

    fetch(`/api/walk/nearby?lat=${lat}&lng=${lng}&user_id=${userId}`)
        .then(res => res.json())
        .then(data => {
            const travelers = data.nearby_travelers || [];
            document.getElementById('nearbyCount').textContent = travelers.length;
            renderNearbyTravelers(travelers);
        })
        .catch(err => console.error('Error scanning nearby walkers:', err));
}

function renderNearbyTravelers(travelers) {
    const container = document.getElementById('nearbyTravelersList');
    if (!container) return;
    container.innerHTML = '';

    if (travelers.length === 0) {
        container.innerHTML = `
            <p style="font-size: 12px; color: #64748b; text-align: center; padding: 12px 0;">
                No other verified women travelers currently opted-in within 1 km.
            </p>
        `;
        return;
    }

    travelers.forEach(t => {
        const card = document.createElement('div');
        card.className = 'traveler-card';
        card.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <div class="traveler-avatar-box">
                    <i class="fa-solid fa-venus"></i>
                </div>
                <div>
                    <strong style="font-size: 0.85rem; color: #0f172a; display: block;">${t.anonymous_handle}</strong>
                    <span style="font-size: 0.72rem; color: #059669; font-weight: 700;">
                        <i class="fa-solid fa-circle-check"></i> Verified Woman • ${t.approx_distance_text}
                    </span>
                </div>
            </div>
            <div>
                <button class="btn-request-walk" onclick="sendWalkRequestToUser(${t.user_id}, '${t.anonymous_handle}', ${t.approx_distance_m})">
                    <i class="fa-solid fa-paper-plane"></i> Request
                </button>
            </div>
        `;
        container.appendChild(card);
    });
}

// SENDS WALK REQUEST TO COMPANION
function sendWalkRequestToUser(recipientId, handle, approxDist) {
    initSocketConnection();
    const myId = window.currentUser ? window.currentUser.id : 1;

    fetch('/api/walk/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            requester_id: myId,
            recipient_id: recipientId,
            approx_distance_m: approxDist
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            activeWalkRequestId = data.walk_request_id;
            currentChatPartner = handle;

            // Broadcast request through Socket.IO to recipient
            if (socket) {
                socket.emit('walk_request_sent', {
                    walk_request_id: data.walk_request_id,
                    requester_id: myId,
                    recipient_id: recipientId,
                    approx_distance_m: approxDist
                });
            }

            alert(`Invitation sent to ${handle}! As soon as she accepts on her device/tab, the live chat will open.`);
        }
    })
    .catch(err => alert('Failed to send walk request.'));
}

// INCOMING WALK MODAL (Recipient popup)
function showIncomingWalkModal(invitationData) {
    const handleEl = document.getElementById('incomingRequesterHandle');
    const msgEl = document.getElementById('incomingRequesterMessage');
    const distEl = document.getElementById('incomingRequesterDist');

    if (handleEl) handleEl.textContent = invitationData.requester_handle;
    if (msgEl) msgEl.textContent = invitationData.message;
    if (distEl) distEl.textContent = `~${invitationData.approx_distance_m}m away`;

    openModal('incomingWalkModal');
}

// RECIPIENT ACCEPTS OR DECLINES
function respondToIncomingWalk(decision) {
    if (!pendingIncomingWalk) return;

    const walkId = pendingIncomingWalk.walk_request_id;
    const requesterId = pendingIncomingWalk.requester_id;
    const myId = window.currentUser ? window.currentUser.id : 2;

    fetch('/api/walk/respond', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            walk_request_id: walkId,
            decision: decision
        })
    })
    .then(res => res.json())
    .then(data => {
        closeModal('incomingWalkModal');
        
        // Broadcast decision through Socket.IO
        if (socket) {
            socket.emit('walk_request_response', {
                walk_request_id: walkId,
                requester_id: requesterId,
                recipient_id: myId,
                decision: decision
            });
        }
    })
    .catch(err => console.error('Error responding to walk:', err));
}

// OPENS LIVE CHAT SESSION UPON MUTUAL CONSENT
function openLiveChatSession(walkId, partnerHandle) {
    initSocketConnection();
    activeWalkRequestId = walkId;
    currentChatPartner = partnerHandle;

    document.getElementById('chatPartnerHandle').textContent = partnerHandle;
    document.getElementById('walkChatDrawer').style.display = 'block';

    const userId = window.currentUser ? window.currentUser.id : 1;
    if (socket) {
        socket.emit('join_walk', {
            walk_request_id: walkId,
            user_id: userId
        });
    }

    // Scroll chat to bottom
    const box = document.getElementById('chatMessagesBox');
    box.scrollTop = box.scrollHeight;
}

function sendWalkChatMessage() {
    const input = document.getElementById('chatMessageInput');
    const text = input.value.trim();
    if (!text || !activeWalkRequestId) return;

    const userId = window.currentUser ? window.currentUser.id : 1;

    if (socket) {
        socket.emit('send_message', {
            walk_request_id: activeWalkRequestId,
            sender_id: userId,
            text: text
        });
    }

    input.value = '';
}

function handleChatEnter(e) {
    if (e.key === 'Enter') {
        sendWalkChatMessage();
    }
}

function appendChatMessage(senderHandle, text, isSelf) {
    const box = document.getElementById('chatMessagesBox');
    const row = document.createElement('div');
    row.className = `chat-msg-row ${isSelf ? 'sent' : 'received'}`;
    row.innerHTML = `
        <div class="chat-bubble">${text}</div>
        <div class="chat-meta">${isSelf ? 'You' : senderHandle}</div>
    `;
    box.appendChild(row);
    box.scrollTop = box.scrollHeight;
}

function endCurrentWalkTrip() {
    if (!confirm('Are you sure you want to end this walk trip? Live chat will close and your visibility will be set to private.')) return;

    const userId = window.currentUser ? window.currentUser.id : 1;

    fetch('/api/walk/end_trip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            walk_request_id: activeWalkRequestId,
            user_id: userId
        })
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById('walkChatDrawer').style.display = 'none';
        document.getElementById('walkOptInToggle').checked = false;
        toggleWalkRadar(false);
        activeWalkRequestId = null;
        alert('Trip safely concluded. Thank you for walking together!');
    });
}

function blockCurrentTraveler() {
    const reason = prompt('Please specify why you are blocking/reporting this traveler:', 'Uncomfortable behavior');
    if (!reason) return;

    const myId = window.currentUser ? window.currentUser.id : 1;
    
    fetch('/api/walk/block_report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            reporter_id: myId,
            reported_user_id: 2,
            report_type: 'inappropriate_behavior',
            reason: reason,
            walk_request_id: activeWalkRequestId
        })
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById('walkChatDrawer').style.display = 'none';
        activeWalkRequestId = null;
        alert('User successfully blocked and reported. Connection terminated.');
        scanNearbyWalkers();
    });
}

// PERSONA SWITCHER FOR FRICTIONLESS 2-USER TESTING
function switchUserPersona(targetUserId) {
    const personas = {
        1: { id: 1, phone: '+919876543210', full_name: 'Aarti Sharma', anonymous_handle: 'SafeTraveler #412', verified_woman_declared: true, is_walk_together_opted_in: true },
        2: { id: 2, phone: '+919876543211', full_name: 'Pooja Verma', anonymous_handle: 'NightCompanion #809', verified_woman_declared: true, is_walk_together_opted_in: true },
        3: { id: 3, phone: '+919876543212', full_name: 'Sneha Patel', anonymous_handle: 'CityWalker #305', verified_woman_declared: true, is_walk_together_opted_in: true }
    };

    const selected = personas[targetUserId] || personas[1];
    window.currentUser = selected;
    localStorage.setItem('saferoute_user', JSON.stringify(selected));

    if (socket) {
        socket.emit('join_user_channel', { user_id: selected.id });
    }

    updateUserDisplay();
    scanNearbyWalkers();
    loadTamperConfig();
    fetchEmergencyContacts();
    alert(`Switched active traveler profile to: ${selected.full_name} (${selected.anonymous_handle})`);
}

function openCompanionWindow() {
    const myId = window.currentUser ? window.currentUser.id : 1;
    const companionId = (myId === 1) ? 2 : 1;
    window.open(`/?user=${companionId}`, '_blank', 'width=450,height=800');
}
