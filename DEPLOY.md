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

### 2b. Fast path — wire secrets from your local `.env` (GitHub CLI)

If you have the [GitHub CLI](https://cli.github.com) installed and authenticated
(`gh auth login`), you can push the secrets straight from your machine. Run these
**from the repo root** (where `.env` lives) **after** adding the remote and
pushing.

```bash
# Helper: read ONE value from .env without executing the file (handles '=' in values).
val() { grep -E "^$1=" .env | head -1 | cut -d= -f2-; }

# --- Live provider keys (pulled from your local .env) ---
gh secret set FINNHUB_API_KEY        --body "$(val FINNHUB_API_KEY)"
gh secret set ALPHA_VANTAGE_API_KEY  --body "$(val ALPHA_VANTAGE_API_KEY)"
gh secret set APCA_API_KEY           --body "$(val APCA_API_KEY)"
gh secret set APCA_SECRET_KEY        --body "$(val APCA_API_SECRET_KEY)"   # .env name -> workflow name

# --- SMTP / email (NOT in .env — entered interactively so they stay out of shell history) ---
printf 'smtp.gmail.com' | gh secret set SMTP_HOST
printf '587'            | gh secret set SMTP_PORT
gh secret set SMTP_USER        # paste your Gmail address, then press Ctrl-D
gh secret set SMTP_PASSWORD    # paste the 16-char Gmail App Password, then Ctrl-D
gh secret set EMAIL_FROM       # your Gmail address, then Ctrl-D
printf 'contact@quantumquant.trade' | gh secret set EMAIL_TO

# --- Non-secret config as repo Variables ---
gh variable set REPORT_TZ   --body 'America/New_York'
gh variable set OE_PROVIDER  --body 'yahoo'
gh variable set EMAIL_TOP_N  --body '25'

# Verify (names only; values are never shown):
gh secret list
gh variable list
```

> **Note 1 — name mapping:** your `.env` stores the Alpaca secret as
> `APCA_API_SECRET_KEY`, but the workflow reads `secrets.APCA_SECRET_KEY`; the
> command above maps it for you.
>
> **Note 2 — don't bulk-import:** avoid `gh secret set --env-file .env`. Your
> `.env` also holds unrelated secrets (OpenAI, Discord, Supabase, OAuth, …) that
> this report does **not** need — push only the keys above.
>
> **Note 3 — quoted values:** the `val` helper returns the raw text after `=`.
> If any of your `.env` values are wrapped in quotes, define
> `val() { grep -E "^$1=" .env | head -1 | cut -d= -f2- | tr -d "\"'"; }` instead
> so surrounding quotes are removed.

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

Or trigger and inspect it entirely from the CLI:

```bash
# Kick off a manual run (skips the 08:30 guard, sends right away):
gh workflow run daily-report.yml

# List recent runs and grab the newest run's status/id:
gh run list --workflow=daily-report.yml --limit 5

# Stream/inspect the logs (omit the id to pick interactively, or pass one):
gh run view --log
# e.g. a specific run:  gh run view <run-id> --log
# live progress:        gh run watch
```

A successful run prints `[SENT] Opportunity Engine — … — Top N candidates by max
return` in the "Scan and email the report" step. If the send fails (e.g. SMTP not
configured) the step prints `[NOT SENT (…)]` and **exits non-zero**, so the run
is marked failed and GitHub notifies you — no silent misses. (A local
`--dry-run` preview always exits 0.)

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
