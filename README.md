# Hethersett Grant Agent

AI-powered grant finding and application assistant for **HEAT** (Hethersett Environmental Action Team) and **HEAG** (Hethersett Environmental Action Group).

## What it does

- **Find Grants** — AI agent searches the web for environmental grants HEAT/HEAG can apply for
- **Track Applications** — Web dashboard to manage your grant pipeline from discovery to award
- **Apply Helper** — Chat with an AI assistant to help complete grant applications

## Quick Start

### 1. Set up the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Add your Anthropic API key
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=your_key_here

# Start the API server
uvicorn main:app --reload --port 8000
```

### 2. Set up the frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

## Usage

1. **Find Grants** — go to "Find Grants", choose your topics, and click "Search for Grants". The AI will spend a minute searching the web and return relevant grants.
2. **Track** — go to "Track Applications" to update statuses (Reviewing → Applied → Awarded) and add notes.
3. **Apply** — go to "Apply Helper", select a grant, and chat with the AI to get help writing your application.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key (get one at console.anthropic.com) |

## Tech Stack

- **Backend**: Python, FastAPI, SQLite (via SQLModel), Anthropic Python SDK
- **Frontend**: React, TypeScript, Vite, Tailwind CSS
- **AI Model**: Claude Opus 4.8 with web search
