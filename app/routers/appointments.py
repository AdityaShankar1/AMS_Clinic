from fastapi import APIRouter

router = APIRouter(
    prefix="/appointments",
    tags=["appointments"]
)

@router.get("")
async def get_appointments():
    return [
        {
            "id": 1,
            "patient_name": "Test Patient",
            "time": "10:00 AM",
            "status": "scheduled"
        }
    ]
