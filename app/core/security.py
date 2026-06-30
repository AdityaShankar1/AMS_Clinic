"""
Minimal P1 access gate. NOT real auth — that's Phase 2 (role-based JWT via
fastapi-users). This exists only so the app is not wide open on the public
internet the moment it's deployed. Single shared password via header.
"""
from fastapi import Header, HTTPException
from app.core.config import settings


async def require_staff_key(x_staff_key: str = Header(...)):
    if x_staff_key != settings.STAFF_ACCESS_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing staff key")
