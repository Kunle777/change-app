import hmac
import hashlib
import os

PAYSTACK_SECRET_KEY = os.environ["PAYSTACK_SECRET_KEY"]


def verify_paystack_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """
    Paystack signs every webhook with HMAC-SHA512 of the raw request body,
    using your secret key. This MUST run against the raw bytes, before any
    JSON parsing — parsing then re-serializing can change whitespace/key
    order and silently invalidate a signature that was actually genuine.
    """
    if not signature_header:
        return False

    computed = hmac.new(
        PAYSTACK_SECRET_KEY.encode("utf-8"),
        raw_body,
        hashlib.sha512,
    ).hexdigest()

    return hmac.compare_digest(computed, signature_header)