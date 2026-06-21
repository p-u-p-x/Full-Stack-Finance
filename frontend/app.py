import os
import streamlit as st
import requests
import plotly.graph_objects as go
import plotly.express as px
from streamlit_option_menu import option_menu

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")   # <-- changed to localhost

st.set_page_config(
    page_title="Full Stack Finance",
    layout="wide",
    page_icon="🔬",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@2.44.0/tabler-icons.min.css">
<style>
    :root {
        --primary: #1DB99A;
        --bg: #0A0F1E;
        --card-bg: #111827;
        --card-bg2: #1A2235;
        --border: #1E2D45;
        --text: #F1F5F9;
        --text-muted: #94A3B8;
        --amber: #EF9F27;
    }

    #MainMenu, footer, header { visibility: hidden !important; }
    [data-testid="stToolbar"]    { display: none !important; }
    .stDeployButton              { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }

    .stApp { background: var(--bg) !important; color: var(--text) !important; }
    .stApp::before {
        content: ''; position: fixed; top:0; left:0; right:0; bottom:0;
        background:
            radial-gradient(ellipse 80% 50% at 10% 10%, rgba(29,185,154,.12) 0%, transparent 60%),
            radial-gradient(ellipse 60% 40% at 90% 80%, rgba(139,124,246,.10) 0%, transparent 60%);
        pointer-events: none; z-index: 0;
    }
    .block-container { position:relative; z-index:1; padding:1.5rem 2rem !important; max-width:100% !important; }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg,#0D1628 0%,#111827 60%,#0A1020 100%) !important;
        border-right: 1px solid rgba(29,185,154,.25) !important;
    }

    /* Main content buttons — green gradient */
    .block-container .stButton > button {
        background: linear-gradient(135deg, var(--primary) 0%, #0D8A70 100%) !important;
        color: white !important; border: none !important; border-radius: 8px !important;
        font-weight: 600 !important; font-size: 14px !important; padding: 10px 24px !important;
        min-height: unset !important; height: auto !important;
        box-shadow: 0 4px 15px rgba(29,185,154,.25) !important;
        width: auto !important; line-height: 1.4 !important;
    }
    .block-container .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 24px rgba(29,185,154,.45) !important;
    }

    /* Cards */
    .metric-card {
        background: linear-gradient(135deg,var(--card-bg) 0%,var(--card-bg2) 100%);
        padding: 1.25rem 1.5rem; border-radius: 14px;
        border: 1px solid var(--border); border-left: 3px solid var(--primary);
        margin: .25rem 0;
        box-shadow: 0 4px 24px rgba(0,0,0,.4), inset 0 1px 0 rgba(255,255,255,.04);
        transition: transform .2s, box-shadow .2s;
    }
    .metric-card:hover { transform: translateY(-3px); box-shadow: 0 8px 32px rgba(29,185,154,.15); }
    .metric-label { color:var(--text-muted); font-size:.8rem; margin:0 0 .4rem; text-transform:uppercase; letter-spacing:.05em; }
    .metric-value { color:var(--primary); font-size:1.9rem; font-weight:700; margin:0; line-height:1; }
    .metric-sub   { color:#4DD9C0; font-size:.78rem; margin:.4rem 0 0; }

    .card {
        background: linear-gradient(135deg,var(--card-bg) 0%,var(--card-bg2) 100%);
        border-radius:14px; border:1px solid var(--border);
        padding:1.5rem 1.75rem; margin-bottom:1rem;
        box-shadow:0 4px 24px rgba(0,0,0,.35),inset 0 1px 0 rgba(255,255,255,.03);
    }
    .card-title {
        font-size:1rem; font-weight:600; color:var(--text); margin-bottom:1rem;
        display:flex; align-items:center; gap:8px;
        border-bottom:1px solid var(--border); padding-bottom:.75rem;
    }
    .card-title i { color:var(--primary); font-size:17px; }
    .section-header {
        font-size:1.2rem; font-weight:700; color:var(--text);
        border-left:3px solid var(--primary); padding-left:.75rem; margin:1.25rem 0 .75rem;
    }
    .chip { display:inline-block; background:rgba(29,185,154,.12); color:#4DD9C0;
            font-size:12px; font-weight:500; padding:5px 13px;
            border-radius:20px; margin:3px; border:1px solid rgba(29,185,154,.25); }
    .chip.purple { background:rgba(139,124,246,.12); color:#A89CF7; border-color:rgba(139,124,246,.25); }
    .risk-row { display:flex; gap:10px; align-items:flex-start;
                background:rgba(239,159,39,.08); border-left:3px solid var(--amber);
                border-radius:0 8px 8px 0; padding:10px 14px; margin-bottom:8px; }
    .risk-row i   { color:var(--amber); font-size:16px; margin-top:2px; flex-shrink:0; }
    .risk-row span { font-size:13px; color:var(--text); line-height:1.5; }
    .sumbox { background:rgba(29,185,154,.06); border-left:3px solid var(--primary);
              border-radius:0 8px 8px 0; padding:16px 20px; font-size:14px; color:var(--text); line-height:1.8; }
    .ansbox { background:rgba(29,185,154,.06); border:1px solid rgba(29,185,154,.25);
              border-radius:10px; padding:16px 20px; font-size:14px; color:var(--text); line-height:1.8; margin-top:12px; }
    .col-label { font-size:11px; font-weight:600; color:var(--text-muted);
                 text-transform:uppercase; letter-spacing:.06em; margin-bottom:10px; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { background:var(--card-bg); border-radius:10px; padding:4px; gap:4px; border:1px solid var(--border); }
    .stTabs [data-baseweb="tab"]      { border-radius:7px !important; color:var(--text-muted) !important; font-size:13px !important; background:transparent !important; }
    .stTabs [aria-selected="true"]    { background:var(--primary) !important; color:white !important; }
    .stTabs [data-baseweb="tab-highlight"] { display:none !important; }

    div[data-testid="stMetric"]              { background:var(--card-bg); border:1px solid var(--border); border-radius:12px; padding:16px !important; }
    div[data-testid="stMetricLabel"] > div  { color:var(--text-muted) !important; }
    div[data-testid="stMetricValue"] > div  { color:var(--text) !important; font-weight:700 !important; }
    div[data-testid="stTextInput"] input    { background:var(--card-bg) !important; border:1px solid var(--border) !important; border-radius:8px !important; color:var(--text) !important; }
    div[data-testid="stFileUploader"]        { background:var(--card-bg); border-radius:10px; border:1px solid var(--border); }

    .stSuccess { background:rgba(29,185,154,.08) !important; border:1px solid rgba(29,185,154,.3) !important; }
    .stInfo    { background:rgba(59,130,246,.08)  !important; border:1px solid rgba(59,130,246,.3)  !important; }
    .stWarning { background:rgba(239,159,39,.08)  !important; border:1px solid rgba(239,159,39,.3)  !important; }
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li { color:var(--text) !important; }

    ::-webkit-scrollbar       { width:5px; }
    ::-webkit-scrollbar-track { background:var(--bg); }
    ::-webkit-scrollbar-thumb { background:rgba(29,185,154,.4); border-radius:3px; }
</style>
""", unsafe_allow_html=True)

# ── Session state defaults ────────────────────────────────────────────────────
for key in ("page", "results", "fact_check", "brief", "brief_company",
            "transcript_text", "detected_language"):
    if key not in st.session_state:
        st.session_state[key] = "Dashboard" if key == "page" else None

# ── Sidebar ───────────────────────────────────────────────────────────────────
PAGES = {
    "Dashboard":  "Upload and Analyze",
    "Audio":      "Speech to Text",
    "Companies":  "NER Results",
    "Sentiment":  "FinBERT + Speakers",
    "Metrics":    "Financial Data",
    "Fact Check": "Verify Claims",
    "Summary":    "Key Insights",
    "Risk Flags": "Risk Detection",
    "Brief":      "Analyst Brief",
    "Ask":        "RAG Q&A",
}
PAGE_ICONS = [
    "speedometer2", "mic", "building", "bar-chart-line", "calculator",
    "shield-check", "file-earmark-text", "exclamation-triangle",
    "file-earmark-arrow-down", "chat-dots",
]

with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:32px 0 20px;">
        <div style="width:52px;height:52px;margin:0 auto 10px;
                    background:linear-gradient(135deg,#1DB99A 0%,#0A7A67 100%);
                    border-radius:14px;display:flex;align-items:center;justify-content:center;
                    box-shadow:0 4px 16px rgba(29,185,154,.35);">
            <i class="ti ti-brain" style="color:white;font-size:26px;"></i>
        </div>
        <div style="color:#1DB99A;font-weight:800;font-size:1rem;letter-spacing:.04em;">Full Stack Finance</div>
        <div style="color:#475569;font-size:.7rem;letter-spacing:.08em;margin-top:2px;">EARNINGS INTELLIGENCE PLATFORM</div>
    </div>
    """, unsafe_allow_html=True)

    selected = option_menu(
        menu_title=None,
        options=list(PAGES.keys()),
        icons=PAGE_ICONS,
        menu_icon="cast",
        default_index=list(PAGES.keys()).index(st.session_state.page),
        key="nav_menu",
        styles={
            "container":        {"padding": "0!important", "background-color": "transparent"},
            "icon":             {"color": "#64748B", "font-size": "16px"},
            "nav-link": {
                "font-size": "13px", "text-align": "left", "margin": "2px 0",
                "padding": "10px 14px", "border-radius": "9px",
                "color": "#94A3B8", "background-color": "transparent",
                "--hover-color": "rgba(29,185,154,0.08)",
            },
            "nav-link-selected": {
                "background-color": "rgba(29,185,154,0.15)",
                "color": "#F1F5F9", "font-weight": "600",
            },
        },
    )
    st.session_state.page = selected

    st.markdown("""
    <div style="margin-top:16px;padding:14px;
                background:linear-gradient(135deg,rgba(29,185,154,.08) 0%,rgba(139,124,246,.06) 100%);
                border-radius:12px;border:1px solid rgba(29,185,154,.15);">
        <div style="color:#1DB99A;font-size:11px;font-weight:700;margin-bottom:8px;
                    text-transform:uppercase;letter-spacing:.06em;">NLP Stack</div>
        <div style="color:#64748B;font-size:11px;line-height:2.1;">
            <span style="color:#4DD9C0;">◆</span> spaCy NER<br>
            <span style="color:#4DD9C0;">◆</span> FinBERT Sentiment<br>
            <span style="color:#4DD9C0;">◆</span> LangChain RAG<br>
            <span style="color:#4DD9C0;">◆</span> ChromaDB Vectors<br>
            <span style="color:#4DD9C0;">◆</span> Groq LLaMA 3.1
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Top bar ───────────────────────────────────────────────────────────────────
page        = st.session_state.page
has_results = st.session_state.results is not None

col_title, col_user = st.columns([3, 1])
with col_title:
    st.markdown(f"""
    <div style="margin-bottom:20px;">
        <div style="font-size:11px;color:#475569;margin-bottom:4px;text-transform:uppercase;letter-spacing:.06em;">
            Full Stack Finance &nbsp;/&nbsp; {page}
        </div>
        <h1 style="font-size:1.7rem;font-weight:700;margin:0;
                   background:linear-gradient(135deg,#F1F5F9 0%,#CBD5E1 100%);
                   -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">
            {page}
        </h1>
    </div>""", unsafe_allow_html=True)
with col_user:
    st.markdown("""
    <div style="display:flex;justify-content:flex-end;margin-bottom:20px;">
        <div style="display:flex;align-items:center;gap:10px;
                    background:linear-gradient(135deg,#111827 0%,#1A2235 100%);
                    border-radius:24px;padding:6px 16px 6px 6px;
                    border:1px solid rgba(29,185,154,.2);box-shadow:0 2px 12px rgba(0,0,0,.3);">
            <div style="width:32px;height:32px;background:linear-gradient(135deg,#1DB99A 0%,#0A7A67 100%);
                        border-radius:50%;display:flex;align-items:center;justify-content:center;
                        font-size:13px;font-weight:700;color:white;">FS</div>
            <div>
                <div style="font-size:13px;color:#F1F5F9;font-weight:600;line-height:1.2;">Full Stack Finance</div>
                <div style="font-size:10px;color:#4DD9C0;line-height:1.2;">NLP Analytics</div>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

# ── Global metrics bar ────────────────────────────────────────────────────────
if has_results:
    data       = st.session_state.results
    avg        = data["sentiment"]["average"]
    label      = "Positive" if avg > .2 else ("Negative" if avg < -.2 else "Neutral")
    ent_count  = len(data["ner"]["companies"]) + len(data["ner"]["people"])
    sent_color = "#1DB99A" if avg > .2 else ("#EF4444" if avg < -.2 else "#94A3B8")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="metric-card">
            <p class="metric-label"><i class="ti ti-file-text" style="font-size:12px;"></i> Characters</p>
            <p class="metric-value">{data["characters"]:,}</p>
            <p class="metric-sub">◆ Fully processed</p></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card" style="border-left-color:#8B7CF6;">
            <p class="metric-label"><i class="ti ti-database" style="font-size:12px;"></i> Vectors Stored</p>
            <p class="metric-value" style="color:#A89CF7;">{data.get("chunks_stored","N/A")}</p>
            <p class="metric-sub" style="color:#A89CF7;">◆ In ChromaDB</p></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card" style="border-left-color:{sent_color};">
            <p class="metric-label"><i class="ti ti-mood-smile" style="font-size:12px;"></i> Sentiment</p>
            <p class="metric-value" style="color:{sent_color};">{label}</p>
            <p class="metric-sub" style="color:{sent_color};">◆ Score: {avg:.3f}</p></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="metric-card" style="border-left-color:#EF9F27;">
            <p class="metric-label"><i class="ti ti-tag" style="font-size:12px;"></i> Entities</p>
            <p class="metric-value" style="color:#EF9F27;">{ent_count}</p>
            <p class="metric-sub" style="color:#EF9F27;">◆ Extracted by spaCy</p></div>""", unsafe_allow_html=True)
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)


# ── Helper: run analysis on raw text/bytes ────────────────────────────────────
def run_analysis(file_bytes, filename, mime):
    """Post to /analyze and store results. Returns True on success."""
    try:
        resp = requests.post(
            f"{BACKEND}/analyze",
            files={"file": (filename, file_bytes, mime)},
            timeout=600,
        )
        if resp.status_code == 200:
            result = resp.json()
            if "error" in result:
                st.error(f"Analysis failed: {result['error']}")
                return False
            st.session_state.results = result
            if result.get("warning"):
                st.warning(result["warning"])
            return True
        else:
            st.error(f"Error {resp.status_code}: {resp.text}")
            return False
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the backend. If you just started the containers, wait a minute for models to load.")
        return False
    except requests.exceptions.ReadTimeout:
        st.error("Analysis is taking longer than expected on first run (models loading). Wait a moment and try again.")
        return False
    except Exception as e:
        st.error(f"Error: {e}")
        return False


# ═════════════════════════════════════════════════════════════════════════════
# PAGES
# ═════════════════════════════════════════════════════════════════════════════

if page == "Dashboard":
    st.markdown('<div class="section-header">Upload Transcript</div>', unsafe_allow_html=True)
    st.markdown('<div class="card"><div class="card-title"><i class="ti ti-cloud-upload"></i> Upload Earnings Call PDF or TXT</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader("Upload file", type=["pdf", "txt"], label_visibility="collapsed")
    if uploaded:
        kb = round(len(uploaded.getvalue()) / 1024, 1)
        st.success(f"◆ Ready: {uploaded.name} ({kb}KB)")
        if st.button("Run Analysis"):
            with st.spinner("Running NLP pipeline — first run may take a few minutes while models warm up..."):
                mime = "application/pdf" if uploaded.name.endswith(".pdf") else "text/plain"
                if run_analysis(uploaded.getvalue(), uploaded.name, mime):
                    st.success("Analysis complete! Use the sidebar to explore results.")
                    st.rerun()
    else:
        st.markdown("""
        <div style="border:1.5px dashed rgba(29,185,154,.3);border-radius:12px;padding:36px;
                    text-align:center;background:rgba(29,185,154,.03);">
            <i class="ti ti-cloud-upload" style="font-size:44px;color:#1DB99A;display:block;margin-bottom:14px;"></i>
            <p style="color:#94A3B8;font-size:14px;margin:0;font-weight:500;">Drop your earnings call PDF or TXT here</p>
            <div style="margin-top:14px;display:flex;justify-content:center;gap:8px;flex-wrap:wrap;">
                <span style="background:rgba(29,185,154,.1);color:#4DD9C0;font-size:11px;padding:3px 10px;border-radius:12px;border:1px solid rgba(29,185,154,.2);">NER</span>
                <span style="background:rgba(139,124,246,.1);color:#A89CF7;font-size:11px;padding:3px 10px;border-radius:12px;border:1px solid rgba(139,124,246,.2);">Sentiment</span>
                <span style="background:rgba(29,185,154,.1);color:#4DD9C0;font-size:11px;padding:3px 10px;border-radius:12px;border:1px solid rgba(29,185,154,.2);">RAG Q&A</span>
                <span style="background:rgba(239,159,39,.1);color:#F0B429;font-size:11px;padding:3px 10px;border-radius:12px;border:1px solid rgba(239,159,39,.2);">Risk Flags</span>
            </div>
        </div>""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    if not has_results:
        st.info("Upload a PDF or TXT and click Run Analysis to get started.")
    else:
        st.success("Analysis loaded. Navigate using the sidebar.")


elif page == "Audio":
    st.markdown('<div class="section-header">Audio Transcription</div>', unsafe_allow_html=True)
    st.markdown('<div class="card"><div class="card-title"><i class="ti ti-microphone"></i> Upload Earnings Call Audio</div>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:13px;color:#64748B;margin-bottom:16px;">Powered by faster-whisper — runs locally, no API key needed</p>', unsafe_allow_html=True)

    audio_file = st.file_uploader("Upload audio", type=["mp3", "mp4", "wav", "m4a"], label_visibility="collapsed")

    if audio_file:
        kb = round(len(audio_file.getvalue()) / 1024, 1)
        st.success(f"Ready: {audio_file.name} ({kb:.0f}KB)")
        st.info("Transcription speed depends on audio length and CPU. First run also downloads the Whisper model. Do not close this tab.")

        if st.button("Transcribe + Analyze"):
            # ── Step 1: Transcribe ────────────────────────────────────────
            with st.spinner("Step 1/2 — Transcribing audio..."):
                try:
                    ext = audio_file.name.rsplit(".", 1)[-1].lower()
                    ct  = {"mp3": "audio/mpeg", "mp4": "audio/mp4",
                           "wav": "audio/wav",  "m4a": "audio/mp4"}.get(ext, "audio/mpeg")
                    res = requests.post(
                        f"{BACKEND}/transcribe",
                        files={"file": (audio_file.name, audio_file.getvalue(), ct)},
                        timeout=1200,
                    )
                except requests.exceptions.ConnectionError:
                    st.error("Cannot reach the backend.")
                    st.stop()
                except requests.exceptions.ReadTimeout:
                    st.error("Transcription timed out — the audio may be too long, or the Whisper model is still downloading. Try again.")
                    st.stop()
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.stop()

                if res.status_code != 200:
                    st.error(f"Backend returned {res.status_code}: {res.text[:300]}")
                    st.stop()

                tresult = res.json()
                if "error" in tresult:
                    st.error(f"Transcription error: {tresult['error']}")
                    st.stop()

                transcript_text = tresult["transcript"]
                lang            = tresult.get("language", "en").upper()
                st.session_state.transcript_text   = transcript_text
                st.session_state.detected_language = lang
                st.success(f"Transcription complete! Detected language: {lang}")

            # ── Show preview ──────────────────────────────────────────────
            with st.expander("Transcript preview (first 1000 chars)", expanded=True):
                st.text(transcript_text[:1000] + ("..." if len(transcript_text) > 1000 else ""))

            # ── Step 2: Auto-run NLP analysis ─────────────────────────────
            with st.spinner("Step 2/2 — Running NLP analysis on transcript..."):
                if run_analysis(transcript_text.encode(), "transcript.txt", "text/plain"):
                    st.success("Analysis complete! Navigate to any tab to see results.")
                    st.rerun()

    elif st.session_state.transcript_text:
        # Already transcribed in a previous run — show it and offer re-analysis
        st.info(f"Last transcript loaded ({st.session_state.detected_language or 'EN'}, "
                f"{len(st.session_state.transcript_text):,} chars)")
        with st.expander("Transcript preview"):
            st.text(st.session_state.transcript_text[:1000] + "...")
        if not has_results:
            if st.button("Run NLP Analysis on saved transcript"):
                with st.spinner("Running analysis..."):
                    if run_analysis(st.session_state.transcript_text.encode(), "transcript.txt", "text/plain"):
                        st.success("Done! Navigate to any tab.")
                        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


elif page == "Companies":
    if not has_results:
        st.warning("Upload and analyze a file first from the Dashboard or Audio tab.")
    else:
        data = st.session_state.results
        st.markdown('<div class="section-header">Named Entity Recognition</div>', unsafe_allow_html=True)
        st.markdown('<div class="card"><div class="card-title"><i class="ti ti-building-skyscraper"></i> Entities Extracted by spaCy</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="col-label">Companies and Organizations</div>', unsafe_allow_html=True)
            chips = "".join(f'<span class="chip">{c}</span>' for c in data["ner"]["companies"]) \
                    or '<span style="color:#475569;font-size:13px;">None detected</span>'
            st.markdown(chips, unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="col-label">People Mentioned</div>', unsafe_allow_html=True)
            chips = "".join(f'<span class="chip purple">{p}</span>' for p in data["ner"]["people"]) \
                    or '<span style="color:#475569;font-size:13px;">None detected</span>'
            st.markdown(chips, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


elif page == "Sentiment":
    if not has_results:
        st.warning("Upload and analyze a file first from the Dashboard or Audio tab.")
    else:
        data   = st.session_state.results
        scores = data["sentiment"]["scores"]
        avg    = data["sentiment"]["average"]
        label  = "Positive" if avg > .2 else ("Negative" if avg < -.2 else "Neutral")

        st.markdown('<div class="section-header">FinBERT Sentiment Analysis</div>', unsafe_allow_html=True)
        st.markdown('<div class="card"><div class="card-title"><i class="ti ti-chart-dots-3"></i> Sentence-level Sentiment</div>', unsafe_allow_html=True)

        m1, m2, m3 = st.columns(3)
        m1.metric("Overall Sentiment", label)
        m2.metric("Average Score", f"{avg:.3f}")
        m3.metric("Positive Sentences", f"{sum(1 for s in scores if s > .2)} of {len(scores)}")

        fig = go.Figure()
        fig.add_trace(go.Scatter(y=scores, mode="lines+markers",
            line=dict(color="#1DB99A", width=2.5), marker=dict(size=6, color="#1DB99A"),
            fill="tozeroy", fillcolor="rgba(29,185,154,0.07)"))
        fig.add_hline(y=0,   line_dash="dash", line_color="#475569", opacity=.7)
        fig.add_hline(y=.2,  line_dash="dot",  line_color="#1DB99A", opacity=.35)
        fig.add_hline(y=-.2, line_dash="dot",  line_color="#EF4444", opacity=.35)
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#F1F5F9"),
            xaxis=dict(title="Sentence #", gridcolor="#1A2235"),
            yaxis=dict(title="Score", range=[-1, 1], gridcolor="#1A2235"),
            height=300, margin=dict(l=0, r=0, t=20, b=0), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        counts = {
            "Positive": sum(1 for s in scores if s > .2),
            "Neutral":  sum(1 for s in scores if -.2 <= s <= .2),
            "Negative": sum(1 for s in scores if s < -.2),
        }
        fig2 = px.pie(values=list(counts.values()), names=list(counts.keys()),
            color_discrete_map={"Positive": "#1DB99A", "Neutral": "#475569", "Negative": "#EF4444"}, hole=.58)
        fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#F1F5F9"), height=240, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig2, use_container_width=True)

        speaker_data = data.get("speaker_sentiment", {})
        if speaker_data:
            st.markdown('<div class="col-label">Sentiment by Speaker</div>', unsafe_allow_html=True)
            for speaker, sdata in speaker_data.items():
                color = "#1DB99A" if sdata["average"] > .2 else ("#EF4444" if sdata["average"] < -.2 else "#94A3B8")
                bar_w = int(abs(sdata["average"]) * 100)
                st.markdown(f"""
                <div style="background:rgba(255,255,255,.03);border:1px solid #1E2D45;
                            border-radius:8px;padding:12px 16px;margin-bottom:8px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                        <span style="color:#F1F5F9;font-size:13px;font-weight:500;">{speaker}</span>
                        <span style="color:{color};font-size:13px;font-weight:600;">{sdata['label']} ({sdata['average']:.3f})</span>
                    </div>
                    <div style="height:4px;background:#1E2D45;border-radius:2px;">
                        <div style="height:100%;width:{bar_w}%;background:{color};border-radius:2px;"></div>
                    </div>
                    <div style="color:#475569;font-size:11px;margin-top:4px;">{sdata['sentences_analyzed']} sentences analyzed</div>
                </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


elif page == "Metrics":
    if not has_results:
        st.warning("Upload and analyze a file first from the Dashboard or Audio tab.")
    else:
        data    = st.session_state.results
        metrics = data.get("financial_metrics", {})
        st.markdown('<div class="section-header">Financial Metrics</div>', unsafe_allow_html=True)
        st.markdown('<div class="card"><div class="card-title"><i class="ti ti-calculator"></i> Extracted Financial Data</div>', unsafe_allow_html=True)
        if metrics:
            for cat, sents in metrics.items():
                if sents:
                    st.markdown(f'<div class="col-label">{cat.replace("_"," ").upper()}</div>', unsafe_allow_html=True)
                    for s in sents:
                        st.markdown(f'<div style="background:rgba(29,185,154,.06);border-left:3px solid #1DB99A;'
                                    f'padding:8px 14px;border-radius:0 6px 6px 0;margin-bottom:6px;'
                                    f'font-size:13px;color:#F1F5F9;">{s}</div>', unsafe_allow_html=True)
                    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        else:
            st.info("No structured financial metrics detected.")
        st.markdown('</div>', unsafe_allow_html=True)


elif page == "Fact Check":
    if not has_results:
        st.warning("Upload and analyze a file first from the Dashboard or Audio tab.")
    else:
        data = st.session_state.results
        st.markdown('<div class="section-header">Claim Verification</div>', unsafe_allow_html=True)
        st.markdown('<div class="card"><div class="card-title"><i class="ti ti-shield-check"></i> Cross-reference Against Yahoo Finance</div>', unsafe_allow_html=True)

        ticker = st.text_input("Enter stock ticker", placeholder="AAPL, MSFT, GOOGL, TSLA", label_visibility="collapsed")
        if st.button("Verify Claims") and ticker:
            with st.spinner(f"Fetching real financials for {ticker.upper()}..."):
                try:
                    res = requests.post(f"{BACKEND}/factcheck", json={
                        "ticker": ticker.upper(),
                        "text":   data.get("summary", "") + " " + " ".join(
                            s for sents in data.get("financial_metrics", {}).values() for s in sents),
                    }, timeout=60)
                    if res.status_code == 200:
                        result = res.json()
                        st.session_state.fact_check = result
                        if "error" not in result:
                            real = result.get("real_financials", {})
                            if real:
                                st.markdown('<div class="col-label">Real Yahoo Finance Data</div>', unsafe_allow_html=True)
                                cols = st.columns(len(real))
                                for i, (k, v) in enumerate(real.items()):
                                    cols[i].metric(k.replace("_", " ").title(), v)
                            st.markdown(f"""
                            <div style="display:flex;gap:16px;margin:16px 0;">
                                <div style="background:rgba(29,185,154,.1);border:1px solid rgba(29,185,154,.3);border-radius:8px;padding:12px 20px;text-align:center;">
                                    <div style="color:#4DD9C0;font-size:11px;text-transform:uppercase;">Verified</div>
                                    <div style="color:#1DB99A;font-size:24px;font-weight:700;">{result.get('verified',0)}</div>
                                </div>
                                <div style="background:rgba(239,159,39,.1);border:1px solid rgba(239,159,39,.3);border-radius:8px;padding:12px 20px;text-align:center;">
                                    <div style="color:#F0B429;font-size:11px;text-transform:uppercase;">Flagged</div>
                                    <div style="color:#EF9F27;font-size:24px;font-weight:700;">{result.get('flagged',0)}</div>
                                </div>
                                <div style="background:rgba(139,124,246,.1);border:1px solid rgba(139,124,246,.3);border-radius:8px;padding:12px 20px;text-align:center;">
                                    <div style="color:#A89CF7;font-size:11px;text-transform:uppercase;">Total Claims</div>
                                    <div style="color:#8B7CF6;font-size:24px;font-weight:700;">{result.get('total_claims',0)}</div>
                                </div>
                            </div>""", unsafe_allow_html=True)
                            for r in result.get("results", []):
                                col = "#1DB99A" if r["status"] == "verified" else ("#EF9F27" if r["status"] == "close" else "#EF4444")
                                ico = "ti-circle-check" if r["status"] == "verified" else ("ti-circle-minus" if r["status"] == "close" else "ti-circle-x")
                                st.markdown(f"""
                                <div style="background:rgba(255,255,255,.03);border:1px solid {col}33;border-radius:8px;padding:12px 16px;margin-bottom:8px;">
                                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
                                        <i class="ti {ico}" style="color:{col};font-size:16px;"></i>
                                        <span style="color:{col};font-size:12px;font-weight:600;text-transform:uppercase;">{r['status']}</span>
                                        {f'<span style="color:#94A3B8;font-size:12px;">Yahoo Finance: {r["real_value"]}</span>' if r.get("real_value") else ''}
                                    </div>
                                    <div style="color:#CBD5E1;font-size:13px;">{r['claim']}</div>
                                </div>""", unsafe_allow_html=True)
                        else:
                            st.error(f"Error: {result.get('error')}")
                except Exception as e:
                    st.error(f"Error: {e}")
        st.markdown('</div>', unsafe_allow_html=True)


elif page == "Summary":
    if not has_results:
        st.warning("Upload and analyze a file first from the Dashboard or Audio tab.")
    else:
        data = st.session_state.results
        st.markdown('<div class="section-header">Executive Summary</div>', unsafe_allow_html=True)
        st.markdown(f"""<div class="card">
            <div class="card-title"><i class="ti ti-file-analytics"></i> Key Financial Insights</div>
            <div class="sumbox">{data["summary"]}</div>
            <p style="font-size:11px;color:#475569;margin-top:12px;margin-bottom:0;">
                Extracted from {data["characters"]:,} characters of transcript text</p>
        </div>""", unsafe_allow_html=True)
        if data.get("warning"):
            st.warning(data["warning"])


elif page == "Risk Flags":
    if not has_results:
        st.warning("Upload and analyze a file first from the Dashboard or Audio tab.")
    else:
        data  = st.session_state.results
        risks = data.get("risks", [])
        st.markdown('<div class="section-header">Risk Flag Detection</div>', unsafe_allow_html=True)
        st.markdown('<div class="card"><div class="card-title"><i class="ti ti-shield-exclamation"></i> Risk Language Detected</div>', unsafe_allow_html=True)
        if risks and risks[0] != "No significant risk language detected.":
            for r in risks:
                st.markdown(f'<div class="risk-row"><i class="ti ti-alert-circle"></i><span>{r}</span></div>', unsafe_allow_html=True)
        else:
            st.success("No significant risk language detected.")
        st.markdown('</div>', unsafe_allow_html=True)


elif page == "Brief":
    if not has_results:
        st.warning("Upload and analyze a file first from the Dashboard or Audio tab.")
    else:
        data = st.session_state.results
        st.markdown('<div class="section-header">Analyst Brief</div>', unsafe_allow_html=True)
        st.markdown('<div class="card"><div class="card-title"><i class="ti ti-file-export"></i> Generate Institutional Analyst Brief</div>', unsafe_allow_html=True)

        company = st.text_input("Company name", placeholder="Apple Inc, Microsoft Corp, HBL...", label_visibility="collapsed")
        if st.button("Generate Brief") and company:
            with st.spinner("Generating with Groq LLaMA 3.1..."):
                try:
                    fact_check = st.session_state.fact_check or {}
                    res = requests.post(f"{BACKEND}/generate-brief", json={
                        "company":            company,
                        "summary":            data.get("summary", ""),
                        "sentiment":          data.get("sentiment", {}),
                        "risks":              data.get("risks", []),
                        "financial_metrics":  data.get("financial_metrics", {}),
                        "speaker_sentiment":  data.get("speaker_sentiment", {}),
                        "fact_check_results": fact_check.get("results", []),
                    }, timeout=60)
                    if res.status_code == 200:
                        result = res.json()
                        if "error" not in result:
                            st.session_state.brief         = result["brief"]
                            st.session_state.brief_company = company
                        else:
                            st.error(f"Error: {result['error']}")
                except Exception as e:
                    st.error(f"Error: {e}")

        if st.session_state.brief:
            st.markdown(f"""
            <div style="background:rgba(29,185,154,.06);border:1px solid rgba(29,185,154,.2);
                        border-radius:12px;padding:20px 24px;margin:16px 0;
                        font-size:14px;color:#F1F5F9;line-height:1.8;white-space:pre-wrap;">{st.session_state.brief}
            </div>""", unsafe_allow_html=True)

            if st.button("Download as PDF"):
                with st.spinner("Generating PDF..."):
                    try:
                        res = requests.post(f"{BACKEND}/export-brief", json={
                            "brief":   st.session_state.brief,
                            "company": st.session_state.brief_company or company,
                        }, timeout=30)
                        if res.status_code == 200:
                            st.download_button(
                                label="Click to save PDF", data=res.content,
                                file_name=f"brief_{(st.session_state.brief_company or company).replace(' ','_')}.pdf",
                                mime="application/pdf",
                            )
                        else:
                            st.error("PDF generation failed")
                    except Exception as e:
                        st.error(f"Error: {e}")
        st.markdown('</div>', unsafe_allow_html=True)


elif page == "Ask":
    if not has_results:
        st.warning("Upload and analyze a file first from the Dashboard or Audio tab.")
    else:
        st.markdown('<div class="section-header">RAG Question Answering</div>', unsafe_allow_html=True)
        st.markdown('<div class="card"><div class="card-title"><i class="ti ti-message-bolt"></i> Ask Anything About This Transcript</div>', unsafe_allow_html=True)
        st.markdown('<p style="font-size:13px;color:#64748B;margin-bottom:16px;">Powered by ChromaDB vector search + Groq LLaMA 3.1</p>', unsafe_allow_html=True)

        question = st.text_input("Your question",
            placeholder="What was the revenue? What is the guidance for next quarter?",
            label_visibility="collapsed")
        if st.button("Get Answer") and question:
            with st.spinner("Searching transcript and generating answer..."):
                try:
                    res = requests.post(f"{BACKEND}/ask", json={"question": question}, timeout=60)
                    if res.status_code == 200:
                        result = res.json()
                        st.markdown(f'<div class="ansbox">{result["answer"]}</div>', unsafe_allow_html=True)
                        if result.get("sources"):
                            with st.expander("View source chunks from transcript"):
                                for i, src in enumerate(result["sources"]):
                                    st.markdown(f"**Chunk {i+1}:** {src[:200]}...")
                    else:
                        st.error(f"Error: {res.text}")
                except Exception as e:
                    st.error(f"Error: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:1.5rem 0 .5rem;
            border-top:1px solid rgba(255,255,255,.05);margin-top:2rem;">
    <p style="color:#1DB99A;font-weight:700;font-size:.85rem;margin:.2rem 0;letter-spacing:.04em;">FULL STACK FINANCE</p>
    <p style="color:#2D3A52;font-size:.72rem;margin:.2rem 0;">spaCy NER · FinBERT · LangChain RAG · ChromaDB · Groq LLaMA 3.1 · Docker</p>
</div>""", unsafe_allow_html=True)