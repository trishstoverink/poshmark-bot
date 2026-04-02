import requests
import uuid
from database import save_session, load_session, clear_session, log_activity

BASE_URL = "https://poshmark.com"

# Headers that mimic a real browser
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest",
}


class PoshmarkAuth:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.username = None
        self._restore_session()

    def _restore_session(self):
        cookies = load_session("cookies")
        username = load_session("username")
        if cookies and username:
            for name, value in cookies.items():
                self.session.cookies.set(name, value)
            self.username = username

    def _save_cookies(self):
        cookies = {name: value for name, value in self.session.cookies.items()}
        save_session("cookies", cookies)
        if self.username:
            save_session("username", self.username)

    def login(self, username, password):
        self.username = username
        device_uuid = str(uuid.uuid4())

        payload = {
            "login_form": {
                "username_email": username,
                "password": password,
                "remember_me": True,
            },
            "device_uuid": device_uuid,
        }

        try:
            resp = self.session.post(
                f"{BASE_URL}/api/v1/login",
                json=payload,
                timeout=30,
            )

            if resp.status_code == 200:
                data = resp.json()
                if "error" not in data:
                    self._save_cookies()
                    log_activity("login", f"Logged in as {username}")
                    return {"success": True, "username": username}
                return {"success": False, "error": data.get("error", {}).get("message", "Login failed")}

            return {"success": False, "error": f"HTTP {resp.status_code}"}

        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def logout(self):
        clear_session()
        self.session.cookies.clear()
        self.username = None
        log_activity("logout", "Logged out")

    def is_logged_in(self):
        if not self.username:
            return False
        # Verify session is still valid by hitting a lightweight endpoint
        try:
            resp = self.session.get(
                f"{BASE_URL}/api/v1/users/me",
                timeout=10,
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def get_session(self):
        return self.session

    def get_username(self):
        return self.username
