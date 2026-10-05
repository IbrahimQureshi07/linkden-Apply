# LinkedIn Apply — Stage 1 (Personal MVP)

Upload your CV → discover matching jobs (JSearch / Google Jobs aggregate, LinkedIn-heavy sources) → AI match scores → organized **Google Sheet** with apply links and Easy Apply / external labels.

Stage 2 (auto-apply) is not included yet.

## Prerequisites

- Python 3.11+
- [OpenAI API key](https://platform.openai.com/api-keys)
- [RapidAPI key](https://rapidapi.com/) subscribed to **[JSearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)** (free tier OK for testing)
- Google Cloud **service account** with Sheets API enabled

## Quick setup

```powershell
cd "c:\Users\User\Desktop\linkden Apply\backend"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy ..\.env.example .env
```

Edit `backend\.env`:

```env
OPENAI_API_KEY=sk-...
RAPIDAPI_KEY=...
CONFIG_PATH=../config.yaml
GOOGLE_SERVICE_ACCOUNT_JSON=./credentials/google-service-account.json
# Optional: append to existing sheet instead of creating new each run
GOOGLE_SHEET_ID=
GOOGLE_SHEET_TITLE=Job Pipeline
```

Copy `config.yaml` at repo root to tune locations (default: Pakistan cities + Remote).

## Google Sheets setup

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/).
2. Enable **Google Sheets API**.
3. Create a **Service Account** → Keys → JSON → save as  
   `backend/credentials/google-service-account.json`
4. Either:
   - Leave `GOOGLE_SHEET_ID` empty — each run creates a new spreadsheet (service account owns it; open the URL from CLI/UI output), or
   - Create a sheet in your Google account, **Share** it with the service account email (Editor), set `GOOGLE_SHEET_ID` in `.env`.

## Run

### CLI

```powershell
cd backend
.\.venv\Scripts\activate
python -m app.cli run --cv "C:\path\to\your-cv.pdf"
python -m app.cli run --cv cv.pdf --location "United States" --min-score 70
```

### API

```powershell
uvicorn app.main:app --reload --app-dir .
# POST http://127.0.0.1:8000/api/stage1/run  multipart: cv=@cv.pdf
```

### Streamlit UI

```powershell
streamlit run streamlit_app.py
```

## Sheet columns

| Column | Purpose |
|--------|---------|
| match_score / match_reason | OpenAI fit score 0–100 |
| source | linkedin, indeed, etc. (from aggregator) |
| apply_type | easy_apply, external, both, unknown |
| job_url / apply_url | Primary and external apply links |
| status | `new` (for Stage 2) |
| run_id / job_id | Stable tracking |

Add a filter in Sheets: **match_score ≥ 70**.

## Cost notes (typical personal run)

- **OpenAI**: 1 profile extraction + 1 query batch + 1 match batch (gpt-4o-mini ≈ low cents per run depending on CV/job count).
- **JSearch**: ~`max_queries × locations` API calls (default up to 8×3). Stay within RapidAPI free tier for testing.
- Caching/daily re-runs: SQLite stores runs under `backend/data/stage1.db`.

## Change location later

Edit `config.yaml` `locations` or pass CLI `--location` / Streamlit locations field — no code changes.

## Streamlit Cloud deploy

1. Push this repo to GitHub (do **not** commit `.env` or service-account JSON files).
2. [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Settings:
   - **Main file path:** `backend/streamlit_app.py`
   - Python: uses `runtime.txt` → **3.12**
   - Root `requirements.txt` is used for installs (Streamlit itself is provided by Cloud)
4. **Advanced settings → Secrets** — paste from [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example):
   - `OPENAI_API_KEY`
   - `RAPIDAPI_KEY`
   - `GOOGLE_SHEET_ID` (sheet shared Editor with service account email)
   - `GOOGLE_SERVICE_ACCOUNT_JSON_CONTENT` = full JSON as multiline string
   - `CONFIG_PATH = "../config.yaml"`
5. Deploy / reboot the app.

If install fails, open **Manage app** → terminal logs, fix `requirements.txt`, push, reboot.

## Project layout

```
backend/app/          FastAPI, pipeline, providers
backend/streamlit_app.py   UI (local + Cloud entry)
requirements.txt      Streamlit Cloud deps (repo root)
runtime.txt           python-3.12
config.yaml           Default Pakistan-focused search
.env.example          Environment template
.streamlit/secrets.toml.example   Cloud secrets template
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `OPENAI_API_KEY is not set` | Fill `backend/.env` or Streamlit Secrets |
| `RAPIDAPI_KEY is not set` | Subscribe to JSearch on RapidAPI |
| Google export failed | Service account JSON / `GOOGLE_SERVICE_ACCOUNT_JSON_CONTENT` + share sheet with SA email |
| Empty job list | Try broader titles in CV; check RapidAPI quota |
| Cloud: `Error installing requirements` | Ensure root `requirements.txt` exists; do not pin `streamlit` there |
| Cloud: `No module named app` | Main file must be `backend/streamlit_app.py` (path bootstrap included) |
