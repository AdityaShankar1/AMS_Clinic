from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import UserRole, staff_only, doctor_only
from app.schemas.visit_record import VisitRecordCreate, VisitRecordUpdate, VisitRecordOut
from app.repositories import visit_record_repository as repo

router = APIRouter(prefix="/visit-records", tags=["visit_records"])


@router.post("", response_model=VisitRecordOut, status_code=201)
async def create_visit_record(
    payload: VisitRecordCreate,
    db: AsyncSession = Depends(get_db),
    _role: UserRole = Depends(doctor_only),
):
    """Create a visit/clinical record. Doctor only."""
    try:
        return await repo.create_visit_record(db, **payload.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not create visit record: {exc}")


@router.get("/{visit_record_id}", response_model=VisitRecordOut)
async def get_visit_record(
    visit_record_id: int,
    db: AsyncSession = Depends(get_db),
    _role: UserRole = Depends(staff_only),
):
    """Get a visit record by ID. Doctor or Receptionist only."""
    record = await repo.get_visit_record_by_id(db, visit_record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Visit record not found")
    return record


@router.get("/patient/{patient_id}", response_model=list[VisitRecordOut])
async def get_patient_history(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    _role: UserRole = Depends(staff_only),
):
    """Get all visit records for a patient. Doctor or Receptionist only."""
    try:
        return await repo.list_visit_records_for_patient(db, patient_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not fetch visit records: {exc}")


@router.put("/{visit_record_id}", response_model=VisitRecordOut)
async def update_visit_record(
    visit_record_id: int,
    payload: VisitRecordUpdate,
    db: AsyncSession = Depends(get_db),
    _role: UserRole = Depends(doctor_only),
):
    """Update a visit record. Doctor only."""
    try:
        updated = await repo.update_visit_record(
            db, visit_record_id, **payload.model_dump(exclude_unset=True)
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="Visit record not found")
        return updated
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Update failed: {exc}")
