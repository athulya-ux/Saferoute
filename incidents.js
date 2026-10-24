// ========================================================
// SafeRoute - Feature 2: Incidents, Street Lights & Crowd
// ========================================================

function renderIncidentsList(incidents) {
    const container = document.getElementById('incidentsList');
    if (!container) return;
    container.innerHTML = '';

    if (!incidents || incidents.length === 0) {
        container.innerHTML = `<p style="font-size: 12px; color: #64748b; padding: 8px 0;">No active incidents reported along current perimeter.</p>`;
        return;
    }

    incidents.forEach(inc => {
        const card = document.createElement('div');
        card.className = 'incident-card';

        const typeLabels = {
            dark_street: '🌑 Dark Street / Poor Lighting',
            harassment: '⚠️ Harassment / Catcalling',
            unsafe_spot: '🚧 Isolated / Unsafe Spot',
            accident: '💥 Accident Hazard'
        };

        const tagText = typeLabels[inc.incident_type] || inc.incident_type;
        const severityBg = inc.severity === 'critical' ? '#fee2e2' : '#fef3c7';
        const severityColor = inc.severity === 'critical' ? '#991b1b' : '#92400e';

        card.innerHTML = `
            <div class="incident-card-top">
                <span class="incident-tag-danger" style="background: ${severityBg}; color: ${severityColor};">
                    ${tagText}
                </span>
                <button class="btn-confirm-incident" onclick="confirmIncident(${inc.id}, this)">
                    <i class="fa-solid fa-thumbs-up"></i> Confirm (+<span class="confirm-count">${inc.confirmation_count}</span>)
                </button>
            </div>
            <p style="font-size: 0.82rem; font-weight: 700; color: #0f172a; margin: 4px 0;">${inc.address || 'Reported Location'}</p>
            <p style="font-size: 0.74rem; color: #475569; line-height: 1.3;">${inc.description || 'Community reported safety hazard.'}</p>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px; font-size: 0.68rem; color: #94a3b8;">
                <span>Expires in: <b>${inc.days_remaining} days</b> (30-day lifecycle)</span>
                <span>${inc.severity.toUpperCase()} RISK</span>
            </div>
        `;

        container.appendChild(card);
    });
}

function confirmIncident(incidentId, btnElement) {
    fetch(`/api/incidents/${incidentId}/confirm`, {
        method: 'POST'
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            if (btnElement) {
                const countSpan = btnElement.querySelector('.confirm-count');
                if (countSpan) countSpan.textContent = data.new_confirmation_count;
                btnElement.style.background = '#d1fae5';
                btnElement.style.color = '#065f46';
            }
            alert('Thank you for confirming. Your input updates the route safety score for everyone.');
            fetchAndRenderIncidents();
        }
    })
    .catch(err => console.error('Failed to confirm incident:', err));
}

function openReportModal() {
    // Prefill location from current map center or pin
    const addrInput = document.getElementById('reportAddressInput');
    if (!addrInput.value && window.selectedDestCoord) {
        addrInput.value = `Near ${window.selectedDestCoord.lat.toFixed(4)}, ${window.selectedDestCoord.lng.toFixed(4)}`;
    }
    openModal('reportIncidentModal');
}

function submitIncidentReport(e) {
    e.preventDefault();
    const type = document.getElementById('reportTypeSelect').value;
    const address = document.getElementById('reportAddressInput').value;
    const description = document.getElementById('reportDescInput').value;
    const severityRadio = document.querySelector('input[name="severity"]:checked');
    const severity = severityRadio ? severityRadio.value : 'medium';

    // Lat / Lng from temporary pin or map center
    const lat = window.tempPinMarker ? window.tempPinMarker.getLatLng().lat : currentCenter[0];
    const lng = window.tempPinMarker ? window.tempPinMarker.getLatLng().lng : currentCenter[1];

    const payload = {
        incident_type: type,
        address: address,
        description: description,
        severity: severity,
        latitude: lat,
        longitude: lng,
        user_id: window.currentUser ? window.currentUser.id : null
    };

    fetch('/api/incidents/report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            closeModal('reportIncidentModal');
            alert('Safety report submitted! It will appear on community maps and protect fellow travelers for the next 30 days.');
            fetchAndRenderIncidents();
            fetchAndRenderStreetLights();
            // Reset form
            document.getElementById('incidentReportForm').reset();
        } else {
            alert(data.error || 'Failed to submit report');
        }
    })
    .catch(err => {
        alert('Network error while submitting report.');
    });
}
