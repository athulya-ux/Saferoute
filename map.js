// ========================================================
// SafeRoute - Leaflet Map Controller
// ========================================================

let map = null;
let userMarker = null;
let routePolylines = [];
let routeMarkers = [];

// Layer Groups
let streetLightsGroup = L.layerGroup();
let helpPointsGroup = L.layerGroup();
let incidentsGroup = L.layerGroup();
let crowdZonesGroup = L.layerGroup();

const layerVisibility = {
    lights: true,
    help: true,
    incidents: true,
    crowd: true
};

// Default center: Urban demo center (e.g., Bangalore central corridor)
let currentCenter = [12.9716, 77.5946];
let userLocation = { lat: 12.9716, lng: 77.5946 };

function initMap() {
    if (map) return;

    map = L.map('map', {
        zoomControl: false,
        attributionControl: false
    }).setView(currentCenter, 14);

    // High performance OpenStreetMap CartoDB Positron / OSM standard tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19
    }).addTo(map);

    L.control.zoom({ position: 'topleft' }).addTo(map);

    // Add layer groups to map
    streetLightsGroup.addTo(map);
    helpPointsGroup.addTo(map);
    incidentsGroup.addTo(map);
    crowdZonesGroup.addTo(map);

    // Click map to select destination or start
    map.on('click', function(e) {
        handleMapClick(e.latlng);
    });

    // Initial data fetch
    fetchAndRenderStreetLights();
    fetchAndRenderHelpPoints();
    fetchAndRenderIncidents();
    fetchAndRenderCrowdZones();
}

function handleMapClick(latlng) {
    const destInput = document.getElementById('destLocationInput');
    destInput.value = `Pinned (${latlng.lat.toFixed(4)}, ${latlng.lng.toFixed(4)})`;
    window.selectedDestCoord = { lat: latlng.lat, lng: latlng.lng };

    // Temporary pin
    if (window.tempPinMarker) map.removeLayer(window.tempPinMarker);
    window.tempPinMarker = L.marker([latlng.lat, latlng.lng], {
        icon: createSvgIcon('#dc2626', 'fa-location-dot')
    }).addTo(map).bindPopup('Selected Destination').openPopup();
}

function locateUserGPS() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const lat = pos.coords.latitude;
                const lng = pos.coords.longitude;
                userLocation = { lat, lng };
                currentCenter = [lat, lng];
                map.setView([lat, lng], 15);

                if (userMarker) map.removeLayer(userMarker);
                userMarker = L.circleMarker([lat, lng], {
                    radius: 8,
                    fillColor: '#e11d48',
                    color: '#ffffff',
                    weight: 3,
                    opacity: 1,
                    fillOpacity: 0.9
                }).addTo(map).bindPopup('<b>Your Current Location</b>').openPopup();

                // Update start input
                document.getElementById('startLocationInput').value = `GPS (${lat.toFixed(4)}, ${lng.toFixed(4)})`;
                window.selectedStartCoord = { lat, lng };

                // Refresh nearby items
                fetchAndRenderHelpPoints(lat, lng);
            },
            (err) => {
                console.warn('Geolocation denied or unavailable. Using default safe corridor coordinates.');
                map.setView(currentCenter, 14);
            },
            { timeout: 8000 }
        );
    }
}

function createSvgIcon(bgColor, faClass, iconSize = 28) {
    return L.divIcon({
        className: 'custom-map-icon',
        html: `
            <div style="background-color: ${bgColor}; width: ${iconSize}px; height: ${iconSize}px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; border: 2px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.3); font-size: ${iconSize * 0.45}px;">
                <i class="fa-solid ${faClass}"></i>
            </div>
        `,
        iconSize: [iconSize, iconSize],
        iconAnchor: [iconSize / 2, iconSize / 2],
        popupAnchor: [0, -iconSize / 2]
    });
}

// 1. STREET LIGHTS RENDERING (Feature 2)
function fetchAndRenderStreetLights() {
    fetch('/api/street_lights')
        .then(res => res.json())
        .then(data => {
            streetLightsGroup.clearLayers();
            const lights = data.street_lights || [];
            document.getElementById('statStreetLights').textContent = data.stats ? data.stats.working : lights.length;

            lights.forEach(l => {
                const color = l.status === 'working' ? '#eab308' : (l.status === 'dim' ? '#f59e0b' : '#64748b');
                const marker = L.circleMarker([l.latitude, l.longitude], {
                    radius: 4,
                    fillColor: color,
                    color: '#ffffff',
                    weight: 1,
                    fillOpacity: 0.85
                });
                marker.bindPopup(`
                    <div style="font-size: 12px; font-family: sans-serif;">
                        <strong>Street Light (${l.status.toUpperCase()})</strong><br>
                        Source: ${l.source === 'osm' ? 'OpenStreetMap' : 'User Verified'}<br>
                        Confirmed by: ${l.confirmed_count} travelers
                    </div>
                `);
                streetLightsGroup.addLayer(marker);
            });
        })
        .catch(err => console.error('Error fetching street lights:', err));
}

// 2. INCIDENT REPORTS RENDERING (Feature 2)
function fetchAndRenderIncidents() {
    fetch('/api/incidents')
        .then(res => res.json())
        .then(data => {
            incidentsGroup.clearLayers();
            const list = data.incidents || [];
            document.getElementById('statActiveIncidents').textContent = list.length;
            renderIncidentsList(list);

            list.forEach(inc => {
                const iconClass = inc.incident_type === 'harassment' ? 'fa-triangle-exclamation' : 
                                 (inc.incident_type === 'dark_street' ? 'fa-moon' : 'fa-circle-exclamation');
                const marker = L.marker([inc.latitude, inc.longitude], {
                    icon: createSvgIcon('#dc2626', iconClass, 26)
                });
                marker.bindPopup(`
                    <div style="font-size: 12px; font-family: sans-serif; line-height: 1.4;">
                        <span style="background: #fee2e2; color: #991b1b; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 10px;">
                            ${inc.incident_type.replace('_', ' ').toUpperCase()}
                        </span>
                        <p style="margin: 6px 0;"><strong>${inc.address || 'Reported Spot'}</strong></p>
                        <p style="color: #475569;">${inc.description || 'Caution advised in this area.'}</p>
                        <div style="margin-top: 6px; display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 11px; color: #64748b;">${inc.days_remaining}d left</span>
                            <button onclick="confirmIncident(${inc.id})" style="background: #e11d48; color: white; border: none; padding: 3px 8px; border-radius: 4px; font-size: 11px; cursor: pointer;">
                                +1 Confirm (${inc.confirmation_count})
                            </button>
                        </div>
                    </div>
                `);
                incidentsGroup.addLayer(marker);
            });
        })
        .catch(err => console.error('Error fetching incidents:', err));
}

// 3. HELP POINTS RENDERING (Feature 3)
function fetchAndRenderHelpPoints(lat = 12.9716, lng = 77.5946) {
    fetch(`/api/help_points?lat=${lat}&lng=${lng}&radius_km=5`)
        .then(res => res.json())
        .then(data => {
            helpPointsGroup.clearLayers();
            const points = data.all_points || [];
            window.loadedHelpPoints = points;
            renderHelpPointsList(points);

            points.forEach(pt => {
                let color = '#2563eb';
                let icon = 'fa-building-shield';
                if (pt.point_type === 'hospital') {
                    color = '#059669';
                    icon = 'fa-hospital';
                } else if (pt.point_type === 'bus_stop') {
                    color = '#d97706';
                    icon = 'fa-bus';
                }

                const marker = L.marker([pt.latitude, pt.longitude], {
                    icon: createSvgIcon(color, icon, 26)
                });
                marker.bindPopup(`
                    <div style="font-size: 12px; font-family: sans-serif;">
                        <strong style="color: ${color};">${pt.point_type.toUpperCase()}</strong><br>
                        <b>${pt.name}</b><br>
                        <span style="color: #64748b;">${pt.address || ''}</span><br>
                        <div style="margin-top: 6px;">
                            ${pt.phone ? `<a href="tel:${pt.phone}" style="background: #2563eb; color: white; padding: 3px 8px; border-radius: 4px; text-decoration: none; font-size: 11px;">Call ${pt.phone}</a>` : '24/7 Monitored'}
                        </div>
                    </div>
                `);
                helpPointsGroup.addLayer(marker);
            });
        })
        .catch(err => console.error('Error fetching help points:', err));
}

// 4. CROWD ZONES RENDERING (Feature 2)
function fetchAndRenderCrowdZones(timeOfDay) {
    const url = timeOfDay ? `/api/crowd_zones?time_of_day=${timeOfDay}` : '/api/crowd_zones';
    fetch(url)
        .then(res => res.json())
        .then(data => {
            crowdZonesGroup.clearLayers();
            const zones = data.zones || [];
            document.getElementById('statCrowdLevel').textContent = zones[0] ? zones[0].crowd_level : 'Moderate';

            zones.forEach(z => {
                const color = z.crowd_level === 'High' ? '#10b981' : (z.crowd_level === 'Moderate' ? '#f59e0b' : '#94a3b8');
                const circle = L.circle(z.center, {
                    radius: z.radius_m,
                    color: color,
                    fillColor: color,
                    fillOpacity: 0.12,
                    weight: 1.5,
                    dashArray: '4, 4'
                });
                circle.bindPopup(`
                    <div style="font-size: 12px;">
                        <strong>${z.name}</strong><br>
                        Crowd Level: <b>${z.crowd_level}</b> (${data.time_of_day})<br>
                        <span style="color: #64748b;">${z.safety_note}</span>
                    </div>
                `);
                crowdZonesGroup.addLayer(circle);
            });
        })
        .catch(err => console.error('Error fetching crowd zones:', err));
}

// 5. DRAW ROUTE POLYLINES ON MAP
function renderRoutesOnMap(routesList, selectedIndex = 0) {
    // Clear previous route polylines & markers
    routePolylines.forEach(pl => map.removeLayer(pl));
    routePolylines = [];
    routeMarkers.forEach(m => map.removeLayer(m));
    routeMarkers = [];

    if (!routesList || routesList.length === 0) return;

    routesList.forEach((r, idx) => {
        const isSelected = idx === selectedIndex;
        const isSafest = r.is_safest;

        let lineColor = '#94a3b8';
        let lineWeight = 4;
        let lineOpacity = 0.65;
        let dashArray = null;

        if (isSafest) {
            lineColor = '#059669'; // Emerald Green
            lineWeight = isSelected ? 7 : 5;
            lineOpacity = isSelected ? 0.95 : 0.75;
        } else if (r.safety_score >= 60) {
            lineColor = '#d97706'; // Amber
            lineWeight = isSelected ? 6 : 4;
            lineOpacity = isSelected ? 0.9 : 0.6;
        } else {
            lineColor = '#dc2626'; // Red
            lineWeight = isSelected ? 6 : 4;
            dashArray = '6, 6';
            lineOpacity = isSelected ? 0.85 : 0.5;
        }

        const polyline = L.polyline(r.coords, {
            color: lineColor,
            weight: lineWeight,
            opacity: lineOpacity,
            dashArray: dashArray,
            lineJoin: 'round'
        }).addTo(map);

        polyline.on('click', () => {
            selectRoute(idx);
        });

        routePolylines.push(polyline);
    });

    // Start & Destination custom markers
    const startCoord = routesList[0].coords[0];
    const destCoord = routesList[0].coords[routesList[0].coords.length - 1];

    const startMarker = L.marker(startCoord, {
        icon: createSvgIcon('#059669', 'fa-person-walking', 30)
    }).addTo(map).bindPopup('<b>Start Location</b>');

    const destMarker = L.marker(destCoord, {
        icon: createSvgIcon('#dc2626', 'fa-flag-checkered', 30)
    }).addTo(map).bindPopup('<b>Trip Destination</b>');

    routeMarkers.push(startMarker, destMarker);

    // Zoom map to fit selected route
    map.fitBounds(routePolylines[selectedIndex].getBounds(), {
        padding: [40, 40]
    });
}

function toggleLayer(layerName) {
    const btn = document.getElementById(`filter${layerName.charAt(0).toUpperCase() + layerName.slice(1)}Btn`);
    if (layerName === 'lights') {
        if (map.hasLayer(streetLightsGroup)) {
            map.removeLayer(streetLightsGroup);
            btn.classList.remove('active');
        } else {
            map.addLayer(streetLightsGroup);
            btn.classList.add('active');
        }
    } else if (layerName === 'help') {
        if (map.hasLayer(helpPointsGroup)) {
            map.removeLayer(helpPointsGroup);
            btn.classList.remove('active');
        } else {
            map.addLayer(helpPointsGroup);
            btn.classList.add('active');
        }
    } else if (layerName === 'incidents') {
        if (map.hasLayer(incidentsGroup)) {
            map.removeLayer(incidentsGroup);
            btn.classList.remove('active');
        } else {
            map.addLayer(incidentsGroup);
            btn.classList.add('active');
        }
    }
}
