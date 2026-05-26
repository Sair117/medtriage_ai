# 🏥 MedTriage AI

An AI-powered medical intake triage bot that helps patients describe their symptoms, assesses urgency, collects intake information, and routes them to the appropriate department.

**Built for:** Clinic front-desk automation  
**Live Demo:** [Coming soon — deploy to Render]

---

## Features

- **Conversational Triage** — Natural language symptom collection with intelligent follow-up questions
- **Urgency Classification** — 🔴 Emergency / 🟡 Urgent / 🟢 Routine with red-flag detection
- **RAG-Powered** — Retrieves from medical triage guidelines for evidence-based assessment
- **Department Routing** — Routes to 10 departments (Emergency, Cardiology, Neurology, etc.)
- **Human Escalation** — Automatically escalates life-threatening or ambiguous cases
- **Dual-Model Strategy** — Flash-Lite for conversation, Flash for critical reasoning
- **Real-time Chat** — WebSocket-based with typing indicators

## Tech Stack

| Component | Technology |
|---|---|
| LLM (Chat) | Gemini 2.5 Flash-Lite |
| LLM (Reasoning) | Gemini 2.5 Flash |
| Agent Framework | LangGraph |
| RAG | ChromaDB + Gemini Embeddings |
| Backend | FastAPI + WebSocket |
| Frontend | Vanilla HTML/CSS/JS |

## Setup

### 1. Get a Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Click "Get API Key" → "Create API Key"
3. Copy the key

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and paste your API key
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Build the Knowledge Base

```bash
cd backend
python ingest.py
```

### 5. Run

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Open http://localhost:8000 in your browser.

## Architecture

```
Patient → Chat UI → WebSocket → FastAPI → LangGraph Agent
                                              ↓
                                    ┌─────────┼─────────┐
                                    ↓         ↓         ↓
                              Flash-Lite   Flash    ChromaDB
                              (chat)    (reasoning)  (RAG)
                                    ↓         ↓         ↓
                                    └─────────┼─────────┘
                                              ↓
                                      Triage Summary
                                    (urgency + department)
```

## Disclaimer

This is a demonstration project for educational purposes only. It does not provide real medical advice and should not be used for actual medical triage.

## License

MIT
