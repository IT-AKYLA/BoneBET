# BoneBET Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir "fastapi>=0.115.0" "uvicorn[standard]>=0.30.0" \
    "pydantic>=2.9.0" "pydantic-settings>=2.5.0" "sqlalchemy>=2.0.35" \
    "aiosqlite>=0.20.0" "alembic>=1.13.0" "redis>=5.0.0" "httpx>=0.27.0" \
    "python-dotenv>=1.0.0" "apscheduler>=3.10.0" "openai>=1.45.0" \
    "tenacity>=9.0.0" "structlog>=24.4.0" "numpy>=2.0.0" "scipy>=1.14.0" \
    "rapidfuzz>=3.0.0"

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY migrations/ ./migrations/
COPY alembic.ini .
COPY run_api.py .

# Create directory for SQLite database
RUN mkdir -p /app/data
ENV DATABASE_URL=sqlite+aiosqlite:////app/data/bonebet.db

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "run_api.py"]