let state = {};

async function fetchStatus() {
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
        autostart: document.getElementById('chk-start').checked
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

// Init
window.onload = () => {
    fetchSettings();
    fetchStatus();
    setInterval(fetchStatus, 1000);
};
