<div align="center">

# 🌱 CropSense

### AI-Powered Crop Disease Detection for Farmers

[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org)
[![ONNX](https://img.shields.io/badge/ONNX-005CED?style=for-the-badge&logo=onnx&logoColor=white)](https://onnx.ai)
[![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain.com)
[![Gemini](https://img.shields.io/badge/Gemini_2.5_Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)
[![Telegram](https://img.shields.io/badge/Telegram_Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

<br/>

**A farmer takes a photo of their crop on a basic smartphone.**
**CropSense detects the disease, explains the treatment in Telugu or English, and predicts the spread risk for the next 7 days — all in under 10 seconds.**

[🚀 Try the Bot](#try-the-bot) · [📸 Screenshots](#screenshots) · [⚡ Quick Start](#quick-start) · [🗺 Roadmap](#roadmap)

<br/>

> Built for 6 million farmers in Telangana, India.
> No app to install. Just send a photo on Telegram.

</div>

---

## 🌾 The Problem

India loses **₹50,000 crore worth of crops every year** to preventable diseases. Farmers in rural Telangana face three barriers:

- **No access** to agronomists — the nearest expert is hours away
- **No internet literacy** — complex apps are unusable for most farmers
- **No early warning** — by the time a disease is visible, 30–40% of the crop is already lost

CropSense solves all three with a simple Telegram message.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📸 **Instant disease detection** | Send a crop photo → get disease name, confidence, and top-3 predictions in seconds |
| 🧠 **Edge AI model** | EfficientNet-B0 quantized to INT8 via ONNX Runtime — runs offline, no GPU needed |
| 💊 **RAG treatment advisor** | LangChain + FAISS over ICAR and Agropedia knowledge base with checksum-verified FAISS artifacts |
| 🗣 **Telugu + English support** | Farmer-friendly response in their native language, zero jargon |
| ⛅ **7-day spread risk forecast** | Rule-based risk scoring predicts spread risk from local weather (temperature, humidity, rainfall) |
| 📱 **Zero install** | Works on any phone via Telegram — no app download, no registration |
| 📊 **Analytics dashboard** | Real-time district-wise disease outbreak map for researchers and agriculture officers |
| 🧭 **Low-confidence guidance** | If confidence is low, bot asks for a retake with clear photo tips (daylight, focus, single leaf) |
| 🗄️ **Persistent session state** | Redis-backed user/session state (with in-memory fallback) for restart-safe conversations |

---

## 🌿 Supported Crops & Diseases

Current model classes in this repository cover PlantVillage-style labels including:

- 🍎 Apple
- 🌽 Corn (Maize)
- 🍇 Grape
- 🍑 Peach
- 🌶 Bell Pepper
- 🥔 Potato
- 🍅 Tomato

Both disease and healthy classes are supported (see `model/class_names.json` for exact labels).

---

## 🏗 System Architecture

```
Farmer sends photo (Telegram)
         │
         ▼
  Telegram Bot (python-telegram-bot, async)
         │
         ├──► Edge AI Model (EfficientNet-B0 + ONNX INT8)
         │         └── Disease name + confidence score
         │
         ├──► RAG Advisor (LangChain + FAISS + ICAR knowledge base)
         │         └── Treatment steps + pesticide names + dosage
         │
         ├──► Weather Forecaster (OpenWeatherMap + rule-based risk scoring)
         │         └── 7-day spread risk: Low / Medium / High
         │
         └──► Multilingual LLM (Gemini 2.5 Flash)
                   └── Final response in Telugu or English
                             │
                             ▼
                   Farmer receives reply (~10 seconds)
                             │
                             ▼
               PostgreSQL logs detection for analytics
                             │
                             ▼
               Streamlit dashboard — district outbreak map
```

---

## 🛠 Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **CV Model** | EfficientNet-B0 (PyTorch) | Fine-tuned on PlantVillage-style crop disease classes |
| **Edge Optimization** | ONNX Runtime + INT8 quantization | Offline inference, low latency, no GPU |
| **RAG Pipeline** | LangChain + FAISS | Retrieve treatment info from crop disease knowledge base |
| **Embeddings** | sentence-transformers `all-MiniLM-L6-v2` | Local, offline, zero API cost |
| **LLM** | Gemini 2.5 Flash | Telugu/English response generation |
| **Forecasting** | Rule-based model + OpenWeatherMap | 7-day disease spread risk prediction |
| **Bot Interface** | python-telegram-bot (async) | Zero-install farmer interface |
| **Database** | PostgreSQL | Detection logging + analytics |
| **Dashboard** | Streamlit + Plotly | District-wise outbreak visualization |
| **State Store** | Redis (+ memory fallback) | Persistent conversation/session state |
| **Observability** | Structured JSON logs | Request IDs, stage timings, timeout/fallback events |
| **Deployment** | Render | Free cloud hosting |

---

## 📁 Project Structure

```
CropSense/
├── model/
│   ├── train.py              ← EfficientNet-B0 fine-tuning on PlantVillage
│   ├── export_onnx.py        ← ONNX export + INT8 quantization
│   ├── inference.py          ← ONNX Runtime inference wrapper
│   └── crop_disease.onnx     ← quantized model (after training)
├── rag/
│   ├── build_kb.py           ← build FAISS knowledge base from PDFs
│   ├── retriever.py          ← query treatment info by disease name
│   └── knowledge_base/       ← ICAR PDFs + Agropedia disease docs
├── forecast/
│   ├── weather.py            ← OpenWeatherMap 7-day forecast fetcher
│   └── risk_model.py         ← rule-based spread risk scoring
├── bot/
│   ├── bot.py                ← main Telegram bot entry point
│   ├── handlers.py           ← photo, text, command handlers
│   └── pipeline.py           ← orchestrates all modules end-to-end
├── dashboard/
│   └── app.py                ← Streamlit analytics dashboard
├── db/
│   └── models.py             ← PostgreSQL schema + queries
├── utils/
│   ├── language.py           ← Telugu/English system prompts
│   ├── gemini.py             ← Gemini client with timeout + fallback
│   ├── voice.py              ← speech-to-text + text-to-speech
│   ├── fertilizer_advisor.py ← fertilizer guidance
│   ├── scheme_advisor.py     ← government scheme guidance
│   ├── crop_calendar.py      ← crop calendar guidance
│   ├── mandi_prices.py       ← mandi price lookup
│   ├── state_store.py        ← Redis-backed state management
│   ├── observability.py      ← request IDs + structured telemetry logs
│   └── alert_manager.py      ← community outbreak alert messaging
├── tests/
│   ├── test_gemini.py        ← timeout/retry/fallback tests
│   ├── test_pipeline_integration.py ← pipeline + DB-log integration tests
│   ├── test_risk_model.py    ← weather risk scoring tests
│   └── test_weather.py       ← district resolution tests
├── data/                     ← PlantVillage dataset (not committed)
├── .env                      ← API keys (never committed)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## ⚡ Quick Start

### Prerequisites
- Python 3.10+
- [Gemini API key](https://aistudio.google.com/apikey) (free)
- [Telegram Bot token](https://t.me/BotFather) (free)
- [OpenWeatherMap API key](https://openweathermap.org/api) (free)
- [Kaggle account](https://kaggle.com) for dataset download

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/Venuenugula/CropSense.git
cd CropSense

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# 5. Download dataset
kaggle datasets download -d abdallahalidev/plantvillage-dataset
unzip plantvillage-dataset.zip -d data/

# 6. Train and export model
python model/train.py
python model/export_onnx.py

# 7. Build RAG knowledge base
python rag/build_kb.py

# 8. Run the bot
python -m bot.bot
```

### Environment Variables

```env
TELEGRAM_BOT_TOKEN=your_telegram_token
GEMINI_API_KEY=your_gemini_key
OPENWEATHER_API_KEY=your_openweather_key
DATABASE_URL=postgresql://user:pass@localhost:5432/cropsense
GROQ_API_KEY=your_groq_key
REDIS_URL=redis://localhost:6379/0
# Optional (improves model download rate limits)
HF_TOKEN=your_huggingface_token
```

### Test Commands

```bash
# Run all tests
python -m pytest -q
```

---

## 📊 Dashboard

The analytics dashboard shows:
- District-wise disease outbreak heatmap (Telangana)
- Most detected diseases this week
- Total farmers helped
- Detection confidence trends
- 7-day spread risk by region
- Official hotspot scatter + district priority table
- Intervention workflow tracker for agriculture officers
- Exportable CSV reports (hotspots + interventions)
- Monitoring panel (helpful feedback rate, uncertainty rate, confidence distribution)

```bash
streamlit run dashboard/app.py
```

---

## ✅ Reliability & Stability Updates

Recent production hardening updates included in this codebase:

- **Event-loop-safe scheduler**
  - Community outbreak alerts now use `python-telegram-bot` `job_queue` during bot init (instead of starting APScheduler before a running loop).
- **Non-blocking heavy pipeline execution**
  - Image analysis flow offloads `run_pipeline(...)` from async handlers using `asyncio.to_thread(...)`.
- **Non-blocking voice LLM path**
  - Voice Q&A generation also runs via `asyncio.to_thread(...)` to keep the bot responsive under slow LLM calls.
- **Gemini timeout + graceful fallback**
  - Shared Gemini client now enforces request timeout and returns a safe fallback response if the model is slow/unavailable.
- **Gemini SDK migration**
  - Main response generation migrated from deprecated `google.generativeai` usage to `google.genai`.
- **Dependency/runtime alignment**
  - Added missing runtime dependencies (`gTTS`, `edge-tts`, `groq`) and enabled `python-telegram-bot[job-queue]`.
- **Safer/weather network updates**
  - OpenWeather endpoints switched from HTTP to HTTPS.
- **DB query reliability fix**
  - Time-window SQL queries now use robust interval parameterization.
- **Safer FAISS loading (Milestone A)**
  - Removed dangerous deserialization path.
  - Added checksum-verified FAISS artifacts (`index.faiss`, `metadata.json`, `checksums.json`).
- **Automated test foundation (Milestone A)**
  - Added `pytest` suite for pipeline, weather/risk logic, and Gemini timeout/retry fallback behavior.
- **Persistent state (Milestone B)**
  - Replaced in-memory conversational stores with Redis-backed state (`REDIS_URL`) and safe memory fallback.
  - Binary payloads (like uploaded image bytes) are safely encoded/decoded for Redis storage.
- **Async external I/O hardening (Milestone B)**
  - Offloaded blocking scheme/mandi/fertilizer/voice operations to background threads in async handlers.
- **Observability instrumentation (Milestone C)**
  - Added structured JSON logs with `request_id` and stage timings (`pipeline_ms`, `gemini_ms`).
  - Added explicit events for `gemini_timeout`, `gemini_fallback`, and pipeline errors/success.
- **User trust UX upgrades (Milestone C)**
  - Added confidence-threshold behavior for uncertain predictions.
  - Added top-3 confidence margin and photo-retake guidance in user responses.

These updates significantly reduce event-loop blocking, startup/runtime failures, and user-facing hangs during external API slowdowns.

---

## 🌐 Try the Bot

> Coming soon — link will be added after deployment

Send any of these to get started:
```
/start          → Welcome message + language selection
/telugu         → తెలుగు
/english        → English
/help           → How to use CropSense
/profile        → Save farmer profile (district/crop/acres/irrigation)
/subscribe      → Subscribe to district+crop outbreak alerts
/checklist      → Weekly action checklist based on profile
/fertilizer     → Fertilizer/medicine advisor
/schemes        → Government schemes advisor
/calendar       → Crop calendar guidance
/alerts         → Community outbreak alerts
/price          → Mandi prices
📸 Send photo   → Instant disease detection
🎤 Send voice   → Voice Q&A + voice reply
```

**Example farmer interaction:**

```
Farmer: [sends photo of rice crop]

CropSense: 🌾 పంట వ్యాధి గుర్తింపు (Crop Disease Detection)

వ్యాధి: Rice Blast (బ్లాస్ట్ వ్యాధి)
నమ్మకం: 94%

చికిత్స:
1. Tricyclazole 75% WP @ 0.6g/L నీటిలో కలిపి పిచికారీ చేయండి
2. 10 రోజుల తర్వాత మళ్ళీ పిచికారీ చేయండి
3. పొలంలో నీరు నిల్వ ఉండకుండా చూసుకోండి

⛅ వ్యాప్తి ప్రమాదం (7 రోజులు): 🔴 అధికం
వర్షం + అధిక తేమ కారణంగా వ్యాధి వ్యాపించే అవకాశం ఎక్కువ.
వెంటనే పిచికారీ చేయండి.
```

---

## 🗺 Current Status & Next Roadmap

### Implemented
- [x] Telegram bot for image-based crop disease detection
- [x] ONNX inference pipeline integration
- [x] RAG-based treatment retrieval
- [x] Telugu/English response generation
- [x] Voice input + voice output support
- [x] Weather-based 7-day spread risk scoring
- [x] PostgreSQL logging + Streamlit dashboard
- [x] Community alert scheduler and district-level alerts
- [x] Reliability hardening (timeouts, non-blocking pipeline paths)
- [x] Safer FAISS loading with artifact checksum verification
- [x] Automated pytest test foundation
- [x] Redis-backed persistent session/conversation state
- [x] Structured observability logs with request IDs and latency metrics
- [x] Confidence-threshold UX with photo retake guidance
- [x] Feedback buttons and feedback logging for diagnosis usefulness
- [x] Farmer profile, alert subscription, and weekly checklist bot flows
- [x] Official hotspot dashboard, intervention workflow, and CSV exports

### Render deployment (webhook)

- **Hugging Face model (ONNX):** [VenuEnugula/cropsense_diseasedetection](https://huggingface.co/VenuEnugula/cropsense_diseasedetection)
- **Start command:** `bash start_bot.sh` — downloads `crop_disease.onnx` and `class_names.json` from that repo (unless already present), optionally pulls `rag/faiss_index/*` from the same repo if you upload them there, then runs `python3 scripts/validate_faiss.py` and starts `python3 -m bot.bot`.
- **FAISS:** Either commit `rag/faiss_index/` (`index.faiss`, `metadata.json`, `checksums.json`) or upload those files under `rag/faiss_index/` on Hugging Face. Set `DOWNLOAD_FAISS_FROM_HF=0` if artifacts are only in git. Build locally with `python rag/build_kb.py` if needed.
- **Env:** `TELEGRAM_BOT_TOKEN`, `WEBHOOK_URL` (e.g. `https://your-service.onrender.com`), `PORT` (Render sets this), plus `DATABASE_URL`, `REDIS_URL`, and API keys as in your `.env`. Use `HF_TOKEN` if the HF repo is private.

### Planned
- [ ] Expand crop/disease coverage and local KB depth
- [ ] Add WhatsApp/SMS channel support
- [ ] Add metrics dashboard + alert thresholds (Prometheus/Grafana)
- [ ] Add CI pipeline for tests and lint checks

---


## 🤝 Contributing

```bash
git checkout -b feature/your-feature-name
git commit -m "feat: your feature description"
git push origin feature/your-feature-name
# Open a Pull Request to develop branch
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch naming conventions.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

### Built with ❤️ for farmers of Telangana by Venu Enugula

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/venu-enugula-mlengineer)
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Venuenugula)
[![PyPI](https://img.shields.io/badge/PyPI-dsa--daa--kit-3775A9?style=for-the-badge&logo=pypi&logoColor=white)](https://pypi.org/project/dsa-daa-kit/)

*If this project helps even one farmer save their crop, it's worth it.*
*Please give it a ⭐ on GitHub to help it reach more people.*

</div>
