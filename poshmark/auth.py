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
            log_activity("posh_login", "Starting Chrome browser...", "info")
            driver = get_browser()

            log_activity("posh_login", "Navigating to Poshmark login...", "info")
            driver.get(f"{POSH_URL}/login")
            time.sleep(3)

            # Log page title to confirm page loaded
            log_activity("posh_login", f"Page loaded: {driver.title}", "info")

            # Try multiple selector strategies for username field
            user_field = None
            for selector_type, selector in [
                (By.ID, "login_form_username_email"),
                (By.NAME, "login_form[username_email]"),
                (By.CSS_SELECTOR, "input[name='login_form[username_email]']"),
                (By.CSS_SELECTOR, "input[type='email']"),
                (By.CSS_SELECTOR, "input[type='text']"),
            ]:
                try:
                    user_field = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((selector_type, selector))
                    )
                    if user_field:
                        log_activity("posh_login", f"Found username field with: {selector}", "info")
                        break
                except Exception:
                    continue

            if not user_field:
                # Log what we can see on the page for debugging
                inputs = driver.find_elements(By.TAG_NAME, "input")
                input_info = [f"{i.get_attribute('name')}|{i.get_attribute('type')}|{i.get_attribute('id')}" for i in inputs[:10]]
                log_activity("posh_login", f"No username field found. Inputs on page: {input_info}", "error")
                return {"success": False, "error": "Could not find login form. Poshmark may have changed their page layout."}

            user_field.clear()
            user_field.send_keys(username)
            log_activity("posh_login", "Entered username", "info")

            # Try multiple selectors for password field
            pw_field = None
            for selector_type, selector in [
                (By.ID, "login_form_password"),
                (By.NAME, "login_form[password]"),
                (By.CSS_SELECTOR, "input[type='password']"),
            ]:
                try:
                    pw_field = driver.find_element(selector_type, selector)
                    if pw_field:
                        break
                except Exception:
                    continue

            if not pw_field:
                return {"success": False, "error": "Could not find password field."}

            pw_field.clear()
            pw_field.send_keys(password)
            log_activity("posh_login", "Entered password", "info")

            # Submit
            pw_field.send_keys(Keys.RETURN)
            log_activity("posh_login", "Submitted login form, waiting...", "info")
            time.sleep(5)

            self.username = username

            # Log where we ended up
            log_activity("posh_login", f"Current URL: {driver.current_url}", "info")

            # Check if we landed on a verification page
            page_source = driver.page_source.lower()
            current_url = driver.current_url.lower()

            if any(kw in page_source for kw in ["verification", "verify your", "enter the code", "confirm your"]) \
                    or "verify" in current_url or "code" in current_url:
                self._awaiting_code = True
                log_activity("posh_login", "Verification code required")
                return {
                    "success": False,
                    "needs_code": True,
                    "message": "Verification code sent to your email.",
                }

            # Check if login succeeded
            if "/login" not in driver.current_url:
                self.logged_in = True
                self._save_state()
                log_activity("posh_login", f"Connected as {username}")
                return {"success": True, "username": username}

            # Still on login page - check for errors
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
            log_activity("posh_login", f"Exception: {str(e)}", "error")
            return {"success": False, "error": f"Error: {str(e)}"}

    def submit_verification_code(self, code):
        try:
            driver = get_browser()
            code = code.strip().replace(" ", "")
            log_activity("posh_verify", f"Submitting code ({len(code)} digits)...", "info")

            # Strategy 1: Individual digit input boxes (one per digit)
            digit_inputs = driver.find_elements(By.CSS_SELECTOR,
                "input[maxlength='1'], input[data-index], input[aria-label*='digit']"
            )
            # Filter to visible ones
            digit_inputs = [i for i in digit_inputs if i.is_displayed()]

            if len(digit_inputs) >= len(code):
                log_activity("posh_verify", f"Found {len(digit_inputs)} digit boxes", "info")
                for i, digit in enumerate(code):
                    try:
                        digit_inputs[i].click()
                        time.sleep(0.1)
                        digit_inputs[i].send_keys(digit)
                    except Exception:
                        # Use JS as fallback
                        driver.execute_script(
                            "arguments[0].value = arguments[1]; "
                            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
                            digit_inputs[i], digit
                        )
                time.sleep(1)
            else:
                # Strategy 2: Single input field - use JS to set value
                code_input = None
                for selector in [
                    "input[name*='code']", "input[name*='verify']",
                    "input[type='tel']", "input[type='number']",
                    "input[placeholder*='code']", "input[placeholder*='Code']",
                    "input[autocomplete='one-time-code']",
                ]:
                    try:
                        el = driver.find_element(By.CSS_SELECTOR, selector)
                        if el.is_displayed():
                            code_input = el
                            log_activity("posh_verify", f"Found code input: {selector}", "info")
                            break
                    except Exception:
                        continue

                if not code_input:
                    # Fallback: any visible input
                    all_inputs = driver.find_elements(By.TAG_NAME, "input")
                    for inp in all_inputs:
                        if inp.is_displayed() and inp.get_attribute("type") in ("text", "tel", "number", ""):
                            code_input = inp
                            break

                if not code_input:
                    inputs_info = [(i.get_attribute("type"), i.get_attribute("name"), i.get_attribute("maxlength"))
                                   for i in driver.find_elements(By.TAG_NAME, "input") if i.is_displayed()]
                    log_activity("posh_verify", f"No code input. Visible inputs: {inputs_info}", "error")
                    return {"success": False, "error": "Could not find code input on page."}

                # Use JS to set value (avoids "invalid element state")
                driver.execute_script(
                    "arguments[0].focus(); arguments[0].value = ''; arguments[0].value = arguments[1]; "
                    "arguments[0].dispatchEvent(new Event('input', {bubbles: true})); "
                    "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
                    code_input, code
                )
                time.sleep(0.5)

            # Click submit button
            submitted = False
            for btn_text in ["Verify", "Submit", "Confirm", "Continue", "Done"]:
                try:
                    btn = driver.find_element(By.XPATH, f"//button[contains(text(), '{btn_text}')]")
                    if btn.is_displayed() and btn.is_enabled():
                        btn.click()
                        submitted = True
                        log_activity("posh_verify", f"Clicked '{btn_text}' button", "info")
                        break
                except Exception:
                    continue

            if not submitted:
                # Try any submit button
                try:
                    btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                    btn.click()
                    submitted = True
                except Exception:
                    pass

            if not submitted:
                # Last resort: press Enter on the last input
                last_input = digit_inputs[-1] if digit_inputs else code_input
                if last_input:
                    last_input.send_keys(Keys.RETURN)

            log_activity("posh_verify", "Waiting for verification result...", "info")
            time.sleep(5)

            log_activity("posh_verify", f"Current URL: {driver.current_url}", "info")

            if "/login" not in driver.current_url.lower() and "verify" not in driver.current_url.lower():
                self.logged_in = True
                self._awaiting_code = False
                self._save_state()
                log_activity("posh_login", f"Connected as {self.username} (verified)")
                return {"success": True, "username": self.username}

            page_source = driver.page_source.lower()
            if "invalid" in page_source or "incorrect" in page_source or "expired" in page_source:
                return {"success": False, "error": "Invalid or expired code."}

            return {"success": False, "error": "Verification failed. Try again."}

        except Exception as e:
            return {"success": False, "error": f"Error: {str(e)}"}

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
