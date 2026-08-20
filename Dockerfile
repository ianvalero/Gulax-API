FROM python:3.11-slim

WORKDIR /app

ARG HTTP_PROXY
ARG HTTPS_PROXY

COPY requirements.txt .

RUN HTTP_PROXY=$HTTP_PROXY \
    HTTPS_PROXY=$HTTPS_PROXY \
    http_proxy=$HTTP_PROXY \
    https_proxy=$HTTPS_PROXY \
    pip install --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini .

EXPOSE 9000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000", "--workers", "4", "--loop", "uvloop"]