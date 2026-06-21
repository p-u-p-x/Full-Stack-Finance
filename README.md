# 💵 Full Stack Finance — AI-Powered Earnings Intelligence Platform

![Python](https://img.shields.io/badge/Python-3.11-2E8B57) ![FastAPI](https://img.shields.io/badge/FastAPI-Backend-00695C) ![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-FF6F61) ![FinBERT](https://img.shields.io/badge/FinBERT-Sentiment-4B0082) ![Whisper](https://img.shields.io/badge/Whisper-Transcription-1E90FF) ![Docker](https://img.shields.io/badge/Docker-Containerized-004C99) ![HuggingFace](https://img.shields.io/badge/HuggingFace-Spaces-FFD700) ![LLaMA](https://img.shields.io/badge/Groq-LLaMA%203.1-32CD32)

---

A full-stack NLP platform that turns earnings call PDFs, transcripts, and audio recordings into structured intelligence — named entities, FinBERT sentiment, financial metrics, risk flags, fact-checked claims, and AI-generated analyst briefs — with a 10-page interactive Streamlit dashboard.

---

## 📌 Overview

Upload. Analyze. Understand Markets.

Full Stack Finance is a production-ready earnings intelligence platform that processes unstructured financial documents and audio through a multi-stage NLP pipeline. Users upload an earnings call PDF, TXT file, or audio recording (MP3/WAV/M4A) and immediately get: company and person entities via spaCy, sentence-level FinBERT sentiment with speaker breakdown, extracted financial metrics (revenue, EPS, gross margin, guidance, growth), risk language detection, claim verification against live Yahoo Finance data, RAG-powered Q&A backed by ChromaDB and Groq LLaMA 3.1, and a downloadable institutional analyst brief in PDF format.

---

## ✨ Features

- 🎙️ **Audio Transcription** — Upload earnings call audio; faster-whisper (Whisper base, int8 CPU) transcribes it and feeds it directly into the full NLP pipeline
- 🏢 **Named Entity Recognition** — spaCy extracts companies, organizations, and people from transcript text
- 📊 **FinBERT Sentiment Analysis** — ProsusAI/finbert classifies every sentence; results aggregated by document and by speaker
- 💰 **Financial Metric Extraction** — Regex pipeline pulls revenue, EPS, gross margin, net income, guidance, and YoY growth sentences
- 🛡️ **Claim Fact-Checking** — Cross-references monetary claims against live yfinance data; flags discrepancies over 15%
- 🔍 **RAG Question Answering** — LangChain + ChromaDB + Groq LLaMA 3.1; ask anything about the transcript in plain English
- 📝 **Analyst Brief Generation** — LLaMA 3.1 writes a structured institutional brief (Headline, Bull Case, Bear Case, Management Tone, Key Risks, Bottom Line)
- 📄 **PDF Export** — Download the analyst brief as a branded PDF via fpdf2
- ⚠️ **Risk Flag Detection** — Scans for 14 risk-associated keywords and surfaces the most salient risk sentences
- 🐳 **Dockerized, Models Pre-Downloaded** — All models baked into the image at build time; zero cold-start downloads

---

## 🏗️ Architecture

```text
                                           User (Browser)
                                                 |
                                                 v
                                 +-------------------------------+
                                 |   Streamlit Frontend          |  Port 7860 (HuggingFace) / 8501 (local)
                                 |   frontend/app.py             |  10-page dark dashboard, Plotly charts
                                 +---------------+---------------+
                                                 |  HTTP REST calls
                                                 v
                                 +-------------------------------+
                                 |   FastAPI Backend             |  Port 8000 (internal)
                                 |   backend/main.py             |
                                 |                               |
                                 |  /analyze   -> full pipeline  |
                                 |  /transcribe-> Whisper STT    |
                                 |  /ask       -> RAG Q&A        |
                                 |  /factcheck -> yfinance       |
                                 |  /generate-brief -> LLaMA     |
                                 |  /export-brief   -> PDF       |
                                 +---+--------+-------------+----+
                                     |        |             |
                                     v        v             v
                                   spaCy    FinBERT     ChromaDB
                                    NER    Sentiment     Vectors
                                     |        |             |
                                     v        v             v
                                 yfinance    Groq     faster-whisper
                                  (live)   LLaMA 3.1   (base int8)
```

On Hugging Face Spaces, both services run inside one Docker container.
`start.sh` launches uvicorn in the background, polls `localhost:8000` until healthy, then starts Streamlit on port 7860 in the foreground.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit, Plotly, streamlit-option-menu |
| Backend | FastAPI, Uvicorn |
| Sentiment | ProsusAI/FinBERT, PyTorch (CPU, batched) |
| NER | spaCy en_core_web_sm |
| Transcription | faster-whisper (Whisper base, int8 CPU) |
| Embeddings | all-MiniLM-L6-v2 via LangChain HuggingFaceEmbeddings |
| Vector Store | ChromaDB PersistentClient |
| LLM | Groq LLaMA 3.1-8b-instant |
| Fact-Checking | yfinance (live financial data) |
| PDF Export | fpdf2 |
| Containerization | Docker, Docker Compose |
| Deployment | Hugging Face Spaces |

---

## 📂 Project Structure

```text
Full-Stack-Finance/
|
+-- backend/
|   +-- main.py              # FastAPI app: all endpoints and ChromaDB logic
|   +-- nlp.py               # NLP module: FinBERT, spaCy, Whisper, RAG, metrics
|   +-- requirements.txt     # Backend Python dependencies
|
+-- frontend/
|   +-- app.py               # Streamlit 10-page dashboard with custom CSS/dark theme
|   +-- requirements.txt     # Frontend Python dependencies
|
+-- Dockerfile               # HuggingFace Spaces single-container build (models pre-downloaded)
+-- docker-compose.yml       # Local dev: backend + frontend + ChromaDB as separate services
+-- start.sh                 # Container entrypoint: backend first, health poll, then Streamlit
+-- railway.toml             # Railway deployment config
+-- .gitignore
+-- README.md
```

---

## ⚙️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/p-u-p-x/Full-Stack-Finance.git
cd Full-Stack-Finance
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your keys:

```env
GROQ_API_KEY=your_groq_api_key_here
OPENAI_API_KEY=your_openai_key_here     # optional fallback for Whisper
CORS_ORIGINS=*
CHROMA_PERSIST_DIR=/tmp/chroma_db
WHISPER_MODEL_SIZE=base
```

### 3. Run with Docker Compose (Recommended)

```bash
docker-compose up --build
```

| Service | URL |
|---|---|
| Streamlit Frontend | http://localhost:8501 |
| FastAPI Backend | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| ChromaDB | http://localhost:8002 |

> **Note:** The first `docker-compose up --build` will take several minutes as FinBERT, Whisper, and the sentence transformer download. Subsequent starts use the cached `model-cache` volume and are instant.

### 4. Run Manually (Without Docker)

```bash
# Backend
cd backend
pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn main:app --host 0.0.0.0 --port 8000 &

# Frontend (new terminal)
cd frontend
pip install -r requirements.txt
streamlit run app.py --server.port 8501
```

---

## 🧠 NLP Pipeline

When a file is uploaded and "Run Analysis" is clicked, the backend executes this pipeline:

```text
        Input (PDF / TXT / Audio)
               |
               v
        Text Extraction
        pypdf (PDF) | UTF-8 decode (TXT) | faster-whisper (Audio)
               |
               v
        spaCy NER  ->  Companies + People (first 3000 chars)
               |
               v
        FinBERT Sentiment  ->  Sentence scores, speaker averages
               |
               v
        Regex Financial Metrics  ->  Revenue, EPS, Gross Margin,
                                      Net Income, Guidance, Growth
               |
               v
        Extractive Summarization  ->  Top keyword-rich sentences
               |
               v
        Risk Flag Detection  ->  14 risk keyword scan
               |
               v
        LangChain Chunking (500 chars, 50 overlap)
               |
               v
        all-MiniLM-L6-v2 Embeddings  ->  ChromaDB storage
               |
               v
        Results returned to Streamlit
```

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Health check |
| `/health` | GET | Detailed model status (spaCy, FinBERT, Whisper, embeddings) |
| `/transcribe` | POST | Upload audio file; returns transcript text and detected language |
| `/analyze` | POST | Upload PDF or TXT; returns full NLP analysis JSON |
| `/ask` | POST | JSON `{question}`; returns RAG answer + source chunks |
| `/factcheck` | POST | JSON `{ticker, text}`; returns verified/flagged claims |
| `/generate-brief` | POST | JSON payload; returns LLaMA-generated analyst brief |
| `/export-brief` | POST | JSON `{brief, company}`; returns PDF binary for download |

---

## 🖥️ Dashboard Pages

| Page | What It Shows |
|---|---|
| Dashboard | File upload and analysis trigger |
| Audio | Whisper transcription upload for MP3/MP4/WAV/M4A |
| Companies | spaCy NER color-coded chips for companies and people |
| Sentiment | FinBERT time-series chart, donut chart, speaker breakdown bars |
| Metrics | Extracted revenue, EPS, gross margin, guidance, growth sentences |
| Fact Check | yfinance cross-reference with verified and flagged claim counts |
| Summary | Extractive key insight sentences |
| Risk Flags | Risk language sentences highlighted in amber |
| Brief | LLaMA analyst brief with PDF download button |
| Ask | RAG Q&A input with source chunk expander |

---

## Usage Flow

1. Open the app at the live URL or local address
2. Go to **Dashboard** and upload an earnings call PDF or TXT, or go to **Audio** for an MP3/WAV
3. Click **Run Analysis** and wait for the NLP pipeline to complete
4. Navigate through the sidebar pages to explore NER, Sentiment, Metrics, Risks, and Summary
5. Go to **Fact Check**, enter the company ticker (e.g. AAPL), and click Verify Claims
6. Go to **Brief**, enter the company name, and click Generate Brief for the LLaMA analyst report
7. Download the brief as a PDF using the Download button
8. Go to **Ask** and type any question about the transcript for a RAG-grounded answer

---

## 🚀 Deployment

Live on Hugging Face Spaces:

**https://p-u-p-x-full-stack-finance.hf.space**

The production `Dockerfile` pre-downloads all models at build time:

```dockerfile
RUN python -c "from transformers import AutoTokenizer, AutoModelForSequenceClassification; \
               AutoTokenizer.from_pretrained('ProsusAI/finbert'); \
               AutoModelForSequenceClassification.from_pretrained('ProsusAI/finbert')"

RUN python -c "from sentence_transformers import SentenceTransformer; \
               SentenceTransformer('all-MiniLM-L6-v2')"

RUN python -c "from faster_whisper import WhisperModel; \
               WhisperModel('base', device='cpu', compute_type='int8')"
```

This keeps container startup under 7 seconds with no network calls at runtime.

---

## 📬 Contact

- 💼 **GitHub:** [@p-u-p-x](https://github.com/p-u-p-x)
- 🌐 **Live App:** [https://p-u-p-x-full-stack-finance.hf.space](https://p-u-p-x-full-stack-finance.hf.space)
