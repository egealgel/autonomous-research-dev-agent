# Autonomous Research & Dev Agent

Multi-agent system: kullanıcı doğal dilde görev tanımlar, sistem araştırma yapar, kod üretir, rapor çıkarır.

## Monorepo Yapısı

```
backend/    FastAPI + Claude API orchestration
frontend/   React dashboard (Aşama 4)
infra/      docker-compose (lokal), Terraform (Aşama 4)
docs/       Mimari notları
storage/    Lokal artifact storage (S3 yerine, gitignored)
```

## Aşamalar

- **Aşama 1** — Tek görev uçtan uca: `/task` → Claude → DB + storage
- **Aşama 2** — Araştırma ajanı: web scraping, GitHub, RAG (Pinecone/pgvector)
- **Aşama 3** — Plan ajanı: araştırma sonuçlarından roadmap / research plan / PRD üretir
- **Aşama 4** — Orkestratör + React dashboard + EventBridge zamanlama

## Geliştirme

```bash
# Postgres'i başlat
cd infra && docker compose up -d

# Backend'i çalıştır
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

API: http://localhost:8000/docs

## Config

`.env` (örneği `backend/.env.example`):
- `ANTHROPIC_API_KEY` — Claude API anahtarı
- `DATABASE_URL` — Postgres connection string
- `STORAGE_PATH` — Lokal artifact dizini (default `./storage`)
