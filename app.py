from flask import Flask, render_template, request, jsonify
from database import (
    init_db, get_all_settings, set_setting, get_activity_log, log_activity,
)
from poshmark.auth import PoshmarkAuth
from poshmark.api import PoshmarkAPI
from poshmark.bot import PoshmarkBot

app = Flask(__name__)

# Initialize components
init_db()
auth = PoshmarkAuth()
api = PoshmarkAPI(auth)
bot = PoshmarkBot(api)


# ── Pages ────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    return render_template("dashboard.html")


# ── Auth API ─────────────────────────────────────────────────

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400
    result = auth.login(username, password)
    return jsonify(result)


@app.route("/api/logout", methods=["POST"])
def logout():
    bot.stop_sharing()
    bot.stop_offers()
    auth.logout()
    return jsonify({"success": True})


@app.route("/api/auth/status")
def auth_status():
    logged_in = auth.is_logged_in()
    return jsonify({
        "logged_in": logged_in,
        "username": auth.get_username() if logged_in else None,
    })


# ── Settings API ─────────────────────────────────────────────

@app.route("/api/settings")
def get_settings():
    return jsonify(get_all_settings())


@app.route("/api/settings", methods=["POST"])
def update_settings():
    data = request.get_json()
    for key, value in data.items():
        set_setting(key, value)
    return jsonify({"success": True})


# ── Bot Control API ──────────────────────────────────────────

@app.route("/api/bot/status")
def bot_status():
    return jsonify(bot.get_status())


@app.route("/api/bot/share/start", methods=["POST"])
def start_share():
    if not auth.is_logged_in():
        return jsonify({"success": False, "error": "Not logged in"}), 401
    set_setting("share_enabled", True)
    bot.start_sharing()
    return jsonify({"success": True})


@app.route("/api/bot/share/stop", methods=["POST"])
def stop_share():
    set_setting("share_enabled", False)
    bot.stop_sharing()
    return jsonify({"success": True})


@app.route("/api/bot/offer/start", methods=["POST"])
def start_offer():
    if not auth.is_logged_in():
        return jsonify({"success": False, "error": "Not logged in"}), 401
    set_setting("offer_enabled", True)
    bot.start_offers()
    return jsonify({"success": True})


@app.route("/api/bot/offer/stop", methods=["POST"])
def stop_offer():
    set_setting("offer_enabled", False)
    bot.stop_offers()
    return jsonify({"success": True})


# ── Activity Log API ─────────────────────────────────────────

@app.route("/api/activity")
def activity():
    limit = request.args.get("limit", 50, type=int)
    return jsonify(get_activity_log(limit))


# ── Run ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  Poshmark Bot running at http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
