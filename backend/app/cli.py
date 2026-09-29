from __future__ import annotations

import json
from pathlib import Path

import click
from dotenv import load_dotenv

from app.config import get_settings
from app.db.database import SessionLocal, init_db
from app.models.schemas import Stage1RunRequest
from app.pipelines.stage1_run import run_stage1_pipeline_sync


@click.group()
def cli() -> None:
    """Stage 1 CLI — CV to jobs sheet."""
    backend_root = Path(__file__).resolve().parents[1]
    load_dotenv(backend_root / ".env")
    load_dotenv(backend_root.parent / ".env")


@cli.command("run")
@click.option("--cv", "cv_path", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--location", "locations", multiple=True, help="Override location (repeatable)")
@click.option("--min-score", type=int, default=None, help="Minimum match score to export")
def run_cmd(cv_path: Path, locations: tuple[str, ...], min_score: int | None) -> None:
    """Run Stage 1 pipeline from a CV file."""
    init_db()
    data = cv_path.read_bytes()
    options = Stage1RunRequest(
        locations=list(locations) if locations else None,
        min_match_score=min_score,
    )
    db = SessionLocal()
    try:
        result = run_stage1_pipeline_sync(data, cv_path.name, db, options)
        click.echo(json.dumps(result.model_dump(), indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    cli()
