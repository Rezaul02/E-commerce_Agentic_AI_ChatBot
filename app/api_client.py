"""
Dummy API er shathe kotha bolar client layer.
Tool gulo direct httpx call na kore ei class ta use korbe --
fole pore real API te switch korte shudhu ei file bodlalei hobe.
"""

from typing import Any, Dict, Optional

import httpx

from app.config import settings


class APIError(Exception):
    """Business-level error (404 / 409 etc.) -- tool eta ke friendly message e convert korbe."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class EcomAPIClient:
    def __init__(self, base_url: Optional[str] = None, timeout: float = 15.0):
        self.base_url = (base_url or settings.DUMMY_API_URL).rstrip("/")
        self._client = httpx.Client(timeout=timeout)

    # ---------- low level ----------
    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            resp = self._client.request(method, url, **kwargs)
        except httpx.RequestError as e:
            raise APIError(f"Backend service e connect kora jacche na: {e}", 503)

        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            if isinstance(detail, list):  # pydantic validation error
                detail = "; ".join(str(d.get("msg", d)) for d in detail)
            raise APIError(str(detail), resp.status_code)

        return resp.json()

    def _get(self, path: str, params: Optional[dict] = None) -> Dict[str, Any]:
        params = {k: v for k, v in (params or {}).items() if v is not None}
        return self._request("GET", path, params=params)

    def _post(self, path: str, json: Optional[dict] = None) -> Dict[str, Any]:
        return self._request("POST", path, json=json)

    # ---------- products ----------
    def search_products(self, **params) -> Dict[str, Any]:
        return self._get("/products", params)

    def get_product(self, product_id: str) -> Dict[str, Any]:
        return self._get(f"/products/{product_id}")

    def check_stock(self, product_id: str) -> Dict[str, Any]:
        return self._get(f"/stock/{product_id}")

    # ---------- orders ----------
    def get_order(self, order_id: str) -> Dict[str, Any]:
        return self._get(f"/orders/{order_id}")

    def list_user_orders(self, user_id: str, limit: int = 5) -> Dict[str, Any]:
        return self._get(f"/users/{user_id}/orders", {"limit": limit})

    # ---------- returns ----------
    def return_eligibility(self, order_id: str) -> Dict[str, Any]:
        return self._get(f"/returns/eligibility/{order_id}")

    def create_return(self, **payload) -> Dict[str, Any]:
        return self._post("/returns", json=payload)

    def get_return(self, rma_id: str) -> Dict[str, Any]:
        return self._get(f"/returns/{rma_id}")

    # ---------- misc ----------
    def recommend(self, **params) -> Dict[str, Any]:
        return self._get("/recommendations", params)

    def get_user(self, user_id: str) -> Dict[str, Any]:
        return self._get(f"/users/{user_id}")

    def get_policy(self, topic: str) -> Dict[str, Any]:
        return self._get(f"/policy/{topic}")


api = EcomAPIClient()
