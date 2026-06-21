import os
import time
import threading
import re as re_module

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
import numpy as np
from dotenv import load_dotenv
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from groq import Groq

from nlp import (extract_companies_and_people, analyze_sentiment, analyze_sentiment_batch,
                 summarize_text, extract_text_from_pdf, detect_risks,
                 analyze_by_speaker, extract_financial_metrics,
                 generate_analyst_brief, transcribe_audio, model_status, split_sentences)

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ------------------------------------------------------------
# Local ChromaDB (PersistentClient) – no separate container needed
# ------------------------------------------------------------
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

_chroma_client = None
_chroma_lock = threading.Lock()

def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        with _chroma_lock:
            if _chroma_client is None:
                _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    return _chroma_client


# ------------------------------------------------------------
# Lazy / retrying embeddings (unchanged from your version)
# ------------------------------------------------------------
_embeddings = None
_embeddings_status = None
_embeddings_lock = threading.Lock()

transcript_store = {}

def get_embeddings():
    global _embeddings, _embeddings_status
    if _embeddings_status is None:
        with _embeddings_lock:
            if _embeddings_status is None:
                try:
                    from langchain_huggingface import HuggingFaceEmbeddings
                    _embeddings = HuggingFaceEmbeddings(
                        model_name="all-MiniLM-L6-v2",
                        model_kwargs={"device": "cpu"},
                        encode_kwargs={"normalize_embeddings": True},
                    )
                    _embeddings_status = True
                except Exception as e:
                    print(f"[main] Could not load embeddings model: {e}")
                    _embeddings_status = False
    return _embeddings if _embeddings_status else None


app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/")
def health():
    return {"status": "backend running", "app": "Full Stack Finance"}


@app.get("/health")
def health_detail():
    """Lets the frontend show what's actually warmed up vs. still loading."""
    return {
        "status": "ok",
        **model_status(),
        "embeddings_loaded": _embeddings_status is True,
    }


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    import tempfile
    suffix = os.path.splitext(file.filename)[1] or ".mp3"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    try:
        text, language = transcribe_audio(tmp_path)
        return {"transcript": text, "language": language}
    except Exception as e:
        return {"error": str(e)}
    finally:
        os.unlink(tmp_path)


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    try:
        content = await file.read()
        if file.filename.endswith(".txt"):
            text = content.decode("utf-8", errors="ignore")
        else:
            text = extract_text_from_pdf(content)

        warning = None
        if len(text.strip()) < 200:
            warning = ("Very little text was extracted from this file. If it's a scanned "
                       "or image-based PDF, this tool can't read it without OCR — try a "
                       "text-based PDF or a .txt export instead.")

        ner = extract_companies_and_people(text[:3000])
        financial_metrics = extract_financial_metrics(text)
        speaker_sentiment = analyze_by_speaker(text)

        sentences = [s for s in split_sentences(text.replace('\n', ' ')) if len(s) > 40][:20]
        scored = analyze_sentiment_batch(sentences) if sentences else []
        scores = [s["score"] for s in scored]

        summary = summarize_text(text)
        risks = detect_risks(text)

        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = splitter.split_text(text)

        chunks_stored = 0
        try:
            client = get_chroma_client()
            collection = client.get_or_create_collection("transcripts")
            try:
                collection.delete(where={"source": "current"})
            except Exception:
                pass

            embeddings = get_embeddings()
            if chunks and embeddings is not None:
                chunk_embeddings = embeddings.embed_documents(chunks)
                collection.add(
                    documents=chunks,
                    embeddings=chunk_embeddings,
                    ids=[f"chunk_{i}" for i in range(len(chunks))],
                    metadatas=[{"source": "current"} for _ in chunks]
                )
                chunks_stored = len(chunks)
        except Exception as e:
            print(f"[main] Vector store step failed: {e}")
            extra = f"Q&A search won't work for this upload (vector store error: {e})."
            warning = (warning + " " if warning else "") + extra

        transcript_store["text"] = text

        result = {
            "characters": len(text),
            "chunks_stored": chunks_stored,
            "ner": ner,
            "sentiment": {
                "average": round(float(np.mean(scores)), 4) if scores else 0,
                "scores": scores
            },
            "speaker_sentiment": speaker_sentiment,
            "financial_metrics": financial_metrics,
            "summary": summary,
            "risks": risks
        }
        if warning:
            result["warning"] = warning
        return result
    except Exception as e:
        return {"error": str(e)}


class QuestionRequest(BaseModel):
    question: str


@app.post("/ask")
def ask(req: QuestionRequest):
    try:
        client = get_chroma_client()
        collection = client.get_or_create_collection("transcripts")
        embeddings = get_embeddings()
        if embeddings is None:
            return {"answer": "The embedding model isn't available right now. Try again in a moment.", "sources": []}

        q_embedding = embeddings.embed_query(req.question)
        results = collection.query(query_embeddings=[q_embedding], n_results=3)
        if not results["documents"] or not results["documents"][0]:
            return {"answer": "No transcript has been analyzed yet — upload one on the Dashboard first.", "sources": []}
        context = " ".join(results["documents"][0])

        if GROQ_API_KEY and GROQ_API_KEY != "your_groq_key_here":
            client_groq = Groq(api_key=GROQ_API_KEY)
            response = client_groq.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are a financial analyst. Answer questions based only on the provided earnings call transcript context. Be concise and specific."},
                    {"role": "user", "content": f"Context from earnings call:\n{context}\n\nQuestion: {req.question}"}
                ],
                max_tokens=400
            )
            answer = response.choices[0].message.content
        else:
            answer = f"(No GROQ_API_KEY set — showing raw matched context instead.) {context[:400]}"

        return {"answer": answer, "sources": results["documents"][0]}
    except Exception as e:
        return {"answer": f"Error: {str(e)}", "sources": []}


class FactCheckRequest(BaseModel):
    ticker: str
    text: str


@app.post("/factcheck")
def factcheck(req: FactCheckRequest):
    try:
        import yfinance as yf
        stock = yf.Ticker(req.ticker)
        financials = stock.financials

        real_data = {}
        if financials is not None and not financials.empty:
            if 'Total Revenue' in financials.index:
                real_data['revenue'] = float(financials.loc['Total Revenue'].iloc[0])
            if 'Net Income' in financials.index:
                real_data['net_income'] = float(financials.loc['Net Income'].iloc[0])
            if 'Gross Profit' in financials.index:
                real_data['gross_profit'] = float(financials.loc['Gross Profit'].iloc[0])

        sentences = [s for s in split_sentences(req.text.replace('\n', ' '))
                     if any(w in s.lower() for w in
                            ['revenue', 'billion', 'million', 'profit', 'grew', 'record', 'increased'])]

        results = []
        for sent in sentences[:10]:
            numbers = re_module.findall(r'\$?([\d.]+)\s*billion', sent, re_module.IGNORECASE)
            status = "unverified"
            real_value = None

            if numbers and 'revenue' in real_data and 'revenue' in sent.lower():
                claimed = float(numbers[0]) * 1e9
                actual = real_data['revenue']
                if actual > 0:
                    diff_pct = abs(claimed - actual) / actual * 100
                    if diff_pct < 5:
                        status = "verified"
                    elif diff_pct < 15:
                        status = "close"
                    else:
                        status = "flagged"
                    real_value = f"${actual / 1e9:.2f}B"

            results.append({
                "claim": sent[:200],
                "status": status,
                "real_value": real_value,
                "flagged": status == "flagged"
            })

        return {
            "ticker": req.ticker.upper(),
            "real_financials": {k: f"${v / 1e9:.2f}B" for k, v in real_data.items()},
            "results": [r for r in results if r["status"] != "unverified"],
            "total_claims": len(results),
            "verified": len([r for r in results if r["status"] == "verified"]),
            "flagged": len([r for r in results if r["status"] == "flagged"])
        }
    except Exception as e:
        return {"results": [], "error": str(e)}


class BriefRequest(BaseModel):
    company: str
    summary: str
    sentiment: dict
    risks: list
    financial_metrics: dict
    speaker_sentiment: dict
    fact_check_results: list


@app.post("/generate-brief")
def generate_brief(req: BriefRequest):
    try:
        brief = generate_analyst_brief(
            summary=req.summary,
            sentiment_data=req.sentiment,
            risks=req.risks,
            financial_metrics=req.financial_metrics,
            speaker_sentiment=req.speaker_sentiment,
            fact_check_results=req.fact_check_results,
            groq_api_key=GROQ_API_KEY,
            company=req.company
        )
        return {"brief": brief, "company": req.company}
    except Exception as e:
        return {"error": str(e), "brief": ""}


class ExportRequest(BaseModel):
    brief: str
    company: str


@app.post("/export-brief")
def export_brief(req: ExportRequest):
    try:
        from fpdf import FPDF
        from datetime import datetime

        pdf = FPDF()
        pdf.set_margins(20, 20, 20)
        pdf.add_page()

        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(29, 185, 154)
        pdf.cell(0, 10, "Full Stack Finance", ln=True)

        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 7, f"Analyst Brief: {req.company}", ln=True)
        pdf.cell(0, 7, f"Generated: {datetime.now().strftime('%B %d, %Y')}", ln=True)
        pdf.ln(4)

        pdf.set_draw_color(29, 185, 154)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(6)

        for line in req.brief.split('\n'):
            line = line.strip()
            if not line:
                pdf.ln(3)
                continue
            is_header = any(line.startswith(h) for h in
                            ['HEADLINE', 'BULL', 'BEAR', 'MANAGEMENT', 'KEY RISKS', 'BOTTOM LINE'])
            if is_header:
                pdf.set_font("Helvetica", "B", 12)
                pdf.set_text_color(29, 185, 154)
                pdf.multi_cell(0, 8, line)
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(40, 40, 40)
            else:
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(40, 40, 40)
                pdf.multi_cell(0, 6, line)

        pdf.ln(8)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 5, "Generated by Full Stack Finance NLP Platform | For educational purposes only", ln=True)

        pdf_bytes = bytes(pdf.output())
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=brief_{req.company.replace(' ', '_')}.pdf"}
        )
    except Exception as e:
        return {"error": str(e)}