from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.visit_record import VisitRecordCreate, VisitRecordUpdate, VisitRecordOut
from app.repositories import visit_record_repository as repo

router = APIRouter(prefix="/visit-records", tags=["visit_records"])


@router.post("", response_model=VisitRecordOut, status_code=201)
async def create_visit_record(payload: VisitRecordCreate, db: AsyncSession = Depends(get_db)):
    return await repo.create_visit_record(db, **payload.model_dump())


@router.get("/{visit_record_id}", response_model=VisitRecordOut)
async def get_visit_record(visit_record_id: int, db: AsyncSession = Depends(get_db)):
    record = await repo.get_visit_record_by_id(db, visit_record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Visit record not found")
    return record


@router.get("/patient/{patient_id}", response_model=list[VisitRecordOut])
async def get_patient_history(patient_id: int, db: AsyncSession = Depends(get_db)):
    return await repo.list_visit_records_for_patient(db, patient_id)


@router.put("/{visit_record_id}", response_model=VisitRecordOut)
async def update_visit_record(visit_record_id: int, payload: VisitRecordUpdate, db: AsyncSession = Depends(get_db)):
    updated = await repo.update_visit_record(db, visit_record_id, **payload.model_dump(exclude_unset=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="Visit record not found")
    return updated
