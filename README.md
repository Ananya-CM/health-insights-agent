# 🏥 Health Insights Agent

An AI-powered web application that analyzes medical reports — blood tests, thyroid profiles, ultrasound reports, and scanned images — and provides personalized health insights using large language models.

> **Disclaimer:** This tool is for educational and informational purposes only. It does not replace professional medical advice. Always consult a qualified healthcare provider.

---

## ✨ Features

- 📄 Upload reports as **PDF, JPG, PNG** or use the built-in sample report
- 🖼️ **AI Vision** — reads scanned/photographed reports using LLaMA 4 Vision
- 🩺 Analyzes **all report types** — blood tests, thyroid profiles, ultrasound, immunology
- 🤖 AI-driven health analysis using Groq-hosted LLaMA models
- 💬 Follow-up Q&A on your report using RAG (retrieval-augmented generation)
- 🔐 User authentication and session management via Supabase
- 💾 Persistent chat session history
- 🔁 Automatic model fallback (4-tier: LLaMA 4 → LLaMA 3.3 → LLaMA 3.1 → LLaMA3)
- 🔬 Vision model fallback (LLaMA 4 Scout → LLaMA 3.2 90B → LLaMA 3.2 11B)

---

## 🛠️ Tech Stack

| Layer          | Technology                                    |
| -------------- | --------------------------------------------- |
| Frontend       | Streamlit                                     |
| LLM API        | Groq (LLaMA models)                           |
| Vision AI      | Groq Vision (LLaMA 4 Scout, LLaMA 3.2 Vision) |
| Auth & DB      | Supabase (PostgreSQL)                         |
| PDF Processing | PDFPlumber                                    |
| Image OCR      | Groq Vision API (no Tesseract needed)         |
| RAG            | LangChain + FAISS + HuggingFace Embeddings    |
| Embeddings     | all-MiniLM-L6-v2 (Sentence Transformers)      |

---

## 📋 Supported Report Types

| Report Type                        | Input Format | How it Works           |
| ---------------------------------- | ------------ | ---------------------- |
| Blood Test (CBC, Lipid, Metabolic) | PDF or Image | PDFPlumber / Vision AI |
| Thyroid Profile (T3, T4, TSH)      | PDF or Image | PDFPlumber / Vision AI |
| Ultrasound / Ultrasonography       | PDF or Image | PDFPlumber / Vision AI |
| Scanned / Photographed Reports     | JPG, PNG     | Vision AI (LLaMA 4)    |
| Immunology Reports                 | PDF or Image | PDFPlumber / Vision AI |

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Ananya-CM/health-insights-agent.git
cd health-insights-agent
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up Supabase

- Create a project at [supabase.com](https://supabase.com)
- Go to **SQL Editor** and run the contents of `public/db/schema.sql`
- Also run the RLS policies (see below)
- Copy your **Project URL** and **anon key**

#### Required RLS Policies (run in Supabase SQL Editor)

```sql
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow insert" ON users FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow select" ON users FOR SELECT USING (auth.uid() = id);

ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Sessions policy" ON chat_sessions FOR ALL
  USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Messages policy" ON chat_messages FOR ALL
  USING (session_id IN (SELECT id FROM chat_sessions WHERE user_id = auth.uid()))
  WITH CHECK (session_id IN (SELECT id FROM chat_sessions WHERE user_id = auth.uid()));
```

### 4. Get a Groq API key

- Sign up at [console.groq.com](https://console.groq.com)
- Create an API key

### 5. Configure secrets

Create `.streamlit/secrets.toml` (use the provided example file):

```toml
GROQ_API_KEY = "your_groq_api_key"
SUPABASE_URL = "your_supabase_url"
SUPABASE_KEY = "your_supabase_anon_key"
```

### 6. Run the app

```bash
streamlit run src/main.py
```

---

## ☁️ Deployment (Streamlit Cloud)

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
2. Click **New app**
3. Fill in:
   - Repository: `Ananya-CM/health-insights-agent`
   - Branch: `main`
   - Main file path: `src/main.py`
4. Click **Advanced settings** → paste your secrets in the Secrets box
5. Click **Deploy**

---

## 📁 Project Structure

```
health-insights-agent/
├── src/
│   ├── main.py                    # App entry point
│   ├── agents/
│   │   ├── analysis_agent.py      # Report analysis + rate limiting + in-context learning
│   │   ├── chat_agent.py          # RAG-based follow-up chat
│   │   └── model_manager.py       # LLM selection + 4-tier fallback
│   ├── auth/
│   │   ├── auth_service.py        # Supabase auth & user data
│   │   └── session_manager.py     # Session lifecycle management
│   ├── components/
│   │   ├── analysis_form.py       # Report upload (PDF + Image) & analysis UI
│   │   ├── auth_pages.py          # Login/signup pages
│   │   ├── sidebar.py             # Session list & controls
│   │   └── footer.py              # App footer
│   ├── config/
│   │   ├── app_config.py          # App-wide settings
│   │   ├── prompts.py             # LLM system prompts (all report types)
│   │   └── sample_data.py         # Sample blood report
│   ├── services/
│   │   └── ai_service.py          # AI service layer
│   └── utils/
│       ├── pdf_extractor.py       # PDF + Image extraction (Vision AI)
│       └── validators.py          # Input validation (PDF, image, medical content)
└── public/
    └── db/
        └── schema.sql             # Supabase database schema
```

---

## 🤖 AI Model Architecture

### Text Analysis (Report → Insights)

```
Report Text → System Prompt → Groq LLM → Health Analysis

Model Fallback Chain:
1. LLaMA 4 Maverick 17B  (primary)
2. LLaMA 3.3 70B         (fallback 1)
3. LLaMA 3.1 8B          (fallback 2)
4. LLaMA3 70B            (fallback 3)
```

### Vision AI (Image/Scan → Text → Insights)

```
Scanned Report Image → Groq Vision API → Extracted Text → LLM Analysis

Vision Model Fallback Chain:
1. LLaMA 4 Scout 17B         (primary vision)
2. LLaMA 3.2 90B Vision      (fallback 1)
3. LLaMA 3.2 11B Vision      (fallback 2)
```

### RAG Pipeline (Follow-up Q&A)

```
Report Text → Sentence Transformer → FAISS Vector Store
User Question → Semantic Search → Relevant Chunks → LLaMA Answer
```

---

## ⚠️ Medical Disclaimer

All analysis generated by this application is AI-produced and intended for informational purposes only. It does not constitute medical advice, diagnosis, or treatment. Always consult a licensed healthcare professional for medical decisions.
