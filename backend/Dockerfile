FROM python:3.11-slim
WORKDIR /app

# All model caches (huggingface, torch, sentence-transformers, whisper)
# live under /root/.cache — we mount that as a volume in docker-compose
# so models only download once, not on every restart.
ENV HF_HOME=/root/.cache/huggingface
ENV TRANSFORMERS_CACHE=/root/.cache/huggingface
ENV XDG_CACHE_HOME=/root/.cache
# Make sure no leftover regional mirror env var breaks Hub access.
ENV HF_ENDPOINT=https://huggingface.co

COPY requirements.txt .

RUN apt-get update && apt-get install -y ffmpeg curl && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu || pip install --no-cache-dir torch

RUN pip install --no-cache-dir --default-timeout=300 --retries 5 -r requirements.txt

RUN python -m spacy download en_core_web_sm

# Models are loaded lazily at runtime (see nlp.py / main.py), not baked
# in here — that keeps builds fast and startup instant.
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]