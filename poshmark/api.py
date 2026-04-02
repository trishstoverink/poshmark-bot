import math
from database import log_activity

API_BASE = "https://api.poshmark.com/api"
WEB_BASE = "https://poshmark.com"


class PoshmarkAPI:
    def __init__(self, auth):
        self.auth = auth

    def _get(self, path, params=None, use_api=True):
        base = API_BASE if use_api else WEB_BASE
        resp = self.auth.get_session().get(
            f"{base}{path}", params=params, timeout=30
        )
        resp.raise_for_status()
        return resp.json()

    def _post(self, path, json_data=None, use_api=True):
        base = API_BASE if use_api else WEB_BASE
        resp = self.auth.get_session().post(
            f"{base}{path}", json=json_data, timeout=30
        )
        resp.raise_for_status()
        return resp.json()

    def get_my_listings(self, max_pages=10):
        """Fetch all active listings for the logged-in user."""
        username = self.auth.get_username()
        if not username:
            return []

        listings = []
        for page in range(1, max_pages + 1):
            try:
                data = self._get(
                    f"/api/v1/users/{username}/posts",
                    params={
                        "filter": "available",
                        "page": page,
                        "per_page": 48,
                    },
                )
                posts = data.get("data", [])
                if not posts:
                    break
                listings.extend(posts)
            except Exception as e:
                log_activity("fetch_listings", f"Error page {page}: {e}", "error")
                break

        return listings

    def share_listing(self, listing_id):
        """Share a listing to followers."""
        try:
            result = self._post(f"/api/v1/posts/{listing_id}/share")
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_listing_likes(self, listing_id):
        """Get users who liked a listing."""
        try:
            data = self._get(f"/api/v1/posts/{listing_id}/likers")
            return data.get("data", [])
        except Exception:
            return []

    def send_offer(self, listing_id, price, shipping_discount=True):
        """Send an offer to likers of a listing."""
        try:
            offer_data = {
                "offer": {
                    "listing_id": listing_id,
                    "offer_price": price,
                    "shipping_discount": shipping_discount,
                }
            }
            result = self._post("/api/v1/offers", json_data=offer_data)
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def calculate_offer_price(self, original_price, discount_percent, min_price):
        """Calculate offer price based on discount %, respecting minimum."""
        discounted = original_price * (1 - discount_percent / 100)
        discounted = math.floor(discounted)  # Round down to whole dollar
        return max(discounted, min_price)
