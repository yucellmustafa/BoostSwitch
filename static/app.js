let state = {};
let autoTurboApps = []; async function fetchStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();

        document.getElementById('connection-dot').classList.add('connected');
        document.getElementById('connection-text').innerText = 'Connected';

        // Check data freshness
        const now = Date.now() / 1000;
        const isStale = data.last_update && (now - data.last_update > 5);
        if (isStale) {
            document.getElementById('connection-dot').style.backgroundColor = '#f59e0b'; // orange
            document.getElementById('connection-text').innerText = 'Data Stale';
        } else {
            document.getElementById('connection-dot').style.backgroundColor = '';
        }

        // Update AC Card
        const cardAc = document.getElementById('card-ac');
        if (data.ac_on) {
            cardAc.classList.add('active');
            document.getElementById('status-ac').innerText = 'Turbo ON';
        } else {
            cardAc.classList.remove('active');
            document.getElementById('status-ac').innerText = 'Turbo OFF';
        }

        // Update DC Card
        const cardDc = document.getElementById('card-dc');
        if (data.dc_on) {
            cardDc.classList.add('active');
            document.getElementById('status-dc').innerText = 'Turbo ON';
        } else {
            cardDc.classList.remove('active');
            document.getElementById('status-dc').innerText = 'Turbo OFF';
        }

        // Update Temps
        const valTemp = document.getElementById('val-temp');
        const cardTemp = valTemp.parentElement;
        const lblTemp = document.getElementById('lbl-temp');
        if (data.temp !== null) {
            valTemp.innerHTML = `${Math.round(data.temp)}<small>°C</small>`;
            lblTemp.innerText = "CPU Temp";

            // Check threshold from settings (approx)
            if (data.temp > (parseInt(document.getElementById('inp-th').value) || 90)) {
                cardTemp.classList.add('danger');
            } else {
                cardTemp.classList.remove('danger');
            }
        } else {
            valTemp.innerHTML = `--<small>°C</small>`;
            lblTemp.innerText = "Reading...";
            cardTemp.classList.remove('danger');
        }

        // Update Battery
        const valBat = document.getElementById('val-bat');
        const cardBat = valBat.parentElement;
        if (data.battery !== null) {
            valBat.innerHTML = `${Math.round(data.battery)}<small>%</small>`;
            if (data.battery < (parseInt(document.getElementById('inp-bat').value) || 20)) {
                cardBat.classList.add('warning');
            } else {
                cardBat.classList.remove('warning');
            }
        } else {
            valBat.innerHTML = `AC<small></small>`;
            cardBat.classList.remove('warning');
        }

        // Update active apps highlight
        const activeApps = data.active_apps || [];
        document.querySelectorAll('.app-chip').forEach(chip => {
            const appName = chip.dataset.app;
            if (activeApps.includes(appName)) {
                chip.classList.add('running');
            } else {
                chip.classList.remove('running');
            }
        });

    } catch (e) {
        document.getElementById('connection-dot').classList.remove('connected');
        document.getElementById('connection-text').innerText = 'Disconnected';
    }
}

async function fetchSettings() {
    const res = await fetch('/api/settings');
    const data = await res.json();

    document.getElementById('inp-th').value = data.thermal_limit;
    document.getElementById('chk-th').checked = data.thermal_control;

    document.getElementById('inp-bat').value = data.battery_threshold;
    document.getElementById('chk-bat').checked = data.smart_battery;

    document.getElementById('chk-hk').checked = data.hotkey_enabled;
    document.getElementById('hotkey-display').innerHTML = `Current: <strong>${data.hotkey || "None"}</strong>`;

    document.getElementById('chk-start').checked = data.autostart;

    document.getElementById('chk-auto-turbo').checked = !!data.auto_turbo_enabled;
    autoTurboApps = data.auto_turbo_apps || [];
    renderAutoApps();
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    if (type === 'error') icon = '❌';
    if (type === 'warning') icon = '⚠️';
    if (type === 'security') {
        icon = '🔒';
        toast.className = 'toast warning';
    }

    toast.innerHTML = `<span class="toast-icon">${icon}</span><span class="toast-message">${message}</span>`;
    container.appendChild(toast);

    // Auto remove after 4s
    setTimeout(() => {
        toast.classList.add('removing');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

async function toggleTurbo(mode) {
    const isCurrentlyOn = document.getElementById(`card-${mode.toLowerCase()}`).classList.contains('active');
    await fetch('/api/state', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: mode, state: !isCurrentlyOn })
    });
    fetchStatus(); // immediate update
}

async function saveSettings() {
    const payload = {
        thermal_limit: parseInt(document.getElementById('inp-th').value),
        thermal_control: document.getElementById('chk-th').checked,
        battery_threshold: parseInt(document.getElementById('inp-bat').value),
        smart_battery: document.getElementById('chk-bat').checked,
        hotkey_enabled: document.getElementById('chk-hk').checked,
        autostart: document.getElementById('chk-start').checked,
        auto_turbo_enabled: document.getElementById('chk-auto-turbo').checked,
        auto_turbo_apps: autoTurboApps
    };

    await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
}

async function recordHotkey() {
    const btn = document.getElementById('btn-hotkey');
    const display = document.getElementById('hotkey-display');

    const originalText = btn.innerText;
    const originalDisplay = display.innerHTML;

    btn.innerText = "Waiting...";
    btn.disabled = true;
    display.innerHTML = '<span style="color: var(--accent-yellow)">Recording... Press keys (Avoid Ctrl+T/W)</span>';

    try {
        const res = await fetch('/api/hotkeys/record', { method: 'POST' });
        const data = await res.json();

        if (data.success && data.hotkey) {
            showToast(`Hotkey set to ${data.hotkey}`, 'success');
            display.innerHTML = `Current: <strong>${data.hotkey}</strong>`;
        } else {
            display.innerHTML = originalDisplay;
        }
    } catch (e) {
        display.innerHTML = originalDisplay;
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
    }
}

async function clearHotkey() {
    await fetch('/api/hotkeys/clear', { method: 'POST' });
    document.getElementById('hotkey-display').innerHTML = `Current: <strong>None</strong>`;
}

// Auto-Turbo handling
function renderAutoApps() {
    const container = document.getElementById('auto-apps-list');
    container.innerHTML = '';

    // Sort apps alphabetically
    const sortedApps = [...autoTurboApps].sort((a, b) => a.localeCompare(b));

    sortedApps.forEach((app) => {
        const originalIndex = autoTurboApps.indexOf(app);
        const chip = document.createElement('div');
        chip.className = 'app-chip';
        // We use the original exact string for dataset to match process names
        chip.dataset.app = app;

        // Lowercase for display
        const displayApp = app.toLowerCase();

        // Generate a consistent color based on the app name
        const hue = app.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0) % 360;
        const initial = displayApp.charAt(0).toUpperCase();

        chip.innerHTML = `
            <div class="app-icon" style="background: hsla(${hue}, 70%, 60%, 0.9);">${initial}</div>
            <span class="app-name-chip">${displayApp}</span>
            <button onclick="removeAutoApp(${originalIndex})" title="Remove">&times;</button>
        `;
        container.appendChild(chip);
    });
}

function addAutoApp() {
    const inp = document.getElementById('inp-auto-app');
    const val = inp.value.trim();
    if (val && !autoTurboApps.includes(val)) {
        autoTurboApps.push(val);
        inp.value = '';
        renderAutoApps();
        saveSettings();
    }
}

function removeAutoApp(index) {
    autoTurboApps.splice(index, 1);
    renderAutoApps();
    saveSettings();
}

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file && file.name) {
        document.getElementById('inp-auto-app').value = file.name;
        addAutoApp();
    }
    // Reset input so the same file can be selected again if removed
    event.target.value = '';
}

// Init
window.onload = () => {
    fetchSettings();
    fetchStatus();
    setInterval(fetchStatus, 1000);
};
