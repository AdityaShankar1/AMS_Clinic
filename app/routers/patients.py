from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import UserRole, staff_only, doctor_only
from app.schemas.patient import PatientCreate, PatientUpdate, PatientOut
from app.repositories import patient_repository as repo

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=PatientOut, status_code=201)
async def create_patient(
    payload: PatientCreate,
    db: AsyncSession = Depends(get_db),
    _role: UserRole = Depends(staff_only),
):
    """Register a new patient. Doctor or Receptionist only."""
    try:
        return await repo.create_patient(db, **payload.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not create patient: {exc}")


@router.get("", response_model=list[PatientOut])
async def search_patients(
    q: str | None = None,
    limit: int = 500,
    db: AsyncSession = Depends(get_db),
    _role: UserRole = Depends(staff_only),
):
    """Search / list patients. Doctor or Receptionist only."""
    try:
        return await repo.search_patients(db, query=q)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not fetch patients: {exc}")


@router.get("/{patient_id}", response_model=PatientOut)
async def get_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    _role: UserRole = Depends(staff_only),
):
    """Get a patient by ID. Doctor or Receptionist only."""
    patient = await repo.get_patient_by_id(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.put("/{patient_id}", response_model=PatientOut)
async def update_patient(
    patient_id: int,
    payload: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    _role: UserRole = Depends(staff_only),
):
    """Update patient details. Doctor or Receptionist only."""
    try:
        updated = await repo.update_patient(db, patient_id, **payload.model_dump(exclude_unset=True))
        if updated is None:
            raise HTTPException(status_code=404, detail="Patient not found")
        return updated
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Update failed: {exc}")


@router.delete("/{patient_id}", response_model=PatientOut)
async def deactivate_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    _role: UserRole = Depends(doctor_only),
):
    """
    Soft-deactivate a patient (sets consent_given=False).
    Doctor only — this is a clinically significant action.
    """
    try:
        updated = await repo.update_patient(db, patient_id, consent_given=False)
        if updated is None:
            raise HTTPException(status_code=404, detail="Patient not found")
        return updated
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Deactivation failed: {exc}")
