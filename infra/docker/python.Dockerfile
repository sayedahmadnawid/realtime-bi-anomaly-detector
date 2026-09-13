FROM python:3.12-slim

WORKDIR /app

# System deps needed to build psycopg2 (if using the non-binary package later)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Source is bind-mounted in docker-compose for local dev (see volumes: ..:/app),
# so this COPY mainly matters for a standalone/prod image build.
COPY . .

CMD ["python", "-m", "ingestion.ingest"]
