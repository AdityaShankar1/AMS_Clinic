# Production image for Clinic AMS FastAPI backend
# Uses Python 3.12 — 3.14 has unresolved macOS/uvicorn startup issues (see DAILY_LOG.md)
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (separate layer — cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run as non-root user for basic container security
RUN useradd -m -u 1000 clinic && chown -R clinic:clinic /app
USER clinic

EXPOSE 8000

# DATABASE_URL and role keys must be passed as environment variables at runtime
# Never bake secrets into the image
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
