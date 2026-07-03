from fastapi import APIRouter, Depends
from app.core.security import AuthSession, resolve_session
from app.schemas.auth import AuthSessionOut

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/me", response_model=AuthSessionOut)
async def who_am_i(session: AuthSession = Depends(resolve_session)):
    return session
