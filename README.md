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
| 📸 **Instant disease detection** | Send a crop photo → get the disease name and confidence score in seconds |
| 🧠 **Edge AI model** | EfficientNet-B0 quantized to INT8 via ONNX Runtime — runs offline, no GPU needed |
| 💊 **RAG treatment advisor** | LangChain + FAISS over ICAR and Agropedia knowledge base — specific pesticide names, dosage, prevention |
| 🗣 **Telugu + English support** | Farmer-friendly response in their native language, zero jargon |
| ⛅ **7-day spread risk forecast** | XGBoost model predicts disease spread risk based on local weather — warns before it spreads |
| 📱 **Zero install** | Works on any phone via Telegram — no app download, no registration |
| 📊 **Analytics dashboard** | Real-time district-wise disease outbreak map for researchers and agriculture officers |

---

## 🌿 Supported Crops & Diseases

| Crop | Diseases Detected |
|---|---|
| 🌾 Rice | Blast, Brown spot, Bacterial blight, Sheath blight |
| 🌿 Cotton | Bacterial blight, Leaf curl, Alternaria leaf spot |
| 🌽 Maize | Common rust, Gray leaf spot, Northern leaf blight |
| 🥜 Groundnut | Early leaf spot, Late leaf spot, Rosette |

> Trained on PlantVillage dataset (54,000+ images, 38 disease classes)

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
         ├──► Weather Forecaster (OpenWeatherMap + XGBoost)
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
| **CV Model** | EfficientNet-B0 (PyTorch) | Fine-tuned on PlantVillage for 20 disease classes |
| **Edge Optimization** | ONNX Runtime + INT8 quantization | Offline inference, low latency, no GPU |
| **RAG Pipeline** | LangChain + FAISS | Retrieve treatment info from crop disease knowledge base |
| **Embeddings** | sentence-transformers `all-MiniLM-L6-v2` | Local, offline, zero API cost |
| **LLM** | Gemini 2.5 Flash | Telugu/English response generation |
| **Forecasting** | XGBoost + OpenWeatherMap | 7-day disease spread risk prediction |
| **Bot Interface** | python-telegram-bot (async) | Zero-install farmer interface |
| **Database** | PostgreSQL | Detection logging + analytics |
| **Dashboard** | Streamlit + Plotly | District-wise outbreak visualization |
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
│   └── risk_model.py         ← XGBoost spread risk classifier
├── bot/
│   ├── bot.py                ← main Telegram bot entry point
│   ├── handlers.py           ← photo, text, command handlers
│   └── pipeline.py           ← orchestrates all modules end-to-end
├── dashboard/
│   └── app.py                ← Streamlit analytics dashboard
├── db/
│   └── models.py             ← PostgreSQL schema + queries
├── utils/
│   ├── language.py           ← Telugu/English detection + prompts
│   └── gemini.py             ← LLM response generator
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
python bot/bot.py
```

### Environment Variables

```env
TELEGRAM_BOT_TOKEN=your_telegram_token
GEMINI_API_KEY=your_gemini_key
OPENWEATHER_API_KEY=your_openweather_key
DATABASE_URL=postgresql://user:pass@localhost:5432/cropsense
```

---

## 📊 Dashboard

The analytics dashboard shows:
- District-wise disease outbreak heatmap (Telangana)
- Most detected diseases this week
- Total farmers helped
- Detection confidence trends
- 7-day spread risk by region

```bash
streamlit run dashboard/app.py
```

---

## 🌐 Try the Bot

> Coming soon — link will be added after deployment

Send any of these to get started:
```
/start          → Welcome message + language selection
/help           → How to use CropSense
/language       → Switch between Telugu and English
📸 Send photo   → Instant disease detection
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

## 🗺 Roadmap

- [x] Project architecture design
- [x] Git flow setup
- [ ] Phase 1: EfficientNet-B0 training on PlantVillage
- [ ] Phase 2: ONNX export + INT8 quantization
- [ ] Phase 3: RAG knowledge base (ICAR + Agropedia)
- [ ] Phase 4: Telugu/English LLM response generation
- [ ] Phase 5: Weather spread risk forecasting
- [ ] Phase 6: Telegram bot integration
- [ ] Phase 7: Streamlit analytics dashboard
- [ ] Phase 8: Render deployment
- [ ] WhatsApp Business API integration
- [ ] Support for 10+ more crops
- [ ] Voice message support (farmer speaks, bot responds)
- [ ] SMS fallback for feature phones

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
