# docs/DEPLOYMENT.md — Deployment Paths

Three deployment paths in increasing order of cost and durability. None depend on paid API keys; `LLM_MODE=fake` and mock adapters are the default.

## Path 1 — Local dev / demo (laptop)

This is what `make demo` does. Single command from a clean clone:

```bash
make demo
```

Under the hood:

1. `docker compose -f infra/docker-compose.yml up -d postgres redis`
2. `uv run --directory apps/api alembic upgrade head`
3. `uv run --directory apps/api python -m apps.api.seeds.demo --fresh`
4. `pnpm install` (if needed)
5. `pnpm contracts:gen:local`
6. `pnpm dev` — `concurrently` runs FastAPI on `:8000` and Next.js on `:3000`

**URLs:**
- Web UI: `http://localhost:3000`
- API: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`
- Postgres: `localhost:5432` (user/pass `ngti/ngti`, db `ngti`)
- Redis: `localhost:6379`

**Tear down:**

```bash
docker compose -f infra/docker-compose.yml down -v   # -v also wipes the volume
```

## Path 2 — Single VM (Hetzner / Fly.io / Railway)

A single small VM hosts everything. Suitable for a sharable demo URL at $5-10/month.

### Provisioning (Hetzner CX21 example, ~€5/mo)

```bash
# 1. SSH in, install Docker + docker-compose
apt-get update && apt-get install -y docker.io docker-compose-plugin git
systemctl enable --now docker

# 2. Clone and configure
git clone <your-fork> /opt/ngti
cd /opt/ngti
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env
# Edit both .env files — set DATABASE_URL, REDIS_URL, LLM_MODE=fake, NEXT_PUBLIC_API_BASE=https://api.yourdomain.com

# 3. Bring up the stack
docker compose -f infra/docker-compose.yml up -d
docker compose -f infra/docker-compose.yml exec api alembic upgrade head
docker compose -f infra/docker-compose.yml exec api python -m apps.api.seeds.demo --fresh
```

### Env-var checklist

| Variable | Where | Required? | Notes |
|---|---|---|---|
| `DATABASE_URL` | api | yes | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | api | yes | `redis://host:6379/0` |
| `CORS_ALLOWED_ORIGINS` | api | yes in prod | Comma-separated browser origins. **Must include the deployed web URL** or every fetch will fail CORS. Defaults cover local dev (`localhost:3000` + `:3001`). Example: `https://goldeneye.example.com` |
| `LLM_MODE` | api | yes | `fake` for demo; `anthropic` / `openai` if you wire real LLM |
| `LLM_MODEL_FAST` | api | if real LLM | e.g. `claude-haiku-4-5-20251001` |
| `LLM_MODEL_SMART` | api | if real LLM | e.g. `claude-sonnet-4-6` |
| `ANTHROPIC_API_KEY` | api | if `LLM_MODE=anthropic` | never check into repo |
| `NEXT_PUBLIC_API_BASE` | web | yes | full origin of the api (e.g. `https://api.example.com`) |
| `NEXT_PUBLIC_WS_URL` | web | yes | WebSocket origin (`wss://api.example.com` in prod) |

### DNS

Point an `A` record (e.g. `ngti.example.com`) at the VM. Front the stack with Caddy or Traefik for TLS — Caddy is the lower-friction path:

```caddyfile
ngti.example.com {
  reverse_proxy localhost:3000
}
api.ngti.example.com {
  reverse_proxy localhost:8000
}
```

Caddy auto-renews Let's Encrypt certs. Drop the Caddyfile in `/etc/caddy/Caddyfile` and `systemctl restart caddy`.

## Path 3 — Managed (Vercel + Railway + Neon + Upstash)

Higher reliability, ~$25-40/month for a low-traffic demo.

| Component | Provider | Notes |
|---|---|---|
| Frontend (Next.js) | **Vercel** | Auto-deploys from GitHub. Set `NEXT_PUBLIC_API_BASE` and `NEXT_PUBLIC_WS_URL` in project env. No Dockerfile needed — Vercel builds Next.js natively. |
| Backend (FastAPI) | **Railway** | Builds `apps/api/Dockerfile`. **Set the build context to the repo root, not `apps/api/`** — the Dockerfile copies `apps/__init__.py` + `infra/migrations/` which live above. The CMD runs `alembic upgrade head` then `uvicorn` on `$PORT`. |
| Postgres + TimescaleDB | **Neon** (or Railway Postgres) | Neon free tier covers the demo. Enable `timescaledb` extension via SQL. |
| Redis | **Upstash** | Free tier sufficient. Use the `redis://default:<pass>@<host>:6379` URL. |
| Worker | Railway second service | Same image as api; different command. |

### Build the api image locally first (sanity check)

```bash
# Must run from the repo root — context is the repo root
docker build -f apps/api/Dockerfile -t ngti-api .

# Smoke-test against your local compose postgres+redis
docker run --rm -p 8001:8000 \
  --network infra_default \
  -e DATABASE_URL=postgresql+asyncpg://ngti:ngti@postgres:5432/ngti \
  -e REDIS_URL=redis://redis:6379/0 \
  -e CORS_ALLOWED_ORIGINS=http://localhost:3000 \
  ngti-api
# In another shell:
curl http://localhost:8001/v1/health   # → {"ok": true}
```

### Web build is API-free

The `(app)/*` routes are marked `force-dynamic` in `app/(app)/layout.tsx`, so
the Vercel build never tries to prerender them — meaning the build doesn't
need the API alive or `NEXT_PUBLIC_API_BASE` pointing at a working host.
Only the landing page `/` is statically generated.

### Vercel env vars

```
NEXT_PUBLIC_API_BASE=https://ngti-api.up.railway.app
NEXT_PUBLIC_WS_URL=wss://ngti-api.up.railway.app
```

### Railway env vars (api service)

```
DATABASE_URL=postgresql+asyncpg://...@ep-xxx.us-east-2.aws.neon.tech/ngti
REDIS_URL=rediss://default:...@usw1-something.upstash.io:6379
LLM_MODE=fake
CORS_ALLOWED_ORIGINS=https://goldeneye.example.com
```

If `CORS_ALLOWED_ORIGINS` is missing or wrong, the deployed Next.js app
will get every fetch blocked by the browser and the chart / dashboard
will appear empty. The api logs won't show a clear failure either —
CORS is a browser-side reject. If you see "no data" in the UI but the
api endpoints return 200 in your shell, this is almost always the cause.

### Cost expectations (low-traffic demo, monthly)

| Item | Cost |
|---|---|
| Vercel Hobby | $0 |
| Railway Hobby (api + worker) | ~$10 |
| Neon Free (≤0.5GB) | $0 |
| Upstash Free | $0 |
| Domain | ~$1 |
| **Total** | **~$10/mo** |

Bumping to a real LLM (Claude or GPT) is the only line that scales with usage — budget $5-20/mo for typical demo traffic with Haiku for summaries and Sonnet for narratives, with the 30-min cache TTL active.

## After deploy

Run the data-health check from the Admin screen at `/admin`. All five adapter rollups should read `ok` with their mock cadences. Open the OpenAPI docs at `/docs` to confirm the schema is in sync.
