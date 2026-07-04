"""
Structured request logging — every request gets a unique ID that appears
in all log lines for that request. This makes log correlation possible
without a full SIEM setup, and is the same principle behind what Wazuh
ingests from application logs.

In a production SOC context, these logs would be shipped to a SIEM
(Wazuh, Splunk, etc.) for alerting on anomalous patterns — e.g.
repeated 401s from the same IP (brute force), bulk patient record
access (data exfiltration attempt), or repeated bookings and cancellations
(appointment manipulation).
"""
import uuid
import time
import logging
from fastapi import Request

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s'
)
logger = logging.getLogger("clinic_ams")


async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()

    logger.info(
        f"[{request_id}] {request.method} {request.url.path} "
        f"from {request.client.host if request.client else 'unknown'}"
    )

    response = await call_next(request)
    duration_ms = round((time.time() - start) * 1000)

    logger.info(
        f"[{request_id}] → {response.status_code} in {duration_ms}ms"
    )

    response.headers["X-Request-ID"] = request_id
    return response
