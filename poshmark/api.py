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

            # Use JavaScript to extract listing data
            listings = driver.execute_script("""
                var results = [];
                var links = document.querySelectorAll('a[href*="/listing/"]');
                var seen = new Set();
                for (var i = 0; i < links.length; i++) {
                    var href = links[i].href;
                    var match = href.match(/\\/listing\\/([^/?]+)/);
                    if (!match) continue;
                    var id = match[1];
                    if (seen.has(id)) continue;
                    seen.add(id);

                    var card = links[i].closest('[data-et-name], .card, .tile, [class*="card"]') || links[i].parentElement;

                    var title = 'Unknown';
                    var titleEl = card ? card.querySelector('a[href*="/listing/"] .title, [class*="title"], .fw--bold') : null;
                    if (!titleEl) titleEl = links[i];
                    title = (titleEl.textContent || titleEl.title || '').trim().substring(0, 80);
                    if (!title || title.length < 2) title = 'Listing ' + id.substring(0, 8);

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
        """Share a listing by navigating to it and clicking share -> followers."""
        driver = self._get_driver()
        if not driver:
            return {"success": False, "error": "Not logged in"}

        try:
            driver.get(f"{POSH_URL}/listing/{listing_id}")
            time.sleep(3)

            # Step 1: Click the share button (exact selector from inspecting the page)
            # The button is: div.social-action-bar__share[data-et-name="share"]
            clicked = driver.execute_script("""
                var el = document.querySelector('.social-action-bar__share, [data-et-name="share"]');
                if (el) { el.click(); return 'found'; }
                return 'not_found';
            """)

            if clicked == 'not_found':
                return {"success": False, "error": "Share button not found on page"}

            time.sleep(2)

            # Step 2: Click "To My Followers" in the share popup
            # The popup contains a share-wrapper-container or pm-followers-share-link
            followers_result = driver.execute_script("""
                // Try 1: share-wrapper-container class (Poshmark share to followers)
                var el = document.querySelector('.share-wrapper-container');
                if (el) { el.click(); return 'share-wrapper'; }

                // Try 2: pm-followers-share-link
                el = document.querySelector('.pm-followers-share-link');
                if (el) { el.click(); return 'pm-followers-link'; }

                // Try 3: Icon with pm-logo class (Poshmark logo in share modal)
                el = document.querySelector('i.icon.pm-logo-white, i.icon.pm-logo');
                if (el) { el.click(); return 'pm-logo'; }

                // Try 4: Any element with "Followers" text in the visible popup/modal
                var els = document.querySelectorAll('a, button, div, li');
                for (var i = 0; i < els.length; i++) {
                    var text = els[i].textContent.trim();
                    if (text === 'Poshmark' || text === 'To My Followers' || text === 'My Followers' || text === 'Followers') {
                        els[i].click();
                        return 'text-match: ' + text;
                    }
                }

                // Try 5: Look at what's in the popup/modal that appeared
                var modal = document.querySelector('[class*="modal"], [class*="popup"], [class*="share-popup"], [class*="dropdown"]');
                if (modal) {
                    var firstOption = modal.querySelector('a, button, div[role="button"], li');
                    if (firstOption) { firstOption.click(); return 'first-modal-option'; }
                }

                return 'followers_not_found';
            """)

            log_activity("share_debug", f"Followers click result: {followers_result}", "info")
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
            time.sleep(3)

            # Click the likes count
            driver.execute_script("""
                var els = document.querySelectorAll('a, span, div, button');
                for (var i = 0; i < els.length; i++) {
                    var aria = (els[i].getAttribute('aria-label') || '').toLowerCase();
                    var cl = (els[i].className || '').toLowerCase();
                    if ((aria.includes('like') || cl.includes('like')) && els[i].textContent.trim().match(/^\\d+$/)) {
                        els[i].click();
                        return true;
                    }
                }
                return false;
            """)
            time.sleep(2)

            # Scrape likers
            likers = driver.execute_script("""
                var results = [];
                var links = document.querySelectorAll('a[href*="/closet/"]');
                var seen = new Set();
                for (var i = 0; i < links.length; i++) {
                    var match = links[i].href.match(/\\/closet\\/([^/?]+)/);
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
            time.sleep(3)

            # Click the offer/price drop button
            found = driver.execute_script("""
                var els = document.querySelectorAll('button, a, div[role="button"]');
                for (var i = 0; i < els.length; i++) {
                    var text = els[i].textContent.toLowerCase();
                    if (text.includes('offer') && text.includes('liker')) { els[i].click(); return true; }
                    if (text.includes('price drop')) { els[i].click(); return true; }
                }
                return false;
            """)

            if not found:
                return {"success": False, "error": "Offer button not found"}

            time.sleep(2)

            # Fill price via JS
            driver.execute_script("""
                var inputs = document.querySelectorAll('input');
                for (var i = 0; i < inputs.length; i++) {
                    var name = (inputs[i].name || '').toLowerCase();
                    var ph = (inputs[i].placeholder || '').toLowerCase();
                    if (name.includes('price') || ph.includes('price') || inputs[i].type === 'number') {
                        var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                        nativeInputValueSetter.call(inputs[i], arguments[0]);
                        inputs[i].dispatchEvent(new Event('input', {bubbles: true}));
                        inputs[i].dispatchEvent(new Event('change', {bubbles: true}));
                        break;
                    }
                }
            """, str(int(price)))

            time.sleep(0.5)

            # Handle shipping discount
            if shipping_discount:
                driver.execute_script("""
                    var labels = document.querySelectorAll('label, div, span');
                    for (var i = 0; i < labels.length; i++) {
                        var text = labels[i].textContent.toLowerCase();
                        if (text.includes('shipping') && text.includes('discount')) {
                            var input = labels[i].querySelector('input[type="checkbox"]');
                            if (input && !input.checked) labels[i].click();
                            break;
                        }
                    }
                """)

            # Submit
            time.sleep(0.5)
            driver.execute_script("""
                var btns = document.querySelectorAll('button');
                for (var i = 0; i < btns.length; i++) {
                    var text = btns[i].textContent.toLowerCase();
                    if (text.includes('submit') || text.includes('apply') || text.includes('send')) {
                        btns[i].click();
                        return true;
                    }
                }
                return false;
            """)

            time.sleep(2)
            return {"success": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def calculate_offer_price(self, original_price, discount_percent, min_price):
        discounted = original_price * (1 - discount_percent / 100)
        discounted = math.floor(discounted)
        return max(discounted, min_price)
