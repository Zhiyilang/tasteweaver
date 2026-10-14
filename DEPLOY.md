# Deploying the TasteWeaver hosted demo

The web console reads `PORT` and **auto-selects the live Qloo Taste Graph when
`QLOO_API_KEY` is set**; with no key it runs the in-process mock (offline).

## Render (recommended — also targets "Best Use of Render")
1. Render dashboard → **New → Blueprint**, connect this repo (`render.yaml` included).
2. In the service **Environment** tab, set `QLOO_API_KEY` (from the hackathon key email).
   `QLOO_BASE_URL` is preset to the hackathon endpoint.
3. Deploy. The public URL is your hosted demo — paste it into the Devpost submission.

## Local
```bash
QLOO_API_KEY=... QLOO_BASE_URL=https://hackathon.api.qloo.com \
  python -m tasteweaver serve --port 8790
```

## Rules to respect
- **Private server-side caching only** — never commit Qloo response data into this public repo.
- The hosted demo used for judging should run **live** (with `QLOO_API_KEY` set); the mock is for CI/local.
