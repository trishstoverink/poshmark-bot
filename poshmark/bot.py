import time
import random
import threading
from database import get_setting, log_activity, has_seen_like, mark_like_seen


class PoshmarkBot:
    def __init__(self, api):
        self.api = api
        self._share_running = False
        self._offer_running = False
        self._share_thread = None
        self._offer_thread = None
        self._stop_share = threading.Event()
        self._stop_offer = threading.Event()
        self.stats = {
            "shares_today": 0,
            "offers_today": 0,
            "last_share_time": None,
            "last_offer_time": None,
            "share_cycle_active": False,
        }

    # ── Sharing ──────────────────────────────────────────────

    def start_sharing(self):
        if self._share_running:
            return
        self._share_running = True
        self._stop_share.clear()
        self._share_thread = threading.Thread(target=self._share_loop, daemon=True)
        self._share_thread.start()
        log_activity("share_start", "Auto-share started")

    def stop_sharing(self):
        self._share_running = False
        self._stop_share.set()
        log_activity("share_stop", "Auto-share stopped")

    def _share_loop(self):
        while not self._stop_share.is_set():
            if not get_setting("share_enabled"):
                self._stop_share.wait(10)
                continue

            self._run_share_cycle()

            interval = get_setting("share_interval_minutes") * 60
            self._stop_share.wait(interval)

    def _run_share_cycle(self):
        self.stats["share_cycle_active"] = True
        listings = self.api.get_my_listings()

        if not listings:
            log_activity("share_cycle", "No listings found", "warning")
            self.stats["share_cycle_active"] = False
            return

        order = get_setting("share_order")
        if order == "random":
            random.shuffle(listings)
        elif order == "oldest_first":
            listings.reverse()
        # "newest_first" is default order from API

        delay_min = get_setting("share_delay_min")
        delay_max = get_setting("share_delay_max")

        shared = 0
        for listing in listings:
            if self._stop_share.is_set():
                break

            listing_id = listing.get("id")
            title = listing.get("title", "Unknown")

            result = self.api.share_listing(listing_id)
            if result["success"]:
                shared += 1
                self.stats["shares_today"] += 1
                self.stats["last_share_time"] = time.strftime("%H:%M:%S")
                log_activity("share", f"Shared: {title}")
            else:
                log_activity("share", f"Failed: {title} - {result['error']}", "error")

            # Random delay between shares
            delay = random.uniform(delay_min, delay_max)
            self._stop_share.wait(delay)

        log_activity("share_cycle", f"Cycle complete: shared {shared}/{len(listings)} listings")
        self.stats["share_cycle_active"] = False

    # ── Offers ───────────────────────────────────────────────

    def start_offers(self):
        if self._offer_running:
            return
        self._offer_running = True
        self._stop_offer.clear()
        self._offer_thread = threading.Thread(target=self._offer_loop, daemon=True)
        self._offer_thread.start()
        log_activity("offer_start", "Auto-offers started")

    def stop_offers(self):
        self._offer_running = False
        self._stop_offer.set()
        log_activity("offer_stop", "Auto-offers stopped")

    def _offer_loop(self):
        while not self._stop_offer.is_set():
            if not get_setting("offer_enabled"):
                self._stop_offer.wait(10)
                continue

            self._check_likes_and_offer()

            interval = get_setting("offer_check_interval_minutes") * 60
            self._stop_offer.wait(interval)

    def _check_likes_and_offer(self):
        listings = self.api.get_my_listings()
        discount = get_setting("offer_discount_percent")
        min_price = get_setting("offer_min_price")
        shipping_discount = get_setting("offer_shipping_discount")

        for listing in listings:
            if self._stop_offer.is_set():
                break

            listing_id = listing.get("id")
            title = listing.get("title", "Unknown")
            original_price = listing.get("price", 0)

            if isinstance(original_price, str):
                original_price = float(original_price.replace("$", "").replace(",", ""))

            likers = self.api.get_listing_likes(listing_id)

            new_likers = []
            for liker in likers:
                user_id = liker.get("id", "")
                if not has_seen_like(listing_id, user_id):
                    new_likers.append(liker)
                    mark_like_seen(listing_id, user_id)

            if new_likers:
                offer_price = self.api.calculate_offer_price(
                    original_price, discount, min_price
                )
                result = self.api.send_offer(
                    listing_id, offer_price, shipping_discount
                )
                if result["success"]:
                    self.stats["offers_today"] += 1
                    self.stats["last_offer_time"] = time.strftime("%H:%M:%S")
                    log_activity(
                        "offer",
                        f"Sent ${offer_price} offer on '{title}' "
                        f"({len(new_likers)} new liker(s))",
                    )
                else:
                    log_activity(
                        "offer",
                        f"Failed offer on '{title}': {result['error']}",
                        "error",
                    )

            # Small delay between checking listings
            time.sleep(random.uniform(1, 3))

    # ── Status ───────────────────────────────────────────────

    def get_status(self):
        return {
            "share_running": self._share_running,
            "offer_running": self._offer_running,
            **self.stats,
        }

    def reset_daily_stats(self):
        self.stats["shares_today"] = 0
        self.stats["offers_today"] = 0
