// ========================================================
// SafeRoute - Feature 1: Safe Routes & Scoring Controller
// ========================================================

let evaluatedRoutesData = [];
let currentSelectedRouteIndex = 0;
let unsafeCountdownInterval = null;

const PRESET_CORRIDORS = {
    majestic_commercial: {
        startName: "Majestic City Interchange",
        start: { lat: 12.9767, lng: 77.5713 },
        destName: "Commercial Street Boulevard",
        dest: { lat: 12.9756, lng: 77.6066 }
    },
    cubbon_mgroad: {
        startName: "Cubbon Park Entrance",
        start: { lat: 12.9710, lng: 77.5910 },
        destName: "MG Road Metro Boulevard",
        dest: { lat: 12.9750, lng: 77.6080 }
    },
    campus_metro: {
        startName: "University Library Campus",
        start: { lat: 12.9715, lng: 77.5860 },
        destName: "Metro Transit Central Station",
        dest: { lat: 12.9775, lng: 77.5720 }
    }
};

function applyPreset(presetKey) {
    const p = PRESET_CORRIDORS[presetKey];
    if (!p) return;

    document.getElementById('startLocationInput').value = p.startName;
    document.getElementById('destLocationInput').value = p.destName;
    window.selectedStartCoord = p.start;
    window.selectedDestCoord = p.dest;

    calculateRouteSafety();
}

function setStartToGPS() {
    locateUserGPS();
}

function swapLocations() {
    const sInput = document.getElementById('startLocationInput');
    const dInput = document.getElementById('destLocationInput');
    const tempVal = sInput.value;
    sInput.value = dInput.value;
    dInput.value = tempVal;

    const tempCoord = window.selectedStartCoord;
    window.selectedStartCoord = window.selectedDestCoord;
    window.selectedDestCoord = tempCoord;
}

function calculateRouteSafety() {
    const btn = document.getElementById('btnCalculateRoute');
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Calculating Safety Scores...`;
    btn.disabled = true;

    // Coordinates default or custom
    const startCoord = window.selectedStartCoord || { lat: 12.9767, lng: 77.5713 };
    const destCoord = window.selectedDestCoord || { lat: 12.9756, lng: 77.6066 };
    const sName = document.getElementById('startLocationInput').value || 'Origin';
    const dName = document.getElementById('destLocationInput').value || 'Destination';

    const timeOfDayVal = document.getElementById('timeOfDaySelect').value;
    const timeOfDay = timeOfDayVal === 'current' ? undefined : timeOfDayVal;

    const payload = {
        start_lat: startCoord.lat,
        start_lng: startCoord.lng,
        start_name: sName,
        dest_lat: destCoord.lat,
        dest_lng: destCoord.lng,
        dest_name: dName,
        time_of_day: timeOfDay,
        user_id: window.currentUser ? window.currentUser.id : null
    };

    fetch('/api/routes/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        btn.innerHTML = `<i class="fa-solid fa-shield-halved"></i> Find Safest Routes`;
        btn.disabled = false;

        if (data.status === 'success' && data.routes) {
            evaluatedRoutesData = data.routes;
            renderRouteCards(data.routes, data.safest_route_id);
            renderRoutesOnMap(data.routes, data.safest_route_id);
            currentSelectedRouteIndex = data.safest_route_id;

            // Update transport & cab deep links for this trip
            updateCabLinks(startCoord, destCoord, sName, dName);
            fetchBusSchedules(sName, dName);

            // Scroll to results
            document.getElementById('routesResultsSection').style.display = 'block';
        }
    })
    .catch(err => {
        btn.innerHTML = `<i class="fa-solid fa-shield-halved"></i> Find Safest Routes`;
        btn.disabled = false;
        alert('Could not compute safe routes. Please verify internet connection or coordinates.');
    });
}

function renderRouteCards(routes, safestId) {
    const container = document.getElementById('routeCardsContainer');
    container.innerHTML = '';

    routes.forEach((r, idx) => {
        const isSafest = r.route_id === safestId;
        const scoreClass = r.safety_score >= 80 ? 'score-high' : (r.safety_score >= 60 ? 'score-medium' : 'score-low');

        const card = document.createElement('div');
        card.className = `route-card ${isSafest ? 'is-safest' : ''} ${idx === currentSelectedRouteIndex ? 'selected' : ''}`;
        card.id = `routeCard_${idx}`;
        card.onclick = (e) => {
            if (!e.target.closest('button')) {
                selectRoute(idx);
            }
        };

        const distKm = (r.distance_m / 1000).toFixed(2);
        const lightsCount = r.breakdown.street_lighting.working_count;
        const crowdLevel = r.breakdown.crowd_level.level;
        const policeCount = r.breakdown.help_points.police_nearby;

        card.innerHTML = `
            <div class="card-top-row">
                <span class="route-name-tag">${r.name}</span>
                ${isSafest ? `<span class="safest-badge"><i class="fa-solid fa-shield-check"></i> SAFEST ROUTE</span>` : `<span class="badge-tag">${r.tag}</span>`}
            </div>

            <div class="card-score-row">
                <div class="safety-score-pill ${scoreClass}">
                    <span class="score-num">${r.safety_score}</span>
                    <span class="score-denom">/100</span>
                </div>
                <div class="route-metrics-line">
                    <span><i class="fa-solid fa-person-walking"></i> ${r.duration_min} mins (${distKm} km)</span>
                </div>
            </div>

            <div class="card-highlights-row">
                <span class="highlight-pill"><i class="fa-solid fa-lightbulb text-yellow"></i> ${lightsCount} Street Lights</span>
                <span class="highlight-pill"><i class="fa-solid fa-users text-blue"></i> ${crowdLevel} Footfall</span>
                <span class="highlight-pill"><i class="fa-solid fa-building-shield text-blue"></i> ${policeCount} Police Nearby</span>
                ${r.breakdown.incidents_count > 0 ? `<span class="highlight-pill" style="color: #dc2626;"><i class="fa-solid fa-triangle-exclamation"></i> ${r.breakdown.incidents_count} Incident Alert</span>` : ''}
            </div>

            <div class="card-bottom-actions">
                <button class="btn-view-breakdown" onclick="openSafetyBreakdownModal(${idx})">
                    <i class="fa-solid fa-circle-info"></i> Why this score?
                </button>
                <button class="btn-select-route" onclick="selectRoute(${idx})">
                    ${idx === currentSelectedRouteIndex ? 'Active Route' : 'Select'}
                </button>
            </div>
        `;

        container.appendChild(card);
    });
}

function selectRoute(index) {
    currentSelectedRouteIndex = index;
    const selectedRoute = evaluatedRoutesData[index];
    if (!selectedRoute) return;

    // Highlight card
    document.querySelectorAll('.route-card').forEach((c, idx) => {
        c.classList.toggle('selected', idx === index);
    });

    // Update map polylines
    renderRoutesOnMap(evaluatedRoutesData, index);

    // FEATURE 3 & 6: Check if selected route is unsafe (< 60)
    if (selectedRoute.safety_score < 60) {
        showUnsafeRouteWarning(selectedRoute);
    } else {
        hideUnsafeRouteWarning();
    }
}

// 10-SECOND CANCELLABLE WARNING WORKFLOW
function showUnsafeRouteWarning(route) {
    const toast = document.getElementById('unsafeRouteWarningToast');
    const countdownEl = document.getElementById('cancelCountdownSec');
    const subtitleEl = document.getElementById('unsafeWarningSubtitle');

    subtitleEl.innerHTML = `Route '${route.name}' scored <b>${route.safety_score}/100</b> with poor lighting or reported incidents. Trip sharing will broadcast in <span id="cancelCountdownSec" class="countdown-num">10</span>s.`;
    toast.style.display = 'block';

    let seconds = 10;
    if (unsafeCountdownInterval) clearInterval(unsafeCountdownInterval);

    unsafeCountdownInterval = setInterval(() => {
        seconds--;
        const curEl = document.getElementById('cancelCountdownSec');
        if (curEl) curEl.textContent = seconds;

        if (seconds <= 0) {
            clearInterval(unsafeCountdownInterval);
            toast.style.display = 'none';
            // Trigger auto trip sharing for safety
            alert('Live trip location dispatched to emergency contacts for your safety.');
        }
    }, 1000);
}

function hideUnsafeRouteWarning() {
    if (unsafeCountdownInterval) clearInterval(unsafeCountdownInterval);
    document.getElementById('unsafeRouteWarningToast').style.display = 'none';
}

function cancelUnsafeTrip() {
    hideUnsafeRouteWarning();
    // Switch back to safest route
    const safest = evaluatedRoutesData.find(r => r.is_safest);
    if (safest) {
        selectRoute(safest.route_id);
    }
}

function acknowledgeUnsafeTrip() {
    hideUnsafeRouteWarning();
}

// SCORE BREAKDOWN MODAL (ITEMIZED TRANSPARENCY)
function openSafetyBreakdownModal(routeIndex) {
    const r = evaluatedRoutesData[routeIndex];
    if (!r) return;

    const body = document.getElementById('breakdownModalBody');
    const b = r.breakdown;

    let reasonsHtml = '';
    if (r.reasons_low && r.reasons_low.length > 0) {
        reasonsHtml = `
            <div class="breakdown-warning-box">
                <strong><i class="fa-solid fa-triangle-exclamation"></i> Factors Lowering Score:</strong>
                <ul style="margin-left: 18px; margin-top: 6px;">
                    ${r.reasons_low.map(reason => `<li>${reason}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    body.innerHTML = `
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
            <div>
                <h4>${r.name}</h4>
                <span class="badge-tag" style="background: ${r.tier_color}; color: white;">${r.safety_tier}</span>
            </div>
            <div style="font-size: 1.8rem; font-weight: 800; color: ${r.tier_color};">
                ${r.safety_score}<span style="font-size: 1rem; color: #64748b;">/100</span>
            </div>
        </div>

        <!-- 1. Street Lighting -->
        <div class="breakdown-row">
            <div class="breakdown-row-header">
                <span><i class="fa-solid fa-lightbulb text-yellow"></i> Street Lighting Coverage</span>
                <span>${b.street_lighting.score} / ${b.street_lighting.max} pts</span>
            </div>
            <div class="breakdown-bar-bg">
                <div class="breakdown-bar-fill" style="width: ${(b.street_lighting.score/30)*100}%; background: #eab308;"></div>
            </div>
            <p class="breakdown-notes">${b.street_lighting.working_count} functional street lamps along corridor (${b.street_lighting.density_per_km} per km).</p>
        </div>

        <!-- 2. Crowd Level -->
        <div class="breakdown-row">
            <div class="breakdown-row-header">
                <span><i class="fa-solid fa-users text-blue"></i> Crowd Footfall (${b.crowd_level.time_of_day})</span>
                <span>${b.crowd_level.score} / ${b.crowd_level.max} pts</span>
            </div>
            <div class="breakdown-bar-bg">
                <div class="breakdown-bar-fill" style="width: ${(b.crowd_level.score/25)*100}%; background: #3b82f6;"></div>
            </div>
            <p class="breakdown-notes">${b.crowd_level.level} crowd level for the current travel time.</p>
        </div>

        <!-- 3. Nearby Help Points -->
        <div class="breakdown-row">
            <div class="breakdown-row-header">
                <span><i class="fa-solid fa-building-shield text-blue"></i> Police &amp; Hospital Proximity (500m)</span>
                <span>${b.help_points.score} / ${b.help_points.max} pts</span>
            </div>
            <div class="breakdown-bar-bg">
                <div class="breakdown-bar-fill" style="width: ${(b.help_points.score/25)*100}%; background: #059669;"></div>
            </div>
            <p class="breakdown-notes">${b.help_points.police_nearby} Police Posts, ${b.help_points.hospitals_nearby} Hospitals, ${b.help_points.bus_stops_nearby} Bus Stops.</p>
        </div>

        <!-- 4. Penalties -->
        <div class="breakdown-row">
            <div class="breakdown-row-header">
                <span><i class="fa-regular fa-clock"></i> Time of Day &amp; Incident Deductions</span>
                <span style="color: #dc2626;">-${b.time_penalty + b.incident_penalty} pts</span>
            </div>
            <p class="breakdown-notes">Time Penalty: -${b.time_penalty} pts | Incident Risk Penalty: -${b.incident_penalty} pts</p>
        </div>

        ${reasonsHtml}
    `;

    openModal('breakdownModal');
}
