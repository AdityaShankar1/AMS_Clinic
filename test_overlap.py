import asyncio
import asyncpg

async def test():
    conn = await asyncpg.connect(
        'postgresql://postgres:AdityaShankar7@db.xnvvqhuivqentenfdunl.supabase.co:5432/postgres'
    )

    doctor_id = await conn.fetchval(
        "INSERT INTO doctors (full_name, specialty) VALUES ('Dr. Test', 'ortho') RETURNING doctor_id"
    )
    patient_id = await conn.fetchval(
        "INSERT INTO patients (full_name, date_of_birth, sex, phone_number) VALUES ('Test Patient', '1990-01-01', 'M', '9999999999') RETURNING patient_id"
    )

    await conn.execute(
        "INSERT INTO appointments (patient_id, doctor_id, scheduled_start) VALUES ($1, $2, '2026-07-01 17:00:00+05:30')",
        patient_id, doctor_id
    )
    print('First appointment inserted OK')

    try:
        await conn.execute(
            "INSERT INTO appointments (patient_id, doctor_id, scheduled_start) VALUES ($1, $2, '2026-07-01 17:10:00+05:30')",
            patient_id, doctor_id
        )
        print('ERROR: second overlapping appointment was incorrectly allowed')
    except Exception as e:
        print('Correctly rejected overlapping appointment:', type(e).__name__, '-', str(e)[:200])

    await conn.execute('DELETE FROM appointments WHERE doctor_id = $1', doctor_id)
    await conn.execute('DELETE FROM doctors WHERE doctor_id = $1', doctor_id)
    await conn.execute('DELETE FROM patients WHERE patient_id = $1', patient_id)
    await conn.close()
    print('Cleanup done')

asyncio.run(test())
