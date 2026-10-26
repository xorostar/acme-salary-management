# Deployment

Two pieces, deployed separately (ADR 005):

| Piece | Where | Why |
|---|---|---|
| API (`apps/api`) | Fly.io, one machine, SQLite on a persistent volume | Docker image already verified locally; volume keeps data across restarts |
| Web (`apps/web`) | Vercel | Native Next.js host; one environment variable |

The container migrates and seeds on first boot, so a fresh deploy comes up with the 10,000
employee demo organization and the two demo logins. A restart skips seeding.

## 1. API on Fly.io

```bash
# once
curl -L https://fly.io/install.sh | sh      # Windows: iwr https://fly.io/install.ps1 -useb | iex
fly auth signup                             # or: fly auth login

cd apps/api
# edit fly.toml: set `app` to a unique name, e.g. acme-salary-api-<you>
fly launch --copy-config --no-deploy
fly volumes create acme_data --size 1 --region lhr
fly secrets set \
  ACME_JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')" \
  ACME_DEMO_PASSWORD="acme-demo-2026"
fly deploy
curl https://<app>.fly.dev/health           # {"status":"ok"}
```

The API refuses to start in production without a real `ACME_JWT_SECRET` (32+ bytes).

## 2. Web on Vercel

1. Push the repository to GitHub.
2. In Vercel: **Add New → Project → Import** the repository.
3. **Root Directory:** `apps/web`. Framework preset: Next.js (detected).
4. **Environment variable:** `NEXT_PUBLIC_API_URL = https://<app>.fly.dev`
5. Deploy. Note the URL, e.g. `https://acme-salaries.vercel.app`.

## 3. Allow the web origin on the API

```bash
cd apps/api
fly secrets set ACME_CORS_ORIGINS='["https://acme-salaries.vercel.app"]'
```

Setting a secret restarts the machine. Log in at the Vercel URL with the demo accounts in
the README.

## Alternatives

- **Render / Railway:** both build `apps/api/Dockerfile` as is. Mount a disk at `/data`. On a
  free plan without a disk, the database re-seeds on every restart. That is acceptable for a
  demo, but changes will not persist.
- **Reset the demo data:** `fly ssh console -C "python -m app.seed --reset"`.

## Checklist after deploying

- [ ] `GET /health` returns ok
- [ ] Login works for `admin@acme.example` and `viewer@acme.example`
- [ ] Dashboard shows 9,321 active employees
- [ ] Run the walkthrough against production:
      `node apps/web/e2e/walkthrough.mjs --web https://<vercel-url>`
      (it creates test data; run `--reset` seeding afterwards if you want a clean demo)
