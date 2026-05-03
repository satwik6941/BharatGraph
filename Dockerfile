FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY query.py api.py ./

# Bake the Vyakyarth model into the image at build time
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('krutrim-ai-labs/Vyakyarth')"

EXPOSE 8080
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]