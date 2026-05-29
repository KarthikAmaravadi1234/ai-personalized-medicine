# MediMind AI — Web UI

A modern React + Vite + Tailwind front-end for the AI Personalized Medicine API.
This is a standalone single-page app that talks to the FastAPI backend; it replaces
the Streamlit prototype with a polished, brandable UI.

## Quick start

```bash
cd web
npm install
cp .env.example .env   # adjust if your backend isn't on localhost:8000
npm run dev            # http://localhost:5173
```

Run the backend in parallel:

```bash
uvicorn backend.api.main:app --reload   # from the repo root
```

## Environment

| Variable             | Default                 | Purpose                                              |
| -------------------- | ----------------------- | ---------------------------------------------------- |
| `VITE_API_BASE_URL`  | `http://localhost:8000` | FastAPI backend base URL                             |
| `VITE_USE_MOCK`      | `false`                 | Serve built-in demo data when the backend is offline |

> **CORS:** the backend must allow the UI origin (`http://localhost:5173`). Add
> `CORSMiddleware` to `backend/api/main.py` if requests are blocked in the browser.

## What's built

- **App shell:** top header (logo, live API + AI status pills, dark-mode toggle) and a
  left sidebar with navigation.
- **Dashboard:** gradient hero, KPI cards (patients, average age, cohort split, AI engine),
  and a recent-patients panel.
- **Patients:** CSV / PDF upload cards with inline results, and a searchable cohort table.
- **Patient detail:** demographic tiles, labs (with flags) and vitals, plus a diabetes
  risk gauge and contribution bars.
- **Chat:** conversational thread per patient with collapsible citations, tool calls, and
  guardrail notes.
- **Knowledge:** ask/search toggle over the clinical knowledge base.

All pages are wired to the backend with a mock fallback (`VITE_USE_MOCK=true`).

## Build

```bash
npm run build && npm run preview
```
