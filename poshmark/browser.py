import threading
import undetected_chromedriver as uc

_browser = None
_lock = threading.Lock()


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
    opts = uc.ChromeOptions()
    opts.add_argument("--window-size=1920,1080")
    # Run headless so no browser window pops up
    opts.add_argument("--headless=new")

    driver = uc.Chrome(options=opts, use_subprocess=True)
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
