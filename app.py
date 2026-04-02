import os
import secrets
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from database import (
    init_db, get_all_settings, set_setting, get_activity_log, log_activity,
    create_user, verify_user, user_count, is_admin, list_users, delete_user,
)
from poshmark.auth import PoshmarkAuth
from poshmark.api import PoshmarkAPI
from poshmark.bot import PoshmarkBot

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

# Initialize components
init_db()
posh_auth = PoshmarkAuth()
api = PoshmarkAPI(posh_auth)
bot = PoshmarkBot(api)


# ── Auth decorator ───────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Not authenticated"}), 401
            return redirect(url_for("auth_page"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return jsonify({"success": False, "error": "Not authenticated"}), 401
        if not is_admin(session["user"]):
            return jsonify({"success": False, "error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated


# ── Pages ────────────────────────────────────────────────────

@app.route("/auth")
def auth_page():
    if "user" in session:
        return redirect(url_for("dashboard"))
    show_register = user_count() == 0
    return render_template("auth.html", show_register=show_register)


@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html", user=session["user"])


# ── User Auth API ────────────────────────────────────────────

@app.route("/api/user/register", methods=["POST"])
def user_register():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400
    if len(password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters"}), 400
    result = create_user(username, password)
    if result["success"]:
        session["user"] = username
    return jsonify(result)


@app.route("/api/user/login", methods=["POST"])
def user_login():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400
    if verify_user(username, password):
        session["user"] = username
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid username or password"})


@app.route("/api/user/logout", methods=["POST"])
def user_logout():
    session.pop("user", None)
    return jsonify({"success": True})


@app.route("/api/user/status")
def user_status():
    username = session.get("user")
    return jsonify({
        "logged_in": "user" in session,
        "username": username,
        "is_admin": is_admin(username) if username else False,
    })


# ── Admin API ────────────────────────────────────────────────

@app.route("/api/admin/users")
@admin_required
def admin_list_users():
    return jsonify(list_users())


@app.route("/api/admin/users", methods=["POST"])
@admin_required
def admin_create_user():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400
    if len(password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters"}), 400
    return jsonify(create_user(username, password))


@app.route("/api/admin/users/<username>", methods=["DELETE"])
@admin_required
def admin_delete_user(username):
    if username == session.get("user"):
        return jsonify({"success": False, "error": "Cannot delete yourself"}), 400
    if delete_user(username):
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "User not found or is admin"}), 404


# ── Poshmark Auth API ────────────────────────────────────────

@app.route("/api/posh/login", methods=["POST"])
@login_required
def posh_login():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400
    result = posh_auth.login(username, password)
    return jsonify(result)


@app.route("/api/posh/logout", methods=["POST"])
@login_required
def posh_logout():
    bot.stop_sharing()
    bot.stop_offers()
    posh_auth.logout()
    return jsonify({"success": True})


@app.route("/api/posh/status")
@login_required
def posh_status():
    logged_in = posh_auth.is_logged_in()
    return jsonify({
        "logged_in": logged_in,
        "username": posh_auth.get_username() if logged_in else None,
    })


# ── Settings API ─────────────────────────────────────────────

@app.route("/api/settings")
@login_required
def get_settings():
    return jsonify(get_all_settings())


@app.route("/api/settings", methods=["POST"])
@login_required
def update_settings():
    data = request.get_json()
    for key, value in data.items():
        set_setting(key, value)
    return jsonify({"success": True})


# ── Bot Control API ──────────────────────────────────────────

@app.route("/api/bot/status")
@login_required
def bot_status():
    return jsonify(bot.get_status())


@app.route("/api/bot/share/start", methods=["POST"])
@login_required
def start_share():
    if not posh_auth.is_logged_in():
        return jsonify({"success": False, "error": "Not logged in to Poshmark"}), 401
    set_setting("share_enabled", True)
    bot.start_sharing()
    return jsonify({"success": True})


@app.route("/api/bot/share/stop", methods=["POST"])
@login_required
def stop_share():
    set_setting("share_enabled", False)
    bot.stop_sharing()
    return jsonify({"success": True})


@app.route("/api/bot/offer/start", methods=["POST"])
@login_required
def start_offer():
    if not posh_auth.is_logged_in():
        return jsonify({"success": False, "error": "Not logged in to Poshmark"}), 401
    set_setting("offer_enabled", True)
    bot.start_offers()
    return jsonify({"success": True})


@app.route("/api/bot/offer/stop", methods=["POST"])
@login_required
def stop_offer():
    set_setting("offer_enabled", False)
    bot.stop_offers()
    return jsonify({"success": True})


# ── Activity Log API ─────────────────────────────────────────

@app.route("/api/activity")
@login_required
def activity():
    limit = request.args.get("limit", 50, type=int)
    return jsonify(get_activity_log(limit))


# ── Run ──────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  Poshmark Bot running at http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
