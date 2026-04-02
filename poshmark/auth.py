import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from database import save_session, load_session, clear_session, log_activity
from poshmark.browser import get_browser, close_browser

POSH_URL = "https://poshmark.com"


class PoshmarkAuth:
    def __init__(self):
        self.username = None
        self.logged_in = False
        self._restore_session()

    def _restore_session(self):
        username = load_session("username")
        was_logged_in = load_session("logged_in")
        if username and was_logged_in:
            self.username = username
            # We'll re-verify on first API call

    def _save_state(self):
        if self.username:
            save_session("username", self.username)
        save_session("logged_in", self.logged_in)

    def login(self, username, password):
        try:
            driver = get_browser()
            driver.get(f"{POSH_URL}/login")
            time.sleep(2)

            wait = WebDriverWait(driver, 15)

            # Find and fill username field
            user_field = wait.until(
                EC.presence_of_element_located((By.NAME, "login_form[username_email]"))
            )
            user_field.clear()
            user_field.send_keys(username)

            # Find and fill password field
            pw_field = driver.find_element(By.NAME, "login_form[password]")
            pw_field.clear()
            pw_field.send_keys(password)

            # Click login button
            login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_btn.click()

            # Wait for navigation away from login page
            time.sleep(3)

            # Check if login succeeded by looking at current URL or page content
            if "/login" not in driver.current_url:
                self.username = username
                self.logged_in = True
                self._save_state()
                log_activity("posh_login", f"Connected as {username}")
                return {"success": True, "username": username}

            # Check for error messages on page
            try:
                error_el = driver.find_element(By.CSS_SELECTOR, ".form__error-message, .error-message, [class*='error']")
                error_text = error_el.text.strip()
                if error_text:
                    return {"success": False, "error": error_text}
            except Exception:
                pass

            return {"success": False, "error": "Login failed. Check your credentials."}

        except Exception as e:
            return {"success": False, "error": f"Browser error: {str(e)}"}

    def logout(self):
        clear_session()
        self.username = None
        self.logged_in = False
        try:
            driver = get_browser()
            driver.delete_all_cookies()
            driver.get(f"{POSH_URL}/logout")
        except Exception:
            pass
        log_activity("posh_logout", "Disconnected from Poshmark")

    def is_logged_in(self):
        if not self.username:
            return False
        return self.logged_in

    def ensure_logged_in(self):
        """Verify we're still logged in, return the browser driver."""
        driver = get_browser()
        if not self.logged_in:
            return None
        return driver

    def get_username(self):
        return self.username
