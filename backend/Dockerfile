FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

EXPOSE 8000

# Migrations run via `alembic upgrade head` in real deployments; AUTO_CREATE_TABLES
# is convenient for demos. Both are documented in the README.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
