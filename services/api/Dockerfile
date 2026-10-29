FROM python:3.13.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
COPY artifacts ./artifacts
COPY data ./data
RUN pip install --no-cache-dir \
      --extra-index-url https://download.pytorch.org/whl/cpu \
      "torch==2.14.1+cpu" \
    && pip install --no-cache-dir .

USER 65532:65532
EXPOSE 8000
CMD ["uvicorn", "smart_ecommerce_api.main:app", "--host", "0.0.0.0", "--port", "8000"]

