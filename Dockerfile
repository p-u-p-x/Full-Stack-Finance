FROM python:3.11-slim
WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y ffmpeg curl && rm -rf /var/lib/apt/lists/*

# Install Python packages for backend AND frontend
COPY backend/requirements.txt backend-requirements.txt
COPY frontend/requirements.txt frontend-requirements.txt
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu || pip install --no-cache-dir torch
RUN pip install --no-cache-dir -r backend-requirements.txt
RUN pip install --no-cache-dir -r frontend-requirements.txt

# SpaCy model
RUN python -m spacy download en_core_web_sm

# Copy the whole project
COPY . .

# Startup script
COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

# Expose ports (Streamlit 8501, Backend 8000 – only 8501 will be public)
EXPOSE 8501 8000

CMD ["/usr/local/bin/start.sh"]
