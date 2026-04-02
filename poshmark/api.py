import time
import math
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
            log_activity("fetch_listings", "Not logged in", "error")
            return []

        username = self.auth.get_username()
        listings = []

        try:
            driver.get(f"{POSH_URL}/closet/{username}")
            time.sleep(4)

            # Scroll down to load more listings
            for _ in range(5):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)

            # Use JavaScript to extract listing data — much more reliable than CSS selectors
            listings = driver.execute_script("""
                var results = [];
                // Find all links to listings
                var links = document.querySelectorAll('a[href*="/listing/"]');
                var seen = new Set();
                for (var i = 0; i < links.length; i++) {
                    var href = links[i].href;
                    // Extract listing ID from URL
                    var match = href.match(/\\/listing\\/([^/?]+)/);
                    if (!match) continue;
                    var id = match[1];
                    if (seen.has(id)) continue;
                    seen.add(id);

                    // Find the parent card/tile element
                    var card = links[i].closest('[data-et-name], .card, .tile, [class*="card"]') || links[i].parentElement;

                    // Get title
                    var title = 'Unknown';
                    var titleEl = card ? card.querySelector('a[href*="/listing/"] .title, [class*="title"], .fw--bold') : null;
                    if (!titleEl) titleEl = links[i];
                    title = (titleEl.textContent || titleEl.title || '').trim().substring(0, 80);
                    if (!title || title.length < 2) title = 'Listing ' + id.substring(0, 8);

                    // Get price
                    var price = 0;
                    var priceEls = card ? card.querySelectorAll('span, div') : [];
                    for (var j = 0; j < priceEls.length; j++) {
                        var txt = priceEls[j].textContent.trim();
                        var priceMatch = txt.match(/^\\$([\\d,]+)/);
                        if (priceMatch) {
                            price = parseFloat(priceMatch[1].replace(',', ''));
                            break;
                        }
                    }

                    // Skip sold items
                    var cardText = card ? card.textContent.toUpperCase() : '';
                    if (cardText.includes('SOLD') || cardText.includes('NOT FOR SALE')) continue;

                    results.push({id: id, url: href, title: title, price: price});
                }
                return results;
            """)

            log_activity("fetch_listings", f"Found {len(listings)} active listings")

        except Exception as e:
            log_activity("fetch_listings", f"Error: {e}", "error")

        return listings

    def share_listing(self, listing_id):
        """Share a listing from the closet page by clicking its share button."""
        driver = self._get_driver()
        if not driver:
            return {"success": False, "error": "Not logged in"}

        try:
            driver.get(f"{POSH_URL}/listing/{listing_id}")
            time.sleep(2)

            wait = WebDriverWait(driver, 10)

            # Find share button — try multiple selectors
            share_btn = None
            for selector in [
                "[data-et-name='share']",
                "i.icon.share-gray-large",
                ".share-wrapper-container",
                "[aria-label*='hare']",
                "a.share",
                ".social-action-bar__share",
                # Fallback: find by the share/repost icon
                "i[class*='share']",
            ]:
                try:
                    share_btn = driver.find_element(By.CSS_SELECTOR, selector)
                    if share_btn and share_btn.is_displayed():
                        break
                    share_btn = None
                except Exception:
                    continue

            # Last resort: find via JS
            if not share_btn:
                share_btn = driver.execute_script("""
                    // Look for share icon by checking all clickable elements
                    var els = document.querySelectorAll('a, button, i, div[role="button"]');
                    for (var i = 0; i < els.length; i++) {
                        var cl = (els[i].className || '').toLowerCase();
                        var aria = (els[i].getAttribute('aria-label') || '').toLowerCase();
                        if (cl.includes('share') || aria.includes('share')) return els[i];
                    }
                    return null;
                """)

            if not share_btn:
                return {"success": False, "error": "Share button not found"}

            share_btn.click()
            time.sleep(2)

            # Click "To My Followers" in the share popup
            followers_btn = None
            for selector in [
                ".share-wrapper-container",
                "a.pm-followers-share-link",
                "[data-et-name='followers']",
            ]:
                try:
                    followers_btn = driver.find_element(By.CSS_SELECTOR, selector)
                    if followers_btn and followers_btn.is_displayed():
                        break
                    followers_btn = None
                except Exception:
                    continue

            if not followers_btn:
                # Try finding by text
                try:
                    followers_btn = driver.find_element(
                        By.XPATH, "//*[contains(text(), 'Followers') or contains(text(), 'followers')]"
                    )
                except Exception:
                    pass

            if not followers_btn:
                # Try the Poshmark logo icon in the share modal
                followers_btn = driver.execute_script("""
                    var els = document.querySelectorAll('i, img, div, a');
                    for (var i = 0; i < els.length; i++) {
                        var cl = (els[i].className || '').toLowerCase();
                        if (cl.includes('pm-logo') || cl.includes('poshmark')) return els[i];
                    }
                    return null;
                """)

            if followers_btn:
                followers_btn.click()
                time.sleep(1)

            return {"success": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_listing_likes(self, listing_id):
        """Get likers of a listing."""
        driver = self._get_driver()
        if not driver:
            return []

        try:
            driver.get(f"{POSH_URL}/listing/{listing_id}")
            time.sleep(2)

            # Find and click the likes count
            likes_el = driver.execute_script("""
                var els = document.querySelectorAll('a, span, div');
                for (var i = 0; i < els.length; i++) {
                    var text = els[i].textContent.trim();
                    var aria = (els[i].getAttribute('aria-label') || '').toLowerCase();
                    if (aria.includes('like') && text.match(/^\\d+$/)) return els[i];
                }
                // Fallback: find heart icon with a count
                var hearts = document.querySelectorAll('[class*="like"], [class*="heart"]');
                for (var i = 0; i < hearts.length; i++) {
                    var parent = hearts[i].parentElement;
                    if (parent && parent.textContent.trim().match(/^\\d+$/)) return parent;
                }
                return null;
            """)

            if not likes_el:
                return []

            likes_el.click()
            time.sleep(2)

            # Scrape likers from the modal/page
            likers = driver.execute_script("""
                var results = [];
                var links = document.querySelectorAll('a[href*="/closet/"]');
                var seen = new Set();
                for (var i = 0; i < links.length; i++) {
                    var href = links[i].href;
                    var match = href.match(/\\/closet\\/([^/?]+)/);
                    if (match && !seen.has(match[1])) {
                        seen.add(match[1]);
                        results.push({id: match[1], username: match[1]});
                    }
                }
                return results;
            """)

            return likers or []

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

            # Find and click the "Offer/Price Drop" button
            offer_btn = driver.execute_script("""
                var els = document.querySelectorAll('button, a, div[role="button"]');
                for (var i = 0; i < els.length; i++) {
                    var text = els[i].textContent.toLowerCase();
                    if (text.includes('offer') && text.includes('liker')) return els[i];
                    if (text.includes('price drop')) return els[i];
                }
                return null;
            """)

            if not offer_btn:
                return {"success": False, "error": "Offer button not found on listing"}

            offer_btn.click()
            time.sleep(2)

            # Fill in offer price
            price_input = None
            for selector in [
                "input[name*='price']",
                "input[placeholder*='price']",
                "input[placeholder*='Price']",
                "input[type='number']",
                "input[type='tel']",
            ]:
                try:
                    el = driver.find_element(By.CSS_SELECTOR, selector)
                    if el.is_displayed():
                        price_input = el
                        break
                except Exception:
                    continue

            if not price_input:
                return {"success": False, "error": "Price input not found"}

            price_input.click()
            price_input.clear()
            time.sleep(0.3)
            price_input.send_keys(str(int(price)))
            time.sleep(0.5)

            # Handle shipping discount
            if shipping_discount:
                try:
                    ship_el = driver.execute_script("""
                        var labels = document.querySelectorAll('label, div, span');
                        for (var i = 0; i < labels.length; i++) {
                            var text = labels[i].textContent.toLowerCase();
                            if (text.includes('shipping') && text.includes('discount')) {
                                var input = labels[i].querySelector('input') || labels[i].previousElementSibling;
                                if (input && input.type === 'checkbox' && !input.checked) return labels[i];
                            }
                        }
                        return null;
                    """)
                    if ship_el:
                        ship_el.click()
                except Exception:
                    pass

            # Click submit
            time.sleep(0.5)
            submit_btn = driver.execute_script("""
                var btns = document.querySelectorAll('button');
                for (var i = 0; i < btns.length; i++) {
                    var text = btns[i].textContent.toLowerCase();
                    if (text.includes('submit') || text.includes('apply') || text.includes('send')) return btns[i];
                }
                return null;
            """)

            if submit_btn:
                submit_btn.click()
                time.sleep(2)
                return {"success": True}

            return {"success": False, "error": "Submit button not found"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def calculate_offer_price(self, original_price, discount_percent, min_price):
        discounted = original_price * (1 - discount_percent / 100)
        discounted = math.floor(discounted)
        return max(discounted, min_price)
