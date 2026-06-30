from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.patient import PatientCreate, PatientUpdate, PatientOut
from app.repositories import patient_repository as repo

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=PatientOut, status_code=201)
async def create_patient(payload: PatientCreate, db: AsyncSession = Depends(get_db)):
    return await repo.create_patient(db, **payload.model_dump())


@router.get("", response_model=list[PatientOut])
async def search_patients(q: str | None = None, db: AsyncSession = Depends(get_db)):
    return await repo.search_patients(db, query=q)


@router.get("/{patient_id}", response_model=PatientOut)
async def get_patient(patient_id: int, db: AsyncSession = Depends(get_db)):
    patient = await repo.get_patient_by_id(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.put("/{patient_id}", response_model=PatientOut)
async def update_patient(patient_id: int, payload: PatientUpdate, db: AsyncSession = Depends(get_db)):
    updated = await repo.update_patient(db, patient_id, **payload.model_dump(exclude_unset=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return updated


@router.delete("/{patient_id}", response_model=PatientOut)
async def deactivate_patient(patient_id: int, db: AsyncSession = Depends(get_db)):
    """Soft deactivate only — no hard delete, per project design rules."""
    updated = await repo.update_patient(db, patient_id, consent_given=False)
    if updated is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return updated
