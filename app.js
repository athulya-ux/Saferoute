// ========================================================
// SafeRoute - Main Application Coordinator
// ========================================================

document.addEventListener('DOMContentLoaded', () => {
    // 0. Handle Persona Selection via URL Parameter (e.g. ?user=2 for Companion Window)
    const urlParams = new URLSearchParams(window.location.search);
    const userParam = urlParams.get('user');
    if (userParam) {
        const personas = {
            '1': { id: 1, phone: '+919876543210', full_name: 'Aarti Sharma', anonymous_handle: 'SafeTraveler #412', verified_woman_declared: true, is_walk_together_opted_in: true },
            '2': { id: 2, phone: '+919876543211', full_name: 'Pooja Verma', anonymous_handle: 'NightCompanion #809', verified_woman_declared: true, is_walk_together_opted_in: true },
            '3': { id: 3, phone: '+919876543212', full_name: 'Sneha Patel', anonymous_handle: 'CityWalker #305', verified_woman_declared: true, is_walk_together_opted_in: true }
        };
        if (personas[userParam]) {
            window.currentUser = personas[userParam];
            localStorage.setItem('saferoute_user', JSON.stringify(personas[userParam]));
        }
    }

    // 1. Initialize Map
    initMap();

    // 2. Initialize User State & Sockets
    updateUserDisplay();
    initSocketConnection();

    // 3. Load Emergency Contacts & Anti-Tamper Guard
    fetchEmergencyContacts();
    initAntiTamperGuard();

    // 4. Time of Day Selector Listener
    const timeSelect = document.getElementById('timeOfDaySelect');
    if (timeSelect) {
        timeSelect.addEventListener('change', (e) => {
            const val = e.target.value === 'current' ? null : e.target.value;
            fetchAndRenderCrowdZones(val);
            if (evaluatedRoutesData && evaluatedRoutesData.length > 0) {
                calculateRouteSafety();
            }
        });
    }

    // 5. Auto calculate initial demo route after brief initialization
    setTimeout(() => {
        applyPreset('majestic_commercial');
    }, 600);
});

// TAB SWITCHING (Mobile Bottom Navigation & Desktop Views)
function openTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // Remove active from nav items
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected tab
    const targetTab = document.getElementById(`tab-${tabName}`);
    if (targetTab) {
        targetTab.classList.add('active');
    }

    // Set nav button active
    const activeNavBtn = document.querySelector(`.nav-item[data-tab="${tabName}"]`);
    if (activeNavBtn) {
        activeNavBtn.classList.add('active');
    }

    // Invalidate map size in case layout shifted
    if (map) {
        setTimeout(() => map.invalidateSize(), 200);
    }
}

// MODAL CONTROLS
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('open');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('open');
    }
}

// Close modal when clicking outside dialog
window.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('open');
    }
});
