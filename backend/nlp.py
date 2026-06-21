import threading
import os
import io
import re

import numpy as np
import torch
import spacy
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from pypdf import PdfReader

# ------------------------------------------------------------
# Lazy-loaded ML resources.
#
# IMPORTANT: nothing here loads when this module is imported.
# Each model loads the first time it's actually needed, behind a
# lock so two concurrent requests can't trigger a duplicate
# download. This is what lets `uvicorn` start in ~1 second
# instead of blocking for minutes (or crashing the whole API)
# while large models download from Hugging Face / OpenAI.
# ------------------------------------------------------------
_load_lock = threading.Lock()

_spacy_nlp = None

_finbert_tokenizer = None
_finbert_model = None
_finbert_status = None  # None = not attempted yet, True/False after attempt

_whisper_model = None
_whisper_status = None
_whisper_backend = None  # "faster-whisper" | "openai-whisper" | None

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")  # tiny/base/small/medium


def _get_spacy():
    global _spacy_nlp
    if _spacy_nlp is None:
        with _load_lock:
            if _spacy_nlp is None:
                _spacy_nlp = spacy.load("en_core_web_sm")
    return _spacy_nlp


def _get_finbert():
    global _finbert_tokenizer, _finbert_model, _finbert_status
    if _finbert_status is None:
        with _load_lock:
            if _finbert_status is None:
                try:
                    _finbert_tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
                    _finbert_model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
                    _finbert_status = True
                except Exception as e:
                    print(f"[nlp] Could not load FinBERT ({e}). Sentiment will fall back to neutral.")
                    _finbert_status = False
    return _finbert_tokenizer, _finbert_model, _finbert_status


def _get_whisper():
    """Try faster-whisper first — it's a CTranslate2 reimplementation of
    Whisper that's roughly 4x faster than openai-whisper on CPU at int8
    quantization, for the same accuracy. Falls back to openai-whisper if
    faster-whisper can't be imported."""
    global _whisper_model, _whisper_status, _whisper_backend
    if _whisper_status is None:
        with _load_lock:
            if _whisper_status is None:
                try:
                    from faster_whisper import WhisperModel
                    _whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
                    _whisper_backend = "faster-whisper"
                    _whisper_status = True
                except Exception as e:
                    print(f"[nlp] faster-whisper unavailable ({e}); falling back to openai-whisper.")
                    try:
                        import whisper
                        _whisper_model = whisper.load_model(WHISPER_MODEL_SIZE)
                        _whisper_backend = "openai-whisper"
                        _whisper_status = True
                    except Exception as e2:
                        print(f"[nlp] Could not load any Whisper backend ({e2}).")
                        _whisper_status = False
    return _whisper_model, _whisper_status


def model_status():
    """Used by the /health endpoint so the frontend can show what's actually ready."""
    return {
        "spacy_loaded": _spacy_nlp is not None,
        "finbert_loaded": _finbert_status is True,
        "whisper_loaded": _whisper_status is True,
        "whisper_backend": _whisper_backend or "none",
        "whisper_model_size": WHISPER_MODEL_SIZE,
    }


# ------------------------------------------------------------
# Sentence splitting.
#
# A plain `text.split('.')` treats every period as a sentence boundary —
# including the one inside "102.5 billion" or "47.2 percent". On an
# earnings call transcript that's everywhere, and it corrupts almost
# every number in the document: "Apple reports 102.5 billion in revenue"
# becomes the fragments "...102" and "5 billion in revenue...", which is
# exactly the kind of thing you don't want feeding a finance analyzer.
#
# This splits on '.', '!', '?' but only when the character isn't sitting
# between two digits (i.e. not a decimal point).
# ------------------------------------------------------------
_SENT_BOUNDARY = re.compile(r'(?<!\d)[.!?](?!\d)')


def split_sentences(text):
    """Decimal-safe sentence splitter — use this instead of text.split('.')
    anywhere financial figures might appear."""
    parts = _SENT_BOUNDARY.split(text)
    return [p.strip() for p in parts if p.strip()]


# Speaker tags like "Kevan Parekh: Products revenue was..." have no space
# or sentence boundary between the name and what follows, which can fool
# spaCy into treating "Kevan Parekh: Products" as one PERSON entity. Strip
# the tag before running NER so the model only sees the spoken content.
_SPEAKER_TAG_RE = re.compile(r'(?m)^[A-Z][a-zA-Z\s]{2,30}:\s*')


# ------------------------------------------------------------
# NLP functions — same public API as before, callers don't change.
# ------------------------------------------------------------
def extract_companies_and_people(text):
    cleaned = _SPEAKER_TAG_RE.sub('', text)
    doc = _get_spacy()(cleaned)
    companies = list(set(e.text for e in doc.ents if e.label_ == "ORG"))
    people = list(set(e.text for e in doc.ents if e.label_ == "PERSON"))
    return {"companies": companies, "people": people}


def _finbert_forward_batch(texts):
    """One forward pass for a whole list of sentences instead of one call
    per sentence. On CPU, per-call overhead (tokenize + model dispatch)
    dominates when you call this sentence-by-sentence in a loop — batching
    is the single biggest speedup available here without adding a GPU."""
    tokenizer, model, ok = _get_finbert()
    if not ok or not texts:
        return [
            {"score": 0.0, "positive": 0.33, "neutral": 0.34, "negative": 0.33, "label": "Neutral"}
            for _ in texts
        ]
    inputs = tokenizer(texts, return_tensors="pt", truncation=True, max_length=512, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
    probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
    results = []
    for i in range(len(texts)):
        pos = probs[i][0].item()
        neg = probs[i][1].item()
        neu = probs[i][2].item()
        score = pos - neg
        results.append({
            "score": round(score, 4),
            "positive": round(pos, 4),
            "neutral": round(neu, 4),
            "negative": round(neg, 4),
            "label": "Positive" if score > 0.2 else ("Negative" if score < -0.2 else "Neutral")
        })
    return results


def analyze_sentiment(text):
    """Single-text sentiment (kept for backward compatibility / one-off calls).
    If you're scoring a list of sentences, use analyze_sentiment_batch instead —
    it's dramatically faster on CPU than calling this in a loop."""
    return _finbert_forward_batch([text])[0]


def analyze_sentiment_batch(texts):
    """Score a list of sentences in batched forward passes (16 at a time, to
    keep memory bounded on very long transcripts) instead of one-by-one."""
    if not texts:
        return []
    BATCH = 16
    out = []
    try:
        for i in range(0, len(texts), BATCH):
            out.extend(_finbert_forward_batch(texts[i:i + BATCH]))
    except Exception as e:
        print(f"[nlp] Batched sentiment failed ({e}); returning neutral for this batch.")
        out = [{"score": 0.0, "positive": 0.33, "neutral": 0.34, "negative": 0.33, "label": "Neutral"} for _ in texts]
    return out


def summarize_text(text, num_sentences=5):
    text = text.replace('\n', ' ').replace('\r', ' ')
    sentences = split_sentences(text)
    keywords = ['billion', 'million', 'revenue', 'profit', 'increased',
                'decreased', 'launch', 'future', 'outlook', 'quarter',
                'year', 'expect', 'growth', 'record', 'guidance']
    important = []
    for sent in sentences:
        sent = sent.strip()
        if 40 < len(sent) < 300:
            if any(k in sent.lower() for k in keywords):
                important.append(sent)
            if len(important) >= num_sentences:
                break
    return '. '.join(important) + '.' if important else "No summary available."


def extract_text_from_pdf(file_bytes):
    reader = PdfReader(io.BytesIO(file_bytes))
    text = ""
    for page in reader.pages:
        t = page.extract_text()
        if t:
            text += t + " "
    return text


def detect_risks(text):
    risk_keywords = [
        'uncertain', 'risk', 'decline', 'challenge', 'headwind',
        'concern', 'volatile', 'lawsuit', 'litigation', 'constraint',
        'tariff', 'inflation', 'recession', 'loss', 'warning'
    ]
    sentences = split_sentences(text.replace('\n', ' '))
    risks = []
    for sent in sentences:
        sent = sent.strip()
        if 20 < len(sent) < 300:
            if any(k in sent.lower() for k in risk_keywords):
                risks.append(sent)
        if len(risks) >= 5:
            break
    return risks if risks else ["No significant risk language detected."]


def split_by_speaker(text):
    lines = text.split('\n')
    speakers = {}
    current_speaker = "General"
    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = re.match(r'^([A-Z][a-zA-Z\s]{2,30}):\s*(.+)', line)
        if match:
            current_speaker = match.group(1).strip()
            content = match.group(2).strip()
            if current_speaker not in speakers:
                speakers[current_speaker] = []
            speakers[current_speaker].append(content)
        else:
            if current_speaker not in speakers:
                speakers[current_speaker] = []
            speakers[current_speaker].append(line)
    return {k: ' '.join(v) for k, v in speakers.items() if len(' '.join(v)) > 100}


def analyze_by_speaker(text):
    """Sentiment per speaker — scored with one batched FinBERT call per
    speaker instead of one call per sentence."""
    speakers = split_by_speaker(text)
    results = {}
    for speaker, content in speakers.items():
        sentences = [s for s in split_sentences(content) if len(s) > 30][:10]
        if not sentences:
            continue
        scored = analyze_sentiment_batch(sentences)
        scores = [s["score"] for s in scored]
        avg = round(sum(scores) / len(scores), 4)
        results[speaker] = {
            "average": avg,
            "label": "Positive" if avg > 0.2 else ("Negative" if avg < -0.2 else "Neutral"),
            "sentences_analyzed": len(scores)
        }
    return results


# ------------------------------------------------------------
# Financial metric extraction.
#
# The old patterns required a literal "$" or "%" character to be present
# (e.g. r'\$[\d,.]+.*?billion'). That works on a typed financial document,
# but earnings call TRANSCRIPTS — whether from a PDF transcript or from
# Whisper — are spoken-word style: "102.5 billion in revenue", "47.2
# percent gross margin". There's no $ or % symbol anywhere. So on this
# exact use case (earnings call transcripts) the old patterns matched
# nothing, ever — that's why Financial Metrics always came back empty.
# These versions make the $ optional and accept "percent" as well as "%".
# ------------------------------------------------------------
_MONEY = r'\$?\s?[\d,]+(?:\.\d+)?\s*(?:billion|million|bn|mn)\b'
_NUMBER = r'\$?\s?[\d,]+(?:\.\d+)?'
_PERCENT = r'[\d.]+\s*(?:%|percent)\b'

_METRIC_PATTERNS = {
    "revenue": rf'(?:revenue|sales)\b.{{0,60}}?{_MONEY}|{_MONEY}.{{0,60}}?(?:revenue|sales)\b',
    "eps": rf'(?:eps|earnings per share|diluted)\b.{{0,40}}?{_NUMBER}|{_NUMBER}.{{0,40}}?(?:per share|eps|diluted|earnings per)\b',
    "gross_margin": rf'gross margin\b.{{0,40}}?{_PERCENT}|{_PERCENT}.{{0,40}}?gross margin\b',
    "net_income": rf'net income\b.{{0,60}}?{_MONEY}|{_MONEY}.{{0,60}}?net income\b',
    "guidance": rf'(?:expect|guide|forecast|anticipate|outlook)\b.{{0,60}}?(?:{_MONEY}|{_PERCENT})',
    "growth": rf'{_PERCENT}.{{0,40}}?(?:year.over.year|yoy|growth|increase|grew)\b|(?:year.over.year|yoy|growth|increase|grew)\b.{{0,40}}?{_PERCENT}',
}


def extract_financial_metrics(text):
    metrics = {k: [] for k in _METRIC_PATTERNS}
    sentences = [s for s in split_sentences(text.replace('\n', ' ')) if len(s) > 20]
    for sent in sentences:
        for category, pattern in _METRIC_PATTERNS.items():
            if re.search(pattern, sent, re.IGNORECASE):
                if sent not in metrics[category]:
                    metrics[category].append(sent)
    return {k: v[:3] for k, v in metrics.items() if v}


def generate_analyst_brief(summary, sentiment_data, risks,
                           financial_metrics, speaker_sentiment,
                           fact_check_results, groq_api_key, company="Unknown"):
    from groq import Groq
    client = Groq(api_key=groq_api_key)

    speaker_text = "\n".join([
        f"- {spk}: {d['label']} (score: {d['average']})"
        for spk, d in (speaker_sentiment or {}).items()
    ]) or "Not available"

    metrics_text = "\n".join([
        f"- {k.upper()}: {v[0][:100] if v else 'Not found'}"
        for k, v in (financial_metrics or {}).items()
    ]) or "Not extracted"

    risks_text = "\n".join(
        f"- {r[:120]}" for r in (risks or [])[:4]
    ) or "None detected"

    prompt = f"""You are a senior financial analyst. Write a concise analyst brief for {company}.

SUMMARY: {summary}

SPEAKER SENTIMENT:
{speaker_text}

FINANCIAL METRICS:
{metrics_text}

RISK FLAGS:
{risks_text}

Write in this exact structure:

HEADLINE
[One sentence: what happened this quarter]

BULL CASE
[2 sentences on strongest positives]

BEAR CASE
[2 sentences on key concerns]

MANAGEMENT TONE
[One sentence per speaker on their tone]

KEY RISKS
[3 bullet points]

BOTTOM LINE
[One sentence verdict for an investor]

Be specific. Use actual numbers."""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are a senior financial analyst writing institutional research notes."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=800
    )
    return response.choices[0].message.content


def transcribe_audio(audio_path):
    """Use local Whisper (faster-whisper if available, else openai-whisper),
    else fall back to OpenAI's hosted API if a key is set."""
    model, ok = _get_whisper()
    if ok:
        if _whisper_backend == "faster-whisper":
            segments, info = model.transcribe(audio_path, beam_size=5)
            text = " ".join(seg.text.strip() for seg in segments)
            return text.strip(), info.language
        else:
            result = model.transcribe(audio_path)
            return result["text"], result["language"]

    import openai
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        openai.api_key = api_key
        with open(audio_path, "rb") as f:
            result = openai.audio.transcriptions.create(model="whisper-1", file=f)
        return result.text, "en"

    raise RuntimeError(
        "Cannot transcribe: local Whisper model failed to load and OPENAI_API_KEY is not set."
    )