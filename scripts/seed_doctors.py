"""One-off script to seed real clinic doctors. Run once."""
import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()
RAW_URL = os.getenv("DATABASE_URL").replace("postgresql+asyncpg://", "postgresql://")

async def seed():
    conn = await asyncpg.connect(RAW_URL)
    
    # Clean up test doctors that have no appointments linked to them
    # to avoid cluttering the database.
    try:
        # Delete doctors whose name starts with 'Dr. Test' or 'Booking Test' and have no appointments
        deleted = await conn.execute(
            """
            DELETE FROM doctors 
            WHERE (full_name LIKE 'Dr. Test%' OR full_name LIKE 'Booking Test%')
              AND doctor_id NOT IN (SELECT DISTINCT doctor_id FROM appointments);
            """
        )
        print(f"Cleaned up test doctors: {deleted}")
    except Exception as e:
        print(f"Non-critical cleanup warning: {e}")

    # Check if real doctors already exist
    exists_rashmi = await conn.fetchval(
        "SELECT EXISTS(SELECT 1 FROM doctors WHERE full_name = $1)",
        "Dr. Rashmi N"
    )
    exists_shrinidhi = await conn.fetchval(
        "SELECT EXISTS(SELECT 1 FROM doctors WHERE full_name = $1)",
        "Dr. Shrinidhi M S"
    )

    if not exists_rashmi:
        await conn.execute(
            "INSERT INTO doctors (full_name, specialty) VALUES ($1, $2)",
            "Dr. Rashmi N", "Orthodontics"
        )
        print("Seeded Dr. Rashmi N")
    else:
        print("Dr. Rashmi N already seeded")

    if not exists_shrinidhi:
        await conn.execute(
            "INSERT INTO doctors (full_name, specialty) VALUES ($1, $2)",
            "Dr. Shrinidhi M S", "Periodontics"
        )
        print("Seeded Dr. Shrinidhi M S")
    else:
        print("Dr. Shrinidhi M S already seeded")

    # List all doctors currently in the system
    rows = await conn.fetch("SELECT * FROM doctors")
    print("\nCurrent Doctors in Database:")
    for r in rows:
        print(dict(r))

    await conn.close()

if __name__ == "__main__":
    asyncio.run(seed())
