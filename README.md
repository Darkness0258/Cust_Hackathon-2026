# 🔱 TRIDENT — AI-Powered Bid & Proposal Response Engine

> Built for **SE Hackathon 2026** at Capital University of Science and Technology (CUST), Islamabad.

TRIDENT automates the entire government tender response workflow — from raw PDF ingestion to a fully drafted, compliance-checked proposal — in under 90 seconds.

---

## 🚀 Live Demo

🌐 **Frontend:** [tridentsystem.vercel.app](https://tridentsystem.vercel.app/)  
📁 **Frontend Repo:** [github.com/Fahad-sec/Trident](https://github.com/Fahad-sec/Trident)

---

## ⚡ What It Does

Upload any government RFP PDF and TRIDENT will:

1. Extract all mandatory requirements using Claude AI
2. Match each requirement against TEKROWE's capability library (RAG)
3. Calculate a win probability score using a 4-factor algorithm
4. Generate a full formal proposal narrative
5. Produce 5 strategic directives for the bid team
6. Display everything on a live dashboard

---

## 🧠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python) |
| AI / LLM | Claude via OpenRouter |
| RAG Engine | sentence-transformers (all-MiniLM-L6-v2) |
| PDF Parsing | PyMuPDF (fitz) |
| Database | Supabase (PostgreSQL) |
| Frontend | Vanilla JS + Tailwind CSS |
| Deployment | Vercel + ngrok |
| Data | Excel — Bid History + Capability Library |

---

## 🏗️ Architecture

```
PDF Upload → parser.py → claude_client.py (extract requirements)
          → rag_engine.py (compliance check)
          → scoring.py (win probability)
          → proposal_engine.py (3 Claude calls)
          → Supabase (save result)
          → Frontend (hydrate dashboard)
```

---

## 📁 Project Structure

```
backend/
├── main.py              # FastAPI app, /analyze endpoint
├── parser.py            # PDF → clean text
├── claude_client.py     # All Claude API calls
├── rag_engine.py        # Semantic compliance matching
├── scoring.py           # 4-factor win probability
├── proposal_engine.py   # Proposal orchestration + DOCX export
├── data_loader.py       # Excel dataset loader
└── .env                 # API keys (not committed)

frontend/
├── index.html           # Dashboard UI
├── app.js               # Upload, hydration, animations
└── mockData.js          # Supabase fetch layer
```

---

## 📊 Scoring Algorithm

| Factor | Max Points |
|--------|-----------|
| Compliance Rate | 35 pts |
| Gaps Count | 25 pts |
| Sector Win Rate | 20 pts |
| Budget Range | 20 pts |
| **Total** | **100 pts** |

- ≥ 65 → **GO DECISION**
- ≥ 50 → **REVIEW DECISION**
- < 50 → **NO-GO DECISION**

---

## 🔧 Run Locally

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Environment Variables
Create a `.env` file:
```env
ANTHROPIC_API_KEY=your_openrouter_key
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
DATASET_PATH=Problem_1_Sample_Datasets__TEKROWE_.xlsx
```

### Frontend
Open `index.html` directly or deploy to Vercel.  
Update `BACKEND_URL` in `app.js` to your ngrok/deployed backend URL.

---

## 👥 Team

| Role | Name |
|------|------|
| Backend / AI Pipeline | Muhammad Hamza Nadeem (Darkness) |
| Frontend / UI | Fahad ([github.com/Fahad-sec](https://github.com/Fahad-sec)) |

---

## 📄 License

MIT
