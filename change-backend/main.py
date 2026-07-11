from fastapi import Depends, FastAPI
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

app = FastAPI()

@app.get("/health/db")
async def health_db(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("Select version()"))
    return {"result": result.scalar()}