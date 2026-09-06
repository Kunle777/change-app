from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.users.models import User
from app.users.dependencies import get_current_user
from app.savings.service import ensure_user_has_dva

router = APIRouter(prefix="/savings", tags=["Savings"])

# quick manual test — run once via Postman or a throwaway script
# POST /api/savings/test-dva  (temporary route, remove after confirming)

@router.post("/test-dva")
async def test_dva(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await ensure_user_has_dva(current_user, db)
    return result