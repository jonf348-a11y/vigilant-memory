# Hethersett Grant Agent

AI-powered grant finding and application assistant for **HEAT** (Hethersett Environmental Action Team) and **HEAG** (Hethersett Environmental Action Group).

## What it does

- **Find Grants** — AI agent searches the web for environmental grants HEAT/HEAG can apply for
- **Track Applications** — Web dashboard to manage your grant pipeline from discovery to award
- **Apply Helper** — Chat with an AI assistant to help complete grant applications

---

## Deploy to Railway (recommended — no laptop needed)

Railway hosts the app in the cloud so anyone can open it in a browser.

### Step 1 — Get an Anthropic API key

1. Go to **console.anthropic.com** and sign up (or log in)
2. Go to **API Keys** and create a new key
3. Copy it — you'll need it in Step 3

### Step 2 — Deploy from GitHub

1. Go to **railway.app** and sign up with your GitHub account
2. Click **New Project → Deploy from GitHub repo**
3. Select **jonf348-a11y/vigilant-memory** and choose the `claude/hethersett-grant-agent-t4xntv` branch
4. Railway will detect the `Dockerfile` and start building automatically

### Step 3 — Add your API key

1. In Railway, click your service → **Variables**
2. Add: `ANTHROPIC_API_KEY` = *(your key from Step 1)*
3. Railway will redeploy automatically

### Step 4 — Add persistent storage (so grants aren't lost on restart)

1. In your Railway project, click **New → Volume**
2. Mount it at `/data`
3. Add another variable: `DATABASE_URL` = `sqlite:////data/grants.db`
4. Redeploy

### Step 5 — Open the app

Click the URL Railway gives you (e.g. `https://your-app.railway.app`) — share it with the team!

---

## Run locally (for developers)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # then edit .env and add your ANTHROPIC_API_KEY
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**.

---

## Usage

1. **Find Grants** — choose topics, click "Search for Grants". The AI spends ~1 minute searching the web.
2. **Track** — update statuses (Reviewing → Applied → Awarded) and add notes to each grant.
3. **Apply** — select a grant and chat with the AI to get help writing the application.

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key — **required** |
| `DATABASE_URL` | SQLite path (default: `sqlite:///./grants.db`). On Railway with a Volume, use `sqlite:////data/grants.db` |
| `PORT` | Port to listen on (Railway sets this automatically) |

## Tech Stack

- **Backend**: Python, FastAPI, SQLite, Anthropic Python SDK
- **Frontend**: React, TypeScript, Vite, Tailwind CSS
- **AI**: Claude Opus 4.8 with web search
