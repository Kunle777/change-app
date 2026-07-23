import os
import jwt as pyjwt
from slowapi import Limiter
from slowapi.util import get_remote_address
from dotenv import load_dotenv

load_dotenv()

limiter = Limiter(key_func=get_remote_address)

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")


def decode_supabase_token(token: str) -> dict:
    payload = pyjwt.decode(
        token,
        SUPABASE_JWT_SECRET,
        algorithms=["HS256"],
        audience="authenticated",
    )
    return payload
