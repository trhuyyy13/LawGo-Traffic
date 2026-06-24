FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    poppler-utils \
    libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

COPY src/ src/
COPY data/ data/

EXPOSE 8000

CMD ["uvicorn", "lawgo_traffic.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
