// ── State ────────────────────────────────────────────────────
let shareRunning = false;
let offerRunning = false;
let isAdmin = false;

// ── API helpers ─────────────────────────────────────────────
async function api(path, method = "GET", body = null, timeoutMs = 30000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const opts = { method, headers: { "Content-Type": "application/json" }, signal: controller.signal };
    if (body) opts.body = JSON.stringify(body);
    try {
        const resp = await fetch(path, opts);
        clearTimeout(timer);
        if (resp.status === 401) {
            window.location.href = "/auth";
            return {};
        }
        return resp.json();
    } catch (e) {
        clearTimeout(timer);
        if (e.name === "AbortError") {
            return { success: false, error: "Request timed out. Check the activity log for details." };
        }
        return { success: false, error: e.message };
    }
}

// ── Account Auth ────────────────────────────────────────────
async function accountLogout() {
    await api("/api/user/logout", "POST");
    window.location.href = "/auth";
}

// ── Poshmark Auth ───────────────────────────────────────────
document.getElementById("posh-login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = document.getElementById("posh-username").value;
    const password = document.getElementById("posh-password").value;
    const errEl = document.getElementById("posh-login-error");
    const btn = document.getElementById("posh-connect-btn");
    errEl.classList.add("hidden");
    btn.textContent = "Connecting...";
    btn.disabled = true;

    const result = await api("/api/posh/login", "POST", { username, password }, 90000);
    btn.textContent = "Connect";
    btn.disabled = false;

    if (result.success) {
        showPoshConnected(result.username);
    } else if (result.needs_code) {
        // Show verification code panel
        document.getElementById("posh-login-form").classList.add("hidden");
        document.getElementById("posh-verify-panel").classList.remove("hidden");
    } else {
        errEl.textContent = result.error || "Connection failed";
        errEl.classList.remove("hidden");
    }
});

// Verification code submission
document.getElementById("posh-verify-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const code = document.getElementById("posh-code").value;
    const errEl = document.getElementById("posh-verify-error");
    const btn = document.getElementById("posh-verify-btn");
    errEl.classList.add("hidden");
    btn.textContent = "Verifying...";
    btn.disabled = true;

    const result = await api("/api/posh/verify", "POST", { code }, 90000);
    btn.textContent = "Verify";
    btn.disabled = false;

    if (result.success) {
        showPoshConnected(result.username);
    } else {
        errEl.textContent = result.error || "Verification failed";
        errEl.classList.remove("hidden");
    }
});

function showPoshConnected(username) {
    document.getElementById("posh-login-panel").classList.add("hidden");
    document.getElementById("posh-verify-panel").classList.add("hidden");
    document.getElementById("main-controls").classList.remove("hidden");
    const badge = document.getElementById("posh-status");
    badge.textContent = "Poshmark: " + username;
    badge.className = "status-badge online";
}

function showPoshDisconnected() {
    document.getElementById("posh-login-panel").classList.remove("hidden");
    document.getElementById("posh-login-form").classList.remove("hidden");
    document.getElementById("posh-verify-panel").classList.add("hidden");
    document.getElementById("main-controls").classList.add("hidden");
    const badge = document.getElementById("posh-status");
    badge.textContent = "Poshmark: Not connected";
    badge.className = "status-badge offline";
}

async function doPoshLogout() {
    await api("/api/posh/logout", "POST");
    shareRunning = false;
    offerRunning = false;
    updateToggleButtons();
    showPoshDisconnected();
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
    } catch (e) {}
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
    } catch (e) {}
}

// ── Admin: User Management ──────────────────────────────────
async function loadUsers() {
    if (!isAdmin) return;
    const users = await api("/api/admin/users");
    const container = document.getElementById("user-list");
    if (!Array.isArray(users)) return;

    container.innerHTML = users.map(u => {
        const badge = u.is_admin ? '<span style="color:#fbbf24; font-size:11px; margin-left:6px;">ADMIN</span>' : '';
        const deleteBtn = u.is_admin ? '' :
            `<button class="btn btn-danger" style="padding:4px 10px; font-size:11px;" onclick="deleteUser('${u.username}')">Remove</button>`;
        return `<div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid #2d3148;">
            <span>${u.username}${badge} <span style="color:#6b7280; font-size:11px;">joined ${u.created_at || ''}</span></span>
            ${deleteBtn}
        </div>`;
    }).join("");
}

async function deleteUser(username) {
    if (!confirm("Remove user '" + username + "'? They will no longer be able to sign in.")) return;
    const result = await api("/api/admin/users/" + encodeURIComponent(username), "DELETE");
    if (result.success) {
        loadUsers();
    } else {
        alert(result.error || "Failed to remove user");
    }
}

document.getElementById("add-user-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const errEl = document.getElementById("add-user-error");
    errEl.classList.add("hidden");
    const username = document.getElementById("new-username").value;
    const password = document.getElementById("new-password").value;
    const result = await api("/api/admin/users", "POST", { username, password });
    if (result.success) {
        document.getElementById("new-username").value = "";
        document.getElementById("new-password").value = "";
        loadUsers();
    } else {
        errEl.textContent = result.error;
        errEl.classList.remove("hidden");
    }
});

// ── Debug: Screenshot ───────────────────────────────────────
async function captureScreenshot() {
    const result = await api("/api/debug/screenshot", "GET", null, 15000);
    if (result.image) {
        const img = document.getElementById("debug-img");
        img.src = "data:image/png;base64," + result.image;
        img.style.display = "block";
        document.getElementById("debug-url").textContent = "URL: " + (result.url || "unknown");
    } else {
        alert(result.error || "Could not capture screenshot");
    }
}

// ── Init ────────────────────────────────────────────────────
async function init() {
    // Check account status
    const userStatus = await api("/api/user/status");
    if (!userStatus.logged_in) {
        window.location.href = "/auth";
        return;
    }
    isAdmin = userStatus.is_admin;

    // Show admin panel and debug panel if admin
    if (isAdmin) {
        document.getElementById("admin-panel").classList.remove("hidden");
        document.getElementById("debug-panel").classList.remove("hidden");
        loadUsers();
    }

    // Check Poshmark connection
    const poshStatus = await api("/api/posh/status");
    if (poshStatus.logged_in) {
        showPoshConnected(poshStatus.username);
    }

    await loadSettings();
    await pollStatus();
    await pollActivity();

    setInterval(pollStatus, 5000);
    setInterval(pollActivity, 5000);
}

init();
