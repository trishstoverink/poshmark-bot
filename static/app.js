// ── State ────────────────────────────────────────────────────
let shareRunning = false;
let offerRunning = false;

// ── API helpers ─────────────────────────────────────────────
async function api(path, method = "GET", body = null) {
    const opts = { method, headers: { "Content-Type": "application/json" } };
    if (body) opts.body = JSON.stringify(body);
    const resp = await fetch(path, opts);
    return resp.json();
}

// ── Auth ────────────────────────────────────────────────────
document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;
    const errEl = document.getElementById("login-error");
    errEl.classList.add("hidden");

    const result = await api("/api/login", "POST", { username, password });
    if (result.success) {
        showLoggedIn(result.username);
    } else {
        errEl.textContent = result.error || "Login failed";
        errEl.classList.remove("hidden");
    }
});

function showLoggedIn(username) {
    document.getElementById("login-panel").classList.add("hidden");
    document.getElementById("main-controls").classList.remove("hidden");
    const badge = document.getElementById("auth-status");
    badge.textContent = username;
    badge.className = "status-badge online";
}

function showLoggedOut() {
    document.getElementById("login-panel").classList.remove("hidden");
    document.getElementById("main-controls").classList.add("hidden");
    const badge = document.getElementById("auth-status");
    badge.textContent = "Not logged in";
    badge.className = "status-badge offline";
}

async function doLogout() {
    await api("/api/logout", "POST");
    shareRunning = false;
    offerRunning = false;
    updateToggleButtons();
    showLoggedOut();
}

// ── Settings ────────────────────────────────────────────────
const SETTING_KEYS = [
    "share_delay_min", "share_delay_max", "share_interval_minutes",
    "share_order", "offer_discount_percent", "offer_min_price",
    "offer_check_interval_minutes", "offer_shipping_discount",
];

async function loadSettings() {
    const settings = await api("/api/settings");
    for (const key of SETTING_KEYS) {
        const el = document.getElementById(key);
        if (!el) continue;
        if (el.type === "checkbox") {
            el.checked = settings[key];
        } else {
            el.value = settings[key];
        }
    }
    // Update displayed range values
    const minVal = document.getElementById("share_delay_min_val");
    const maxVal = document.getElementById("share_delay_max_val");
    const discVal = document.getElementById("offer_discount_val");
    if (minVal) minVal.textContent = settings.share_delay_min;
    if (maxVal) maxVal.textContent = settings.share_delay_max;
    if (discVal) discVal.textContent = settings.offer_discount_percent;
}

async function saveSettings() {
    const data = {};
    for (const key of SETTING_KEYS) {
        const el = document.getElementById(key);
        if (!el) continue;
        if (el.type === "checkbox") {
            data[key] = el.checked;
        } else if (el.type === "number" || el.type === "range") {
            data[key] = parseFloat(el.value);
        } else {
            data[key] = el.value;
        }
    }
    await api("/api/settings", "POST", data);
}

// ── Bot Controls ────────────────────────────────────────────
async function toggleShare() {
    if (shareRunning) {
        await api("/api/bot/share/stop", "POST");
        shareRunning = false;
    } else {
        await saveSettings();
        const result = await api("/api/bot/share/start", "POST");
        if (result.success) shareRunning = true;
    }
    updateToggleButtons();
}

async function toggleOffer() {
    if (offerRunning) {
        await api("/api/bot/offer/stop", "POST");
        offerRunning = false;
    } else {
        await saveSettings();
        const result = await api("/api/bot/offer/start", "POST");
        if (result.success) offerRunning = true;
    }
    updateToggleButtons();
}

function updateToggleButtons() {
    const shareBtn = document.getElementById("share-toggle");
    const offerBtn = document.getElementById("offer-toggle");

    if (shareRunning) {
        shareBtn.textContent = "Stop";
        shareBtn.className = "btn btn-stop";
    } else {
        shareBtn.textContent = "Start";
        shareBtn.className = "btn btn-success";
    }

    if (offerRunning) {
        offerBtn.textContent = "Stop";
        offerBtn.className = "btn btn-stop";
    } else {
        offerBtn.textContent = "Start";
        offerBtn.className = "btn btn-success";
    }
}

// ── Status Polling ──────────────────────────────────────────
async function pollStatus() {
    try {
        const status = await api("/api/bot/status");
        shareRunning = status.share_running;
        offerRunning = status.offer_running;
        updateToggleButtons();

        document.getElementById("shares-today").textContent = status.shares_today;
        document.getElementById("offers-today").textContent = status.offers_today;
        document.getElementById("last-share").textContent = status.last_share_time || "--";
        document.getElementById("last-offer").textContent = status.last_offer_time || "--";
    } catch (e) {
        // server unreachable, ignore
    }
}

// ── Activity Log ────────────────────────────────────────────
function getActionClass(action) {
    if (action.includes("share")) return "share";
    if (action.includes("offer")) return "offer";
    if (action.includes("login") || action.includes("logout")) return "login";
    if (action.includes("error")) return "error";
    return "system";
}

async function pollActivity() {
    try {
        const logs = await api("/api/activity?limit=30");
        const container = document.getElementById("activity-log");

        if (!logs.length) {
            container.innerHTML = '<p class="log-empty">No activity yet</p>';
            return;
        }

        container.innerHTML = logs.map(entry => {
            const time = entry.timestamp ? entry.timestamp.split(" ")[1]?.substring(0, 8) || "" : "";
            const cls = entry.status === "error" ? "error" : getActionClass(entry.action);
            const detail = (entry.detail || "").replace(/</g, "&lt;");
            return `<div class="log-entry">
                <span class="log-time">${time}</span>
                <span class="log-action ${cls}">${entry.action}</span>
                <span class="log-detail">${detail}</span>
            </div>`;
        }).join("");
    } catch (e) {
        // ignore
    }
}

// ── Init ────────────────────────────────────────────────────
async function init() {
    const authResult = await api("/api/auth/status");
    if (authResult.logged_in) {
        showLoggedIn(authResult.username);
    }
    await loadSettings();
    await pollStatus();
    await pollActivity();

    // Poll every 5 seconds
    setInterval(pollStatus, 5000);
    setInterval(pollActivity, 5000);
}

init();
