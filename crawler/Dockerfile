FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml /app/
COPY app /app/app

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -e .

CMD ["python", "-m", "app.cloud_job"]
