import os

import jwt as pyjwt
from dotenv import load_dotenv
from jwt import PyJWKClient
from slowapi import Limiter
from slowapi.util import get_remote_address

load_dotenv()

limiter = Limiter(key_func=get_remote_address)

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://jcflmvahszgqikxtnuwn.supabase.co").rstrip("/")
JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
_jwks_client = PyJWKClient(JWKS_URL)


def decode_supabase_token(token: str) -> dict:
    signing_key = _jwks_client.get_signing_key_from_jwt(token)
    payload = pyjwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256"],
        audience="authenticated",
    )
    return payload
