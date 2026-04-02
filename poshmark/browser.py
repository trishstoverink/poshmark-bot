import os
import shutil
import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

_browser = None
_lock = threading.Lock()


def get_browser():
    """Get or create the shared headless Chrome browser instance."""
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

    # Use system-installed Chrome + ChromeDriver (from Dockerfile)
    chrome_path = shutil.which("google-chrome") or "/usr/bin/google-chrome"
    chromedriver_path = shutil.which("chromedriver") or "/usr/bin/chromedriver"

    if os.path.exists(chrome_path):
        opts.binary_location = chrome_path

    service = Service(executable_path=chromedriver_path)
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
