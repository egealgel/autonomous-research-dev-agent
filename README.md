# ARDA — Autonomous Research & Dev Agent

> Bir görev tanımla. Sistem URL'leri tarar, vektör hafızaya yazar, Claude Sonnet 4.6 ile detaylı roadmap, PRD veya araştırma planı üretir.

Multi-agent stack: bir backend (FastAPI + Claude + Postgres + pgvector + Redis/RQ) + animasyonlu bir React dashboard (Framer Motion + Lenis + TanStack Query).
<img width="1457" height="786" alt="Ekran Resmi 2026-06-20 22 39 49" src="https://github.com/user-attachments/assets/b4506731-d91b-4a35-80ed-321c7d403757" />
<img width="1457" height="786" alt="Ekran Resmi 2026-06-20 22 39 58" src="https://github.com/user-attachments/assets/f8219c56-3b60-4638-b6f0-7726985aef0b" />
<img width="1457" height="786" alt="Ekran Resmi 2026-06-20 22 40 11" src="https://github.com/user-attachments/assets/3c465621-1b7c-4e7b-8b7c-ac619cba2ff2" />



## Monorepo Yapısı

```
backend/    FastAPI + Claude + planner/research agents + pgvector RAG
frontend/   React + TypeScript + Tailwind + Framer Motion dashboard
infra/      docker-compose (Postgres+pgvector, Redis)
docs/       Mimari notları
storage/    Lokal artifact storage (S3 yerine, gitignored)
```

## Stack

| Katman | Teknoloji |
|---|---|
| Backend | FastAPI · Python 3.13 (uv) · SQLAlchemy 2 · Alembic · Anthropic SDK |
| LLM | Claude Sonnet 4.6 + prompt-caching ready |
| DB | PostgreSQL 16 + pgvector (HNSW cosine) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (lokal, 384-dim) |
| Async queue | Redis + RQ (SimpleWorker — Mac fork-safe) |
| Frontend | Vite · React 18 · TypeScript · Tailwind v4 |
| Animation | Framer Motion · Lenis (smooth scroll) |
| Server state | TanStack Query |
| Markdown | react-markdown + remark-gfm + rehype-highlight |

## Geliştirme

```bash
# 1) Servisler (Postgres + Redis)
cd infra && docker compose up -d

# 2) Backend (port 8000)
cd backend
uv sync
cp .env.example .env   # ANTHROPIC_API_KEY'i doldur
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

# 3) Worker (research + plan kuyrukları)
cd backend
uv run python worker.py

# 4) Frontend (port 5173)
cd frontend
npm install
npm run dev
```

Açık uçlar:
- API + Swagger UI: http://localhost:8000/docs
- Dashboard: http://localhost:5173

## Konfig

`.env` (örneği `backend/.env.example`):
- `ANTHROPIC_API_KEY` — Claude API anahtarı
- `ANTHROPIC_MODEL` — default `claude-sonnet-4-6`
- `DATABASE_URL` — Postgres connection string
- `REDIS_URL` — Redis URL
- `STORAGE_PATH` — Lokal artifact dizini (default `./storage`)
- `MONTHLY_BUDGET_USD` — bilgilendirme için harcama limiti

## Endpoints

| Method | Path | Açıklama |
|---|---|---|
| `POST` | `/tasks` | Tek-shot Claude çağrısı (sync) |
| `GET` | `/tasks` | Tüm görevler (newest first) |
| `GET` | `/tasks/{id}` | Tek görev detayı |
| `POST` | `/research` | URL'leri scrape + RAG ile Claude'a sor (async) |
| `GET` | `/research/{id}` | Research görev durumu |
| `POST` | `/plan` | Roadmap / research_plan / PRD üret (async) |
| `GET` | `/plan/{id}` | Plan görev durumu |
| `GET` | `/usage/current-month` | Aylık token + maliyet |
| `GET` | `/health` | Healthcheck |
