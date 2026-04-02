import time
import math
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from database import log_activity
from poshmark.browser import get_browser

POSH_URL = "https://poshmark.com"


class PoshmarkAPI:
    def __init__(self, auth):
        self.auth = auth

    def _get_driver(self):
        return self.auth.ensure_logged_in()

    def get_my_listings(self):
        """Fetch all active listings by scraping the closet page."""
        driver = self._get_driver()
        if not driver:
            return []

        username = self.auth.get_username()
        listings = []

        try:
            driver.get(f"{POSH_URL}/closet/{username}")
            time.sleep(3)

            # Scroll down to load more listings
            for _ in range(5):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)

            # Find all listing tiles
            tiles = driver.find_elements(By.CSS_SELECTOR, "[data-et-name='listing'], .card--small, .tile")

            for tile in tiles:
                try:
                    listing = {}
                    # Get listing link/id
                    link = tile.find_element(By.CSS_SELECTOR, "a[href*='/listing/']")
                    href = link.get_attribute("href")
                    listing["id"] = href.split("/listing/")[1].split("?")[0].split("/")[0] if "/listing/" in href else ""
                    listing["url"] = href

                    # Get title
                    try:
                        title_el = tile.find_element(By.CSS_SELECTOR, ".tile__title, .card__title, [data-et-name='title']")
                        listing["title"] = title_el.text.strip()
                    except Exception:
                        listing["title"] = "Unknown"

                    # Get price
                    try:
                        price_el = tile.find_element(By.CSS_SELECTOR, ".fw--bold, [data-et-name='price']")
                        price_text = price_el.text.strip().replace("$", "").replace(",", "")
                        listing["price"] = float(price_text) if price_text else 0
                    except Exception:
                        listing["price"] = 0

                    if listing["id"]:
                        listings.append(listing)
                except Exception:
                    continue

            log_activity("fetch_listings", f"Found {len(listings)} listings")

        except Exception as e:
            log_activity("fetch_listings", f"Error: {e}", "error")

        return listings

    def share_listing(self, listing_id):
        """Share a listing by clicking the share button on Poshmark."""
        driver = self._get_driver()
        if not driver:
            return {"success": False, "error": "Not logged in"}

        try:
            driver.get(f"{POSH_URL}/listing/{listing_id}")
            time.sleep(2)

            wait = WebDriverWait(driver, 10)

            # Click the share button
            share_btn = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "[data-et-name='share'], .share-button, [aria-label*='Share'], .social-action-bar__share")
            ))
            share_btn.click()
            time.sleep(1)

            # Click "To My Followers" option in the share menu
            try:
                followers_btn = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//*[contains(text(), 'My Followers') or contains(text(), 'Followers')]")
                ))
                followers_btn.click()
                time.sleep(1)
            except Exception:
                # Some layouts auto-share to followers on first click
                pass

            return {"success": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_listing_likes(self, listing_id):
        """Get likers of a listing by scraping the likes page."""
        driver = self._get_driver()
        if not driver:
            return []

        try:
            driver.get(f"{POSH_URL}/listing/{listing_id}")
            time.sleep(2)

            # Click the likes count to see likers
            try:
                likes_link = driver.find_element(
                    By.CSS_SELECTOR, "[data-et-name='likes'], .like-count, [aria-label*='like']"
                )
                likes_link.click()
                time.sleep(2)
            except Exception:
                return []

            # Scrape liker usernames
            likers = []
            liker_elements = driver.find_elements(
                By.CSS_SELECTOR, ".user-list__item a, .liker a, [data-et-name='user']"
            )
            for el in liker_elements:
                try:
                    href = el.get_attribute("href") or ""
                    username = href.rstrip("/").split("/")[-1] if href else el.text.strip()
                    if username:
                        likers.append({"id": username, "username": username})
                except Exception:
                    continue

            return likers

        except Exception:
            return []

    def send_offer(self, listing_id, price, shipping_discount=True):
        """Send an offer to likers via the listing page."""
        driver = self._get_driver()
        if not driver:
            return {"success": False, "error": "Not logged in"}

        try:
            driver.get(f"{POSH_URL}/listing/{listing_id}")
            time.sleep(2)

            wait = WebDriverWait(driver, 10)

            # Click "Offer to Likers" or similar button
            offer_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//*[contains(text(), 'Offer') and (contains(text(), 'Liker') or contains(text(), 'liker'))]")
            ))
            offer_btn.click()
            time.sleep(2)

            # Fill in offer price
            price_input = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[name*='price'], input[placeholder*='price'], input[type='number']")
            ))
            price_input.clear()
            price_input.send_keys(str(int(price)))
            time.sleep(0.5)

            # Handle shipping discount
            if shipping_discount:
                try:
                    shipping_opt = driver.find_element(
                        By.XPATH, "//*[contains(text(), 'Discounted Shipping') or contains(text(), 'shipping')]//input[@type='checkbox'] | //input[contains(@name, 'shipping')]"
                    )
                    if not shipping_opt.is_selected():
                        shipping_opt.click()
                except Exception:
                    pass

            # Submit the offer
            submit_btn = driver.find_element(
                By.XPATH, "//button[contains(text(), 'Submit') or contains(text(), 'Apply') or contains(text(), 'Send')]"
            )
            submit_btn.click()
            time.sleep(2)

            return {"success": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def calculate_offer_price(self, original_price, discount_percent, min_price):
        """Calculate offer price based on discount %, respecting minimum."""
        discounted = original_price * (1 - discount_percent / 100)
        discounted = math.floor(discounted)
        return max(discounted, min_price)
