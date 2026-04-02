import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from database import save_session, load_session, clear_session, log_activity
from poshmark.browser import get_browser

POSH_URL = "https://poshmark.com"


class PoshmarkAuth:
    def __init__(self):
        self.username = None
        self.logged_in = False
        self._awaiting_code = False
        self._restore_session()

    def _restore_session(self):
        username = load_session("username")
        was_logged_in = load_session("logged_in")
        if username and was_logged_in:
            self.username = username
            self.logged_in = True

    def _save_state(self):
        if self.username:
            save_session("username", self.username)
        save_session("logged_in", self.logged_in)

    def login(self, username, password):
        try:
            driver = get_browser()
            driver.get(f"{POSH_URL}/login")
            time.sleep(3)

            wait = WebDriverWait(driver, 15)

            # Fill username
            user_field = wait.until(
                EC.presence_of_element_located((By.ID, "login_form_username_email"))
            )
            user_field.clear()
            user_field.send_keys(username)

            # Fill password
            pw_field = driver.find_element(By.ID, "login_form_password")
            pw_field.clear()
            pw_field.send_keys(password)

            # Submit via Enter key (most reliable across Poshmark versions)
            pw_field.send_keys(Keys.RETURN)
            time.sleep(4)

            self.username = username

            # Check if we landed on the verification code page
            page_source = driver.page_source.lower()
            current_url = driver.current_url.lower()

            if "verification" in page_source or "verify" in page_source or "code" in current_url:
                self._awaiting_code = True
                log_activity("posh_login", "Verification code sent to email")
                return {
                    "success": False,
                    "needs_code": True,
                    "message": "Verification code sent to your email. Enter it below.",
                }

            # Check if login succeeded (redirected away from login page)
            if "/login" not in driver.current_url:
                self.logged_in = True
                self._save_state()
                log_activity("posh_login", f"Connected as {username}")
                return {"success": True, "username": username}

            # Check for error messages
            try:
                errors = driver.find_elements(By.CSS_SELECTOR, ".form__error-message, .error-message, [class*='error']")
                for err in errors:
                    text = err.text.strip()
                    if text:
                        return {"success": False, "error": text}
            except Exception:
                pass

            return {"success": False, "error": "Login failed. Check your credentials."}

        except Exception as e:
            return {"success": False, "error": f"Browser error: {str(e)}"}

    def submit_verification_code(self, code):
        """Submit the email verification code."""
        try:
            driver = get_browser()
            wait = WebDriverWait(driver, 10)

            # Find the verification code input
            code_input = None
            for selector in [
                "input[name*='code']",
                "input[name*='verify']",
                "input[type='tel']",
                "input[type='number']",
                "input[placeholder*='code']",
                "input[placeholder*='Code']",
                "input[aria-label*='code']",
                "#verification_code",
            ]:
                try:
                    code_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    if code_input:
                        break
                except Exception:
                    continue

            if not code_input:
                # Try finding any visible text input on the page
                inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input[type='tel'], input[type='number'], input:not([type])")
                for inp in inputs:
                    if inp.is_displayed():
                        code_input = inp
                        break

            if not code_input:
                return {"success": False, "error": "Could not find verification code input on page."}

            code_input.clear()
            code_input.send_keys(code)
            time.sleep(0.5)

            # Try to submit - look for a submit/verify button, or just press Enter
            submitted = False
            for btn_selector in [
                "button[type='submit']",
                "button[data-pa-name*='verify']",
                "//button[contains(text(), 'Verify')]",
                "//button[contains(text(), 'Submit')]",
                "//button[contains(text(), 'Confirm')]",
                "//button[contains(text(), 'Continue')]",
            ]:
                try:
                    if btn_selector.startswith("//"):
                        btn = driver.find_element(By.XPATH, btn_selector)
                    else:
                        btn = driver.find_element(By.CSS_SELECTOR, btn_selector)
                    if btn.is_displayed():
                        btn.click()
                        submitted = True
                        break
                except Exception:
                    continue

            if not submitted:
                code_input.send_keys(Keys.RETURN)

            time.sleep(4)

            # Check if verification succeeded
            current_url = driver.current_url.lower()
            if "/login" not in current_url and "verify" not in current_url:
                self.logged_in = True
                self._awaiting_code = False
                self._save_state()
                log_activity("posh_login", f"Connected as {self.username} (verified)")
                return {"success": True, "username": self.username}

            # Still on verification page - code might be wrong
            page_source = driver.page_source.lower()
            if "invalid" in page_source or "incorrect" in page_source or "expired" in page_source:
                return {"success": False, "error": "Invalid or expired code. Try again."}

            return {"success": False, "error": "Verification failed. Please try again."}

        except Exception as e:
            return {"success": False, "error": f"Browser error: {str(e)}"}

    def is_awaiting_code(self):
        return self._awaiting_code

    def logout(self):
        clear_session()
        self.username = None
        self.logged_in = False
        self._awaiting_code = False
        try:
            driver = get_browser()
            driver.delete_all_cookies()
            driver.get(f"{POSH_URL}/logout")
        except Exception:
            pass
        log_activity("posh_logout", "Disconnected from Poshmark")

    def is_logged_in(self):
        return self.logged_in and self.username is not None

    def ensure_logged_in(self):
        if not self.logged_in:
            return None
        return get_browser()

    def get_username(self):
        return self.username
