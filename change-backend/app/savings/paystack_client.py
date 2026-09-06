# app/savings/paystack_client.py
import os
import httpx

PAYSTACK_SECRET_KEY = os.environ["PAYSTACK_SECRET_KEY"]
PAYSTACK_BASE_URL = "https://api.paystack.co"

HEADERS = {
    "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
    "Content-Type": "application/json",
}


class PaystackError(Exception):
    """Raised when Paystack returns status: false or a non-2xx response."""
    def __init__(self, message: str, response_body: dict):
        self.response_body = response_body
        super().__init__(message)


async def paystack_request(method: str, path: str, json: dict | None = None) -> dict:
    """
    Single shared entrypoint for every Paystack API call, present and future.
    Centralizing this now means auth headers, base URL, and error handling
    are correct in exactly one place — not re-copied into every function
    that ever needs to talk to Paystack (customer creation, DVA, transfers,
    subscriptions in Phase 8, all reuse this).
    """
    async with httpx.AsyncClient(base_url=PAYSTACK_BASE_URL, headers=HEADERS, timeout=15.0) as client:
        response = await client.request(method, path, json=json)

    body = response.json()

    if not response.is_success or not body.get("status"):
        raise PaystackError(
            message=body.get("message", "Unknown Paystack error"),
            response_body=body,
        )

    return body["data"]