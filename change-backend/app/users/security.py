import os

import jwt as pyjwt
from dotenv import load_dotenv
from jwt import PyJWKClient
from slowapi import Limiter
from slowapi.util import get_remote_address
from passlib.context import CryptContext


load_dotenv()

limiter = Limiter(key_func=get_remote_address)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://jcflmvahszgqikxtnuwn.supabase.co").rstrip("/")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
_jwks_client = PyJWKClient(JWKS_URL)


def decode_supabase_token(token: str) -> dict:
    header = pyjwt.get_unverified_header(token)
    token_algorithm = header.get("alg")

    if token_algorithm not in {"ES256", "HS256"}:
        raise ValueError(f"Unsupported Supabase token algorithm: {token_algorithm}")

    if token_algorithm == "HS256":
        if not SUPABASE_JWT_SECRET:
            raise RuntimeError("SUPABASE_JWT_SECRET is required for HS256 token verification")
        key = SUPABASE_JWT_SECRET
    else:
        key = _jwks_client.get_signing_key_from_jwt(token).key

    payload = pyjwt.decode(
        token,
        key,
        algorithms=[token_algorithm],
        audience="authenticated",
    )
    return payload

def hash_secret(raw: str) -> str:
    return pwd_context.hash(raw)  # same pwd_context already used for... actually wait, Supabase owns passwords now

def verify_secret(raw: str, hashed: str) -> bool:
    return pwd_context.verify(raw, hashed)



