// ========================================================
// SafeRoute - Feature 3: Nearby Help & Transport Controller
// ========================================================

let currentHelpCategory = 'all';

function renderHelpPointsList(points) {
    const container = document.getElementById('helpPointsList');
    if (!container) return;
    container.innerHTML = '';

    const filtered = currentHelpCategory === 'all' 
        ? points 
        : points.filter(p => p.point_type === currentHelpCategory);

    if (filtered.length === 0) {
        container.innerHTML = `<p style="font-size: 12px; color: #64748b; padding: 12px 0;">No ${currentHelpCategory} points found within 5 km.</p>`;
        return;
    }

    filtered.forEach(p => {
        const card = document.createElement('div');
        card.className = 'help-point-card';

        let iconClass = 'fa-building-shield';
        let iconType = 'icon-police';
        if (p.point_type === 'hospital') {
            iconClass = 'fa-hospital';
            iconType = 'icon-hospital';
        } else if (p.point_type === 'bus_stop') {
            iconClass = 'fa-bus';
            iconType = 'icon-bus_stop';
        }

        card.innerHTML = `
            <div class="help-point-left">
                <div class="help-point-icon ${iconType}">
                    <i class="fa-solid ${iconClass}"></i>
                </div>
                <div>
                    <strong style="font-size: 0.85rem; color: #0f172a; display: block;">${p.name}</strong>
                    <span style="font-size: 0.72rem; color: #64748b;">${p.address || '5km Safe Zone'} • <b>${p.distance_km || ((p.distance_m/1000).toFixed(1))} km away</b></span>
                </div>
            </div>
            <div>
                ${p.phone ? `<a href="tel:${p.phone}" class="btn-call-point"><i class="fa-solid fa-phone"></i> Call</a>` : `<span style="font-size: 0.7rem; color: #059669; font-weight: 700;">24/7 Verified</span>`}
            </div>
        `;

        container.appendChild(card);
    });
}

function filterHelpCategory(category) {
    currentHelpCategory = category;
    document.querySelectorAll('.help-tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('onclick').includes(category));
    });
    if (window.loadedHelpPoints) {
        renderHelpPointsList(window.loadedHelpPoints);
    }
}

function fetchBusSchedules(startName, destName) {
    fetch(`/api/transport/buses?start_name=${encodeURIComponent(startName)}&dest_name=${encodeURIComponent(destName)}`)
        .then(res => res.json())
        .then(data => {
            const container = document.getElementById('busScheduleContainer');
            if (!container) return;
            container.innerHTML = '';

            const buses = data.available_services || [];
            buses.forEach(b => {
                const card = document.createElement('div');
                card.style.cssText = 'background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 10px; margin-bottom: 8px; font-size: 12px;';
                card.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                        <strong style="color: #be185d;"><i class="fa-solid fa-bus"></i> ${b.route_number}</strong>
                        <span style="background: #ffe4e6; color: #9f1239; padding: 2px 6px; border-radius: 12px; font-weight: bold; font-size: 10px;">${b.frequency}</span>
                    </div>
                    <div style="color: #475569; margin-bottom: 6px;">Next departures in: <b>${b.next_arrivals_mins.join(' min, ')} mins</b></div>
                    <div style="font-size: 11px; color: #059669; font-weight: 600;">
                        <i class="fa-solid fa-check-double"></i> ${b.safety_features.join(' • ')}
                    </div>
                `;
                container.appendChild(card);
            });
        })
        .catch(err => console.error('Error fetching buses:', err));
}

function updateCabLinks(start, dest, startName, destName) {
    const uberBtn = document.getElementById('btnUberDirect');
    const olaBtn = document.getElementById('btnOlaDirect');

    const uberUrl = `https://m.uber.com/ul/?action=setPickup&pickup[latitude]=${start.lat}&pickup[longitude]=${start.lng}&pickup[nickname]=${encodeURIComponent(startName)}&dropoff[latitude]=${dest.lat}&dropoff[longitude]=${dest.lng}&dropoff[nickname]=${encodeURIComponent(destName)}`;
    const olaUrl = `https://book.olacabs.com/?lat=${start.lat}&lng=${start.lng}&drop_lat=${dest.lat}&drop_lng=${dest.lng}`;

    if (uberBtn) uberBtn.href = uberUrl;
    if (olaBtn) olaBtn.href = olaUrl;
}
