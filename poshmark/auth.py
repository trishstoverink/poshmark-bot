import requests
import uuid
from database import save_session, load_session, clear_session, log_activity

API_BASE = "https://api.poshmark.com/api"
WEB_BASE = "https://poshmark.com"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Mobile Safari/537.36"
    ),
    "Accept": "application/json",
}


class PoshmarkAuth:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.username = None
        self.access_token = None
        self._restore_session()

    def _restore_session(self):
        cookies = load_session("cookies")
        username = load_session("username")
        token = load_session("access_token")
        if username:
            self.username = username
        if cookies:
            for name, value in cookies.items():
                self.session.cookies.set(name, value)
        if token:
            self.access_token = token
            self.session.headers["Authorization"] = f"Bearer {token}"

    def _save_auth(self):
        cookies = {name: value for name, value in self.session.cookies.items()}
        save_session("cookies", cookies)
        if self.username:
            save_session("username", self.username)
        if self.access_token:
            save_session("access_token", self.access_token)

    def login(self, username, password):
        self.username = username

        # Method 1: Token-based API login
        try:
            resp = self.session.post(
                f"{API_BASE}/auth/users/access_token",
                data={"user_handle": username, "password": password},
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                token = data.get("access_token")
                if token:
                    self.access_token = token
                    self.session.headers["Authorization"] = f"Bearer {token}"
                    self._save_auth()
                    log_activity("posh_login", f"Connected as {username} (token)")
                    return {"success": True, "username": username}
        except Exception:
            pass

        # Method 2: Web cookie-based login
        try:
            device_uuid = str(uuid.uuid4())
            resp = self.session.post(
                f"{WEB_BASE}/api/v1/login",
                json={
                    "login_form": {
                        "username_email": username,
                        "password": password,
                        "remember_me": True,
                    },
                    "device_uuid": device_uuid,
                },
                headers={**DEFAULT_HEADERS, "Content-Type": "application/json"},
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                if "error" not in data:
                    self._save_auth()
                    log_activity("posh_login", f"Connected as {username} (cookie)")
                    return {"success": True, "username": username}
                return {"success": False, "error": data.get("error", {}).get("message", "Login failed")}

            return {"success": False, "error": f"HTTP {resp.status_code} - Poshmark may be blocking automated login. Try again later."}

        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def logout(self):
        clear_session()
        self.session.cookies.clear()
        self.session.headers.pop("Authorization", None)
        self.username = None
        self.access_token = None
        log_activity("posh_logout", "Disconnected from Poshmark")

    def is_logged_in(self):
        if not self.username:
            return False
        if self.access_token:
            return True
        # Check if cookies are still valid
        try:
            resp = self.session.get(f"{WEB_BASE}/api/v1/users/me", timeout=10)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def get_session(self):
        return self.session

    def get_username(self):
        return self.username
