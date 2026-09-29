from __future__ import annotations

from datetime import datetime

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.database import get_db, init_db
from app.db.models import RunRecord
from app.models.schemas import RunStatusResponse, Stage1RunRequest, Stage1RunResult
from app.pipelines.stage1_run import get_run_result, run_stage1_pipeline

app = FastAPI(title="LinkedIn Apply — Stage 1", version="0.1.0")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/stage1/run", response_model=Stage1RunResult)
async def stage1_run(
    cv: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Stage1RunResult:
    data = await cv.read()
    if not cv.filename:
        raise HTTPException(status_code=400, detail="Filename required.")
    try:
        return await run_stage1_pipeline(data, cv.filename, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/stage1/run/advanced", response_model=Stage1RunResult)
async def stage1_run_advanced(
    cv: UploadFile = File(...),
    db: Session = Depends(get_db),
    options: Stage1RunRequest | None = None,
) -> Stage1RunResult:
    data = await cv.read()
    if not cv.filename:
        raise HTTPException(status_code=400, detail="Filename required.")
    try:
        return await run_stage1_pipeline(data, cv.filename, db, options)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/stage1/runs/{run_id}", response_model=RunStatusResponse)
def get_run(run_id: str, db: Session = Depends(get_db)) -> RunStatusResponse:
    row = db.get(RunRecord, run_id)
    if not row:
        raise HTTPException(status_code=404, detail="Run not found.")
    result = get_run_result(db, run_id)
    return RunStatusResponse(
        run_id=row.id,
        status=row.status,  # type: ignore[arg-type]
        created_at=row.created_at,
        completed_at=row.completed_at,
        error=row.error,
        result=result,
    )
