
from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text



from app.db.session import engine

from app.routers import auth, patients, doctors, appointments, visit_records, gui



app = FastAPI(title="Clinic AMS")



origins = [

    "http://localhost:5173",

    "https://ams-clinic.vercel.app",

    "https://ams-clinic-frontend.vercel.app"

]



app.add_middleware(

    CORSMiddleware,

    allow_origins=origins,

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

)



@app.get("/health")

async def health_check():

    try:

        async with engine.connect() as conn:

            result = await conn.execute(text("SELECT 1"))

            await conn.commit()

        return {"status": "ok", "db": "connected"}

    except Exception as exc:

        return {"status": "error", "db": str(exc)}



# Mount directly using the exact instances exported

app.include_router(gui.router)

app.include_router(auth.router)

app.include_router(appointments.router)

app.include_router(patients.router)

app.include_router(doctors.router)

app.include_router(visit_records.router)

