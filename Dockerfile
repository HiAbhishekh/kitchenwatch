FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir \
    "pydantic>=2.8" \
    "fastapi>=0.115" \
    "uvicorn>=0.30" \
    "python-multipart>=0.0.9" \
    "google-cloud-firestore>=2.16" \
    "google-genai>=1.0" \
    "google-api-python-client>=2.150" \
    "google-auth>=2.35" \
    "google-auth-httplib2>=0.2" \
    && pip install --no-cache-dir --no-deps .

ENV PORT=8080
ENV PYTHONUNBUFFERED=1
CMD exec uvicorn kitchenwatch.app:app --host 0.0.0.0 --port ${PORT}
