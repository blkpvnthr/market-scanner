# Serverless Deployment — Weekday 8:30 AM Email Report

Deliver the full ranked report (**≥20 candidates, ordered best→worst by maximum
modelled return**) to your inbox every weekday at **08:30**, with no laptop
running. Two paths are provided — **GitHub Actions** (recommended, free, zero
infra) and **AWS Lambda** (if you already live in AWS).

> **Research only. Not financial advice.** No trading or order execution.

---

## Option A — GitHub Actions (recommended)

The workflow lives at `.github/workflows/daily-report.yml`. GitHub runs it on a
cron schedule on its own infrastructure.

### 1. Push the repo to GitHub
```bash
git remote add origin git@github.com:<you>/market-scanner.git
git push -u origin main
```
(`.env` is git-ignored and is **never** pushed — set secrets in GitHub instead.)

### 2. Add secrets
Repo → **Settings → Secrets and variables → Actions → Secrets** → *New secret*:

| Secret | Example | Required |
|---|---|---|
| `SMTP_HOST` | `smtp.gmail.com` | ✅ |
| `SMTP_PORT` | `587` | optional (default 587) |
| `SMTP_USER` | `you@gmail.com` | ✅ |
| `SMTP_PASSWORD` | *app password* (not your login password) | ✅ |
| `EMAIL_FROM` | `you@gmail.com` | ✅ |
| `EMAIL_TO` | `contact@quantumquant.trade` | ✅ |
| `FINNHUB_API_KEY` / `ALPHA_VANTAGE_API_KEY` / `APCA_API_KEY` / `APCA_SECRET_KEY` | … | optional |

> Gmail needs an **App Password** (Google Account → Security → 2-Step
> Verification → App passwords). Outlook/Office365: `smtp.office365.com:587`.

### 3. Set the timezone (Variables, not Secrets)
Repo → **Settings → Secrets and variables → Actions → Variables**:

| Variable | Default | Notes |
|---|---|---|
| `REPORT_TZ` | `America/New_York` | **Set this to your timezone** (IANA name) |
| `OE_PROVIDER` | `yahoo` | `mock` · `yahoo` · `finnhub` · `alpha_vantage` · `alpaca` |
| `EMAIL_TOP_N` | `25` | clamped to ≥ 20 |

**How the 08:30 timing works (DST-safe):** GitHub cron is UTC-only and ignores
daylight saving. The workflow fires at both `12:30` and `13:30` UTC on weekdays;
an in-job guard checks the local hour in `REPORT_TZ` and lets **exactly one**
trigger proceed at 08:xx local — so you get one email at 08:30 year-round, with
no manual clock changes at DST boundaries.

### 4. Test it now
Repo → **Actions → Daily Opportunity Report → Run workflow** (manual runs skip
the time guard and send immediately).

> Note: GitHub disables scheduled workflows after ~60 days of repo inactivity —
> any push (or a manual run) re-arms them.

---

## Option B — AWS Lambda + EventBridge

Handler: `opportunity_engine.serverless.lambda_handler`

1. **Package** (container image is easiest since `yfinance` pulls deps):
   ```dockerfile
   FROM public.ecr.aws/lambda/python:3.11
   COPY . ${LAMBDA_TASK_ROOT}
   RUN pip install -e ".[providers]"
   CMD ["opportunity_engine.serverless.lambda_handler"]
   ```
2. **Environment variables** on the function: same `SMTP_*`, `EMAIL_*`,
   `OE_PROVIDER`, `EMAIL_TOP_N`, and any provider keys.
3. **Schedule** with EventBridge Scheduler, which supports timezones directly:
   - Cron: `cron(30 8 ? * MON-FRI *)`
   - Timezone: `America/New_York` (set your own) → fires 08:30 local, DST-safe.
4. Give the function ~512 MB / 60 s timeout (network calls to providers + SMTP).

The same handler works on GCP Cloud Functions (+ Cloud Scheduler) and Azure
Functions (+ Timer trigger) — all pass timezone-aware cron, so no guard needed.

---

## Local smoke test before deploying

```bash
# Render the exact email without sending (writes an HTML preview you can open):
python -m opportunity_engine email --dry-run --html-out preview.html

# Send a real one once SMTP_* / EMAIL_* are exported in your shell:
python -m opportunity_engine email
```

Both produce a report of at least 20 candidates ranked best→worst by max return.

---

**Research only. Not financial advice.** No automated buying or selling.
