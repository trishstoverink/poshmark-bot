import os
import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

_browser = None
_lock = threading.Lock()

CHROME_BIN = os.environ.get("CHROME_BIN", "/opt/chrome-linux64/chrome")
CHROMEDRIVER = os.environ.get("CHROMEDRIVER_PATH", "/opt/chromedriver-linux64/chromedriver")


def get_browser():
    global _browser
    with _lock:
        if _browser is None or _is_dead(_browser):
            _browser = _create_browser()
        return _browser


def _is_dead(driver):
    try:
        _ = driver.title
        return False
    except Exception:
        return True


def _create_browser():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    # Set Chrome binary location
    if os.path.exists(CHROME_BIN):
        opts.binary_location = CHROME_BIN

    # Set ChromeDriver path
    if os.path.exists(CHROMEDRIVER):
        service = Service(executable_path=CHROMEDRIVER)
    else:
        # Fallback: let Selenium try to find it on PATH
        service = Service()

    driver = webdriver.Chrome(service=service, options=opts)
    driver.implicitly_wait(10)
    return driver


def close_browser():
    global _browser
    with _lock:
        if _browser:
            try:
                _browser.quit()
            except Exception:
                pass
            _browser = None
