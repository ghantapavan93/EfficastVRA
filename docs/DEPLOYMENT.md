# Deployment — Render + Vercel + Neon (all free)

The repo is wired so a cloud deploy is **configuration, not code changes**. This is the free, demo-grade
path; the same setup hardens to production by flipping a couple of env vars.

```
  Browser ──▶ Vercel (Next.js frontend)
                 │  rewrites /api/* and /health  (server-side proxy → no CORS)
                 ▼
             Render (FastAPI backend, free web service)
                 │  VRA_DATABASE_URL
                 ▼
             Neon (serverless Postgres, free)
```

**Why this works out of the box:** `backend/app/main.py` `lifespan` creates the tables and seeds the
synthetic scenario on first boot; `/health` (+ `/healthz`, `/api/health`) exercises the DB; `db.py`
normalizes a `postgres(ql)://` URL to the psycopg3 driver and enables `pool_pre_ping` so Neon's
scale-to-zero resume doesn't error; `frontend/next.config.mjs` reads `BACKEND_URL` from the env.

---

## 1) Neon — the database (~2 min)
1. neon.tech → **New Project** (pick a region near your Render region).
2. Copy the **connection string**. Prefer the **direct** URL (the host *without* `-pooler`) for this
   single small service — e.g. `postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require`.
3. Keep it handy for step 2. (Neon scales to zero after ~5 min idle and resumes in <1 s — the backend's
   pre-ping handles it. pgvector is available later for the semantic-RAG evolution.)

## 2) Render — the backend (~5 min)
**Blueprint (recommended):** Render → **New → Blueprint** → pick this repo. It reads `render.yaml`
(free web service, `rootDir: backend`, build `pip install -e ".[postgres]"`, start `uvicorn … --port $PORT`,
health check `/health`). Then set the three env vars:
- `VRA_DATABASE_URL` = the Neon string from step 1.
- `VRA_FRONTEND_ORIGIN` = your Vercel URL (fill after step 3, then redeploy).
- `VRA_DEMO_MODE` = `1` (demo) — already defaulted in the blueprint.

**Manual (if you skip the blueprint):** New → Web Service → this repo → Root Directory `backend`,
Runtime `Python`, Build `pip install -e ".[postgres]"`, Start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`,
Health Check Path `/health`, Plan `Free`; add the same env vars.

Deploy → note the backend URL, e.g. `https://efficast-vra-backend.onrender.com`. Verify
`…/health` returns `{"status":"ok","db":true,…}`.

## 3) Vercel — the frontend (~3 min)
1. Vercel → **Add New → Project** → import this repo.
2. **Root Directory = `frontend`** (important — it's a monorepo). Framework auto-detects as Next.js.
3. Add env var **`BACKEND_URL`** = your Render URL from step 2 (no trailing slash).
4. Deploy → note the Vercel URL, e.g. `https://efficast-vra.vercel.app`.
5. Go back to Render and set `VRA_FRONTEND_ORIGIN` to that Vercel URL; redeploy the backend.

> Vercel's **Hobby** tier is **personal/non-commercial** — fine for a demo/portfolio/pitch. A commercial
> launch needs Vercel Pro (or self-host the frontend).

## 4) Keep it warm (the one trick that makes "free" feel production-grade)
Render free services spin down after 15 min idle (30–60 s cold start). Add a free uptime pinger
(**UptimeRobot** or **cron-job.org**) hitting `https://<backend>/health` every ~10 minutes. The free
750 instance-hours/month is just enough to keep one service continuously warm, so a click never waits.
This also keeps Neon from idling between visits.

## 5) Production hardening (when you want it to be more than a demo)
- Set `VRA_DEMO_MODE=0` on Render → anonymous requests (no `X-VRA-User`) get **401** instead of being
  treated as the supervisor (the B1 fix). The frontend always sends the header, so the UI still works;
  the `/api/demo/*` reset routes are disabled.
- Point `BACKEND_URL`/`VRA_FRONTEND_ORIGIN` at a **custom domain** (free on both; automatic HTTPS).
- Ship Render logs to a free log drain (BetterStack/Logtail) for durable observability.
- For real concurrency/durability (multi-writer audit-seq, durable outbox worker, OIDC multi-tenancy)
  see the **[infra]** items in `ARCHITECTURE_AUDIT.md` — Neon Postgres is the prerequisite they need.

## Env var reference
| Var | Where | Value | Notes |
|-----|-------|-------|-------|
| `VRA_DATABASE_URL` | Render | Neon connection string | `DATABASE_URL` is also accepted; `db.py` adds the `+psycopg` driver |
| `VRA_FRONTEND_ORIGIN` | Render | Vercel URL | CORS allow-origin |
| `VRA_DEMO_MODE` | Render | `1` demo / `0` prod | gates the anonymous-supervisor fallback + demo routes |
| `BACKEND_URL` | Vercel | Render URL | used by `next.config.mjs` rewrites |

Cost at rest: **$0**. Cold start is the only free-tier compromise — mitigated by step 4, or removed
entirely by running the backend on an Oracle Cloud Always-Free VM instead of Render (see the cloud
options discussion).
