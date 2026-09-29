from __future__ import annotations

from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.config import get_settings
from app.models.schemas import MatchedJob

SHEET_HEADERS = [
    "match_score",
    "match_reason",
    "job_title",
    "company",
    "location",
    "posted_at",
    "source",
    "apply_type",
    "job_url",
    "apply_url",
    "easy_apply_note",
    "salary",
    "status",
    "run_id",
    "job_id",
]


def _credentials():
    settings = get_settings()
    path = Path(settings.google_service_account_json)
    if not path.is_absolute():
        path = settings.backend_root / path
    if not path.exists():
        raise ValueError(
            f"Google service account JSON not found at {path}. "
            "See README for setup."
        )
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    return service_account.Credentials.from_service_account_file(str(path), scopes=scopes)


def _sheet_link(spreadsheet_id: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"


def export_jobs_to_sheet(
    jobs: list[MatchedJob],
    run_id: str,
    sheet_title_suffix: str | None = None,
) -> tuple[str, str]:
    """Returns (spreadsheet_id, sheet_url)."""
    settings = get_settings()
    creds = _credentials()
    service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    sheets = service.spreadsheets()

    spreadsheet_id = settings.google_sheet_id.strip()
    if not spreadsheet_id:
        title = settings.google_sheet_title
        if sheet_title_suffix:
            title = f"{title} — {sheet_title_suffix}"
        body = {"properties": {"title": title}}
        created = sheets.create(body=body).execute()
        spreadsheet_id = created["spreadsheetId"]

    rows = [SHEET_HEADERS]
    for job in jobs:
        rows.append(
            [
                job.match_score,
                job.match_reason,
                job.job_title,
                job.company,
                job.location,
                job.posted_at or "",
                job.source,
                job.apply_type.value,
                job.job_url,
                job.apply_url or "",
                job.easy_apply_note or "",
                job.salary or "",
                "new",
                run_id,
                job.job_id,
            ]
        )

    # Ensure header row exists on first sheet
    meta = sheets.get(spreadsheetId=spreadsheet_id).execute()
    sheet_name = meta["sheets"][0]["properties"]["title"]
    range_name = f"'{sheet_name}'!A1"

    existing = sheets.values().get(spreadsheetId=spreadsheet_id, range="A1:A1").execute()
    if not existing.get("values"):
        sheets.values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="RAW",
            body={"values": [SHEET_HEADERS]},
        ).execute()

    append_range = f"'{sheet_name}'!A1"
    sheets.values().append(
        spreadsheetId=spreadsheet_id,
        range=append_range,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": rows[1:] if len(rows) > 1 else []},
    ).execute()

    return spreadsheet_id, _sheet_link(spreadsheet_id)
