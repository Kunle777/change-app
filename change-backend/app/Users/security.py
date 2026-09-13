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

def hash_secret(raw: str) -> str:
    return pwd_context.hash(raw)  # same pwd_context already used for... actually wait, Supabase owns passwords now

def verify_secret(raw: str, hashed: str) -> bool:
    return pwd_context.verify(raw, hashed)



