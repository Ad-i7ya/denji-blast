# DENJI BLAST v4.0 — Hosting Guide

Your bot supports **two modes** — it auto-detects which to use:

| Mode | When | How it's triggered |
|------|------|--------------------|
| **Polling** | Local / VPS / Cloud Shell | Default (no env vars) |
| **Webhook** | Wasmer Edge / serverless | Set `WEBHOOK_URL` env var |

---

## 🥇 Method 1: Wasmer Edge (RECOMMENDED — you have Pro!)

> ⚠️ **UPDATE (Aug 2026): this method is currently BROKEN for aiogram bots.**
> Wasmer Edge runs Python on a wasm32-wasi interpreter. aiogram's compiled deps
> (`pydantic-core`, aiohttp C extensions) have **no wasm32-wasi wheels**, so the
> bot fails at boot with `ModuleNotFoundError: No module named 'aiohttp'`.
> Confirmed during deploy (app boots, returns HTTP 500). Use **Method 3 (Render
> free tier)** for a no-card free host that runs this bot correctly.

Wasmer Edge is serverless — it scales to zero when idle and wakes on requests.
Your bot's **webhook mode** is the perfect fit: Telegram sends updates to your
bot URL, which wakes the app. Almost zero compute hours used!

> ✅ Real example: https://wasmer.io/vivaneiona/sasha-bot (Telegram bot on Wasmer Edge)

### Step 1 — Project structure (already done)

```
src/bot.py          ← your bot (copy of bot.py)
wasmer.toml         ← package manifest
app.yaml            ← edge app config
.env/               ← Python venv with deps (you create this)
```

### Step 2 — Install Wasmer CLI & log in

```bash
curl https://get.wasmer.io -sSfL | sh
wasmer login
```

### Step 3 — Create the venv with dependencies

```bash
python3 -m venv .env
source .env/bin/activate
pip install aiogram aiohttp
```

### Step 4 — Add secrets (bot token)

```bash
wasmer secret set BOT_TOKEN 8850591358:AAGoAAx4hKtN8Bk0UJDxk-NLgUJ13D9KWKY
```

### Step 5 — Deploy!

```bash
wasmer deploy
```

Done! Your bot is live at `https://denji-blast-te4m1ord.wasmer.app`

### Step 6 — Register the webhook (auto-set by the bot on startup)

The bot calls `bot.set_webhook()` itself when it boots with `WEBHOOK_URL` set
(already configured in `app.yaml`). No manual step needed.

### ⚠️ Important Wasmer notes

- **Data persistence**: `blast_data.json` is written to `/data/` (see `DATA_FILE`
  in `app.yaml`). The `volumes` section in `app.yaml` already mounts a persistent
  volume at `/data` (Pro: 10GB included) so user data survives redeploys.
- **Firebase fallback (NEW)**: You can define firebases in the `FIREBASES` env var
  (one per line: `Label | https://url.firebaseio.com`). If `blast_data.json` is
  ever wiped, the bot auto-loads firebases from this env var on startup — so
  even a full data loss doesn't kill your SMS capability.
- **Compute hours**: Pro = 500 hours/mo. Webhook mode only burns compute when
  Telegram actually sends an update — a mostly-idle bot uses almost nothing.
- **Logs**: `wasmer logs <app-name>` to see output.

---

## 🆓 Method 2: Hugging Face Spaces (No Card Needed)

### Step 1 — Account
Go to https://huggingface.co/join — email only, **no card**.

### Step 2 — Create Space
1. https://huggingface.co/new-space
2. Name: `denji-blast` · SDK: `Docker` · Hardware: `CPU basic` (free) · Visibility: `Private` 🔒

### Step 3 — Upload files
Upload `bot.py`, `requirements.txt`, `Dockerfile`.

### Step 4 — Add secret
Settings → Variables and secrets → add `BOT_TOKEN` = your token.

### Step 5 — Keep-alive (so it never sleeps) 🔑
HF Spaces sleep after 48h of no traffic:
1. Free account at https://cron-job.org (no card)
2. Cron job → URL: `https://YOUR-USERNAME-denji-blast.hf.space/health`
3. Schedule: every 10 min

The built-in `/health` endpoint responds "OK" so the ping works.

---

## 🥇 Method 3: Render Free (RECOMMENDED — no card, works with aiogram)

This is the recommended host: free tier needs **no credit card**, runs the bot
with instant response, and the bot already has webhook mode + `/health` built in.

### Step 1 — Push the repo to GitHub

Create a GitHub repo (private is fine) and push `bot.py`, `requirements.txt`,
`render.yaml`, `Dockerfile` (ignore `.env/`, `venv/`, `blast_data.json`).

### Step 2 — Create the service from the Blueprint

1. https://render.com → **New → Blueprint** → connect your GitHub repo
2. Render reads `render.yaml` automatically (Python runtime, free plan,
   start command `python bot.py`)

### Step 3 — Set the bot token (secret)

Dashboard → your service → **Environment** → add:

```
BOT_TOKEN   <your bot token>   (Secret)
```

The bot requires `BOT_TOKEN` — it exits if unset (no token is hardcoded in code).
`WEBHOOK_URL` is auto-detected from Render's `RENDER_EXTERNAL_URL`, so Telegram
updates arrive via webhook and the bot answers instantly.

### Step 4 — Keep it awake (free tier sleeps after 15 min idle)

1. Free account at https://cron-job.org (no card)
2. Cron job → URL: `https://YOUR-SERVICE-NAME.onrender.com/health`
3. Schedule: every 10 min → the built-in `/health` endpoint answers `OK`

### ⚠️ Free tier notes

- **No persistent disk**: `blast_data.json` (users/credits/history) is stored on
  the ephemeral filesystem and resets on redeploy/restart. Firebases survive via
  the `FIREBASES` env var fallback (set it in Environment).
- Health-check paths are a paid feature; the cron keep-alive covers uptime.

---

## 🖥️ Method 4: Local / VPS / Google Cloud Shell (Polling)

```bash
pip3 install aiogram aiohttp
nohup python3 bot.py > bot.log 2>&1 &
```

---

## 🔒 Security Notes

- **Your bot token is a secret** — keep apps/Spaces **Private**, never commit it.
- `/source` is **MASTER OWNER ONLY** (hardcoded to your ID `7625368333`).
- Admin panel invisible to everyone unless you add them via **Super Admins** /
  **Admins** buttons in the owner panel.

## ✅ Quick Test After Deploy

1. Telegram → message your bot: `/start`
2. You should see: **👑 DENJI BLAST v4.0 - OWNER PANEL**
3. Send `/source` → you get bot.py (owner only)
4. Type `/` → see all commands
