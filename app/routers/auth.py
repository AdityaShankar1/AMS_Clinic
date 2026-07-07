from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token, hash_password, verify_password
from app.core.security import AuthSession, UserRole, doctor_only, resolve_session
from app.db.session import get_db
from app.repositories import user_repository as user_repo
from app.schemas.auth import AuthSessionOut, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Login with email + password → JWT token."""
    user = await user_repo.get_user_by_email(db, form.username)
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive.")
    token = create_access_token(
        user_id=user.user_id,
        role=user.role,
        patient_id=user.patient_id,
    )
    return TokenResponse(
        access_token=token,
        role=user.role,
        user_id=user.user_id,
        full_name=user.full_name,
    )


@router.get("/me", response_model=AuthSessionOut)
async def who_am_i(session: AuthSession = Depends(resolve_session)):
    return session


@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    session: AuthSession = Depends(resolve_session),
    db: AsyncSession = Depends(get_db),
):
    """Any authenticated user can change their own password."""
    if session.user_id == 0:
        raise HTTPException(
            status_code=400,
            detail="Password change requires JWT login, not a legacy key."
        )
    user = await user_repo.get_user_by_id(db, session.user_id)
    if user is None or not verify_password(current_password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")
    if len(new_password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters.")
    await user_repo.update_password(db, session.user_id, hash_password(new_password))
    return {"message": "Password updated successfully."}
