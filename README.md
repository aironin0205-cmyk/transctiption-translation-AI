# Subtitle AI MVP (Transcription + EN→FA Translation + TM)

This repo is an MVP you can run **without being a programmer**:
- Upload episode (audio/video)
- Audio prep: `ffmpeg-normalize` (Cobra VAD optional)
- ASR: AssemblyAI Universal-2 (word timestamps)
- Deterministic subtitle segmentation
- Agents: Strategist → (Terminologist) → Translator → QA/Polisher → Librarian
- Translation Memory: PostgreSQL + pgvector (HNSW)
- UI: Streamlit

> MVP note: This uses auto table creation at startup (no migrations). For production, add Alembic.

---

## Requirements
- Docker + Docker Compose
- Keys:
  - `ASSEMBLYAI_API_KEY`
  - `OPENROUTER_API_KEY`
- Optional:
  - `PICOVOICE_ACCESS_KEY` (for Cobra VAD; MVP skips VAD if missing)

---

## Quick start
1) Copy `.env.example` → `.env` and fill keys.
2) Run:
```bash
docker compose up -d --build
```
3) Open:
- UI: http://localhost:8501
- API docs: http://localhost:8000/docs

---

## Outputs
- English SRT: `data/outputs/<job>__en.srt`
- Persian SRT: `data/outputs/<job>__fa.srt`
- QA report: `data/reports/<job>__qa_report.json`
- Librarian report: `data/reports/<job>__librarian.json`
