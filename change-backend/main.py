import logging
import re
import time
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.braindump.routers import router as braindump_router
from app.checkins.routers import router as checkins_router
from app.tasks.routers import router as tasks_router
from app.users.routers import router as users_router
from app.users.security import limiter
from app.ai.routers import router as ai_router
from app.wins.routers import router as wins_router
from app.memory.routers import router as memory_router
from app.ai.errors import AIRequestError


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("change_backend")
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router)
app.include_router(tasks_router)
app.include_router(braindump_router)
app.include_router(checkins_router)
app.include_router(ai_router)
app.include_router(wins_router)
app.include_router(memory_router)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    provided_id = request.headers.get("x-request-id", "")
    request_id = (
        provided_id
        if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", provided_id)
        else str(uuid.uuid4())
    )
    request.state.request_id = request_id
    start_time = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    logger.info(
        "%s %s -> %s in %.2fms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(AIRequestError)
async def ai_request_error_handler(request: Request, exc: AIRequestError):
    logger.error(
        "AI request failed category=%s request_id=%s",
        exc.info.code,
        exc.request_id,
    )
    return JSONResponse(
        status_code=exc.info.status_code,
        headers={"X-Request-ID": exc.request_id},
        content={
            "code": exc.info.code,
            "message": exc.info.message,
            "request_id": exc.request_id,
        },
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "Unhandled request failure request_id=%s error_type=%s",
        request_id,
        type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        headers={"X-Request-ID": request_id},
        content={
            "code": "backend_error",
            "message": "Elvyn couldn't complete that request. Please try again.",
            "request_id": request_id,
        },
    )



@app.get("/health/db")
async def health_db(db: AsyncSession = Depends(get_db)):
    await db.execute(select(1))
    return {"database": "ok"}
