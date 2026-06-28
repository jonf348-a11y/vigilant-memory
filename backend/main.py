import json
import os
from datetime import datetime, timedelta
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from database import create_db_and_tables, get_session, engine
from models import (
    Grant,
    GrantStatus,
    GrantUpdate,
    SearchJob,
    ApplicationSession,
    SearchRequest,
    TargetedSearchRequest,
    ChatRequest,
)
from agent import research_grants_deep, research_targeted, chat_with_assistant, PHASES

SEARCH_COOLDOWN_DAYS = 30


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="Hethersett Grant Agent",
    description="Grant finding and application assistant for HEAT and HEAG",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Background task ---

def _append_log(job_id: int, message: str, level: str):
    """Thread-safe log append — opens its own session to avoid conflicts."""
    with Session(engine) as s:
        job = s.get(SearchJob, job_id)
        if not job:
            return
        entries = json.loads(job.log_entries or "[]")
        entries.append({
            "ts": datetime.utcnow().isoformat(),
            "msg": message,
            "level": level,
        })
        # Keep last 500 log lines to avoid unbounded growth
        job.log_entries = json.dumps(entries[-500:])
        s.add(job)
        s.commit()


def _save_grants_batch(grants: list[dict]) -> int:
    """Save a list of raw grant dicts to the DB, skipping duplicates."""
    count = 0
    with Session(engine) as s:
        for g in grants:
            existing = s.exec(
                select(Grant).where(
                    Grant.title == g.get("title", ""),
                    Grant.funder == g.get("funder", ""),
                )
            ).first()
            if existing:
                continue
            focus_list = g.get("focus_areas", [])
            grant = Grant(
                title=g.get("title", "Untitled"),
                funder=g.get("funder", "Unknown"),
                description=g.get("description", ""),
                url=g.get("url"),
                deadline=g.get("deadline"),
                max_amount=_safe_int(g.get("max_amount")),
                min_amount=_safe_int(g.get("min_amount")),
                focus_areas=json.dumps(focus_list if isinstance(focus_list, list) else []),
                eligibility_notes=g.get("eligibility_notes"),
            )
            s.add(grant)
            count += 1
        s.commit()
    return count


def _safe_int(value) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _get_known_funders() -> list[str]:
    """Return deduplicated list of funder names already in the database."""
    with Session(engine) as s:
        existing = s.exec(select(Grant)).all()
        return list({g.funder for g in existing if g.funder})


def run_grant_search(job_id: int, focus_areas: list[str]):
    with Session(engine) as session:
        job = session.get(SearchJob, job_id)
        if not job:
            return
        job.status = "running"
        session.add(job)
        session.commit()

    total_saved = 0

    def progress(message: str, level: str = "info"):
        nonlocal total_saved
        _append_log(job_id=job_id, message=message, level=level)

    try:
        known_funders = _get_known_funders()
        grants = research_grants_deep(focus_areas, progress, known_funders=known_funders)
        total_saved = _save_grants_batch(grants)

        with Session(engine) as s:
            job = s.get(SearchJob, job_id)
            if job:
                job.status = "complete"
                job.grants_found = total_saved
                job.completed_at = datetime.utcnow().isoformat()
                s.add(job)
                s.commit()

    except Exception as e:
        _append_log(job_id=job_id, message=f"Fatal error: {e}", level="error")
        with Session(engine) as s:
            job = s.get(SearchJob, job_id)
            if job:
                job.status = "failed"
                job.error = str(e)
                s.add(job)
                s.commit()


def run_targeted_search(job_id: int, question: str):
    with Session(engine) as session:
        job = session.get(SearchJob, job_id)
        if not job:
            return
        job.status = "running"
        session.add(job)
        session.commit()

    def progress(message: str, level: str = "info"):
        _append_log(job_id=job_id, message=message, level=level)

    try:
        known_funders = _get_known_funders()
        grants = research_targeted(question, known_funders, progress)
        total_saved = _save_grants_batch(grants)

        with Session(engine) as s:
            job = s.get(SearchJob, job_id)
            if job:
                job.status = "complete"
                job.grants_found = total_saved
                job.completed_at = datetime.utcnow().isoformat()
                s.add(job)
                s.commit()

    except Exception as e:
        _append_log(job_id=job_id, message=f"Fatal error: {e}", level="error")
        with Session(engine) as s:
            job = s.get(SearchJob, job_id)
            if job:
                job.status = "failed"
                job.error = str(e)
                s.add(job)
                s.commit()


# --- Grant search endpoints ---

def _get_last_full_search(session: Session) -> Optional[SearchJob]:
    return session.exec(
        select(SearchJob)
        .where(SearchJob.search_type == "full")
        .where(SearchJob.status == "complete")
        .order_by(SearchJob.completed_at.desc())
    ).first()


def _get_running_search(session: Session) -> Optional[SearchJob]:
    return session.exec(
        select(SearchJob).where(SearchJob.status.in_(["running", "pending"]))
    ).first()


@app.get("/api/search/quota")
def get_search_quota(session: Session = Depends(get_session)):
    """Return quota status — last search date, next allowed date, whether locked."""
    running = _get_running_search(session)
    last = _get_last_full_search(session)

    result: dict = {
        "currently_running": running is not None,
        "running_job_id": running.id if running else None,
        "last_full_search_at": None,
        "next_full_search_allowed_at": None,
        "days_since_last": None,
        "days_remaining": None,
        "is_locked": False,
        "total_grants_in_db": session.exec(select(Grant)).all().__len__(),
    }

    if last and last.completed_at:
        last_dt = datetime.fromisoformat(last.completed_at)
        days_since = (datetime.utcnow() - last_dt).days
        next_allowed_dt = last_dt + timedelta(days=SEARCH_COOLDOWN_DAYS)
        days_remaining = max(0, SEARCH_COOLDOWN_DAYS - days_since)
        result["last_full_search_at"] = last.completed_at
        result["next_full_search_allowed_at"] = next_allowed_dt.isoformat()
        result["days_since_last"] = days_since
        result["days_remaining"] = days_remaining
        result["is_locked"] = days_remaining > 0

    return result


@app.post("/api/search", status_code=202)
def start_grant_search(
    request: SearchRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Start a background grant search job. Limited to once every 30 days."""
    running = _get_running_search(session)
    if running:
        raise HTTPException(
            status_code=409,
            detail=f"A search is already in progress (job #{running.id}). Wait for it to finish.",
        )

    last = _get_last_full_search(session)
    if last and last.completed_at:
        last_dt = datetime.fromisoformat(last.completed_at)
        days_since = (datetime.utcnow() - last_dt).days
        if days_since < SEARCH_COOLDOWN_DAYS:
            days_remaining = SEARCH_COOLDOWN_DAYS - days_since
            next_allowed = (last_dt + timedelta(days=SEARCH_COOLDOWN_DAYS)).strftime("%-d %B %Y")
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Full search ran {days_since} day(s) ago. "
                    f"Next full search allowed on {next_allowed} "
                    f"({days_remaining} day(s) remaining). "
                    "Use targeted search for specific questions in the meantime."
                ),
            )

    job = SearchJob(focus_areas=json.dumps(request.focus_areas), search_type="full")
    session.add(job)
    session.commit()
    session.refresh(job)

    background_tasks.add_task(run_grant_search, job.id, request.focus_areas)
    return {"job_id": job.id, "status": "pending"}


@app.post("/api/search/targeted", status_code=202)
def start_targeted_search(
    request: TargetedSearchRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Start a targeted search for a specific question. No monthly limit."""
    if not request.question or len(request.question.strip()) < 5:
        raise HTTPException(status_code=400, detail="Question must be at least 5 characters.")

    running = _get_running_search(session)
    if running:
        raise HTTPException(
            status_code=409,
            detail=f"A search is already in progress (job #{running.id}). Wait for it to finish.",
        )

    job = SearchJob(
        focus_areas=json.dumps([]),
        search_type="targeted",
        log_entries=json.dumps([{
            "ts": datetime.utcnow().isoformat(),
            "msg": f"Targeted search: {request.question}",
            "level": "phase",
        }]),
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    background_tasks.add_task(run_targeted_search, job.id, request.question.strip())
    return {"job_id": job.id, "status": "pending"}


@app.get("/api/search/{job_id}")
def get_search_status(job_id: int, session: Session = Depends(get_session)):
    """Check the status of a search job."""
    job = session.get(SearchJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.id,
        "status": job.status,
        "grants_found": job.grants_found,
        "error": job.error,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
    }


@app.get("/api/search/{job_id}/log")
def get_search_log(
    job_id: int,
    since: int = 0,
    session: Session = Depends(get_session),
):
    """Return log entries for a search job, optionally from a given index."""
    job = session.get(SearchJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    entries = json.loads(job.log_entries or "[]")
    return {
        "job_id": job.id,
        "status": job.status,
        "grants_found": job.grants_found,
        "total_entries": len(entries),
        "entries": entries[since:],
    }


@app.get("/api/search/phases/list")
def list_phases():
    """Return the list of research phases."""
    return [{"name": p["name"], "label": p["label"]} for p in PHASES]


# --- Grant CRUD endpoints ---

@app.get("/api/grants")
def list_grants(
    status: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """List all grants, optionally filtered by status."""
    query = select(Grant)
    if status:
        query = query.where(Grant.status == status)
    grants = session.exec(query.order_by(Grant.created_at.desc())).all()

    result = []
    for g in grants:
        d = g.model_dump()
        d["focus_areas"] = json.loads(g.focus_areas or "[]")
        result.append(d)
    return result


@app.get("/api/grants/{grant_id}")
def get_grant(grant_id: int, session: Session = Depends(get_session)):
    """Get a single grant by ID."""
    grant = session.get(Grant, grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")
    d = grant.model_dump()
    d["focus_areas"] = json.loads(grant.focus_areas or "[]")
    return d


@app.patch("/api/grants/{grant_id}")
def update_grant(
    grant_id: int,
    update: GrantUpdate,
    session: Session = Depends(get_session),
):
    """Update grant status or notes."""
    grant = session.get(Grant, grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(grant, key, value)
    grant.updated_at = datetime.utcnow().isoformat()

    session.add(grant)
    session.commit()
    session.refresh(grant)

    d = grant.model_dump()
    d["focus_areas"] = json.loads(grant.focus_areas or "[]")
    return d


@app.delete("/api/grants/{grant_id}", status_code=204)
def delete_grant(grant_id: int, session: Session = Depends(get_session)):
    """Delete a grant."""
    grant = session.get(Grant, grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")
    session.delete(grant)
    session.commit()


# --- Dashboard stats ---

@app.get("/api/stats")
def get_stats(session: Session = Depends(get_session)):
    """Get dashboard statistics."""
    all_grants = session.exec(select(Grant)).all()
    total = len(all_grants)
    by_status = {}
    total_potential = 0

    for g in all_grants:
        s = g.status.value
        by_status[s] = by_status.get(s, 0) + 1
        if g.max_amount and g.status not in (GrantStatus.REJECTED, GrantStatus.NOT_ELIGIBLE):
            total_potential += g.max_amount

    recent_jobs = session.exec(
        select(SearchJob).order_by(SearchJob.created_at.desc()).limit(5)
    ).all()

    all_jobs = session.exec(select(SearchJob)).all()
    total_searches = len(all_jobs)

    return {
        "total_grants": total,
        "by_status": by_status,
        "total_potential_value": total_potential,
        "total_searches": total_searches,
        "recent_searches": [
            {
                "job_id": j.id,
                "status": j.status,
                "grants_found": j.grants_found,
                "created_at": j.created_at,
            }
            for j in recent_jobs
        ],
    }


# --- Application helper endpoints ---

@app.post("/api/apply/chat")
def chat(request: ChatRequest, session: Session = Depends(get_session)):
    """Send a message to the application helper and get a response."""
    grant = session.get(Grant, request.grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")

    # Load or create session
    if request.session_id:
        app_session = session.get(ApplicationSession, request.session_id)
        if not app_session:
            raise HTTPException(status_code=404, detail="Session not found")
        history = json.loads(app_session.messages or "[]")
    else:
        app_session = ApplicationSession(grant_id=request.grant_id)
        session.add(app_session)
        session.commit()
        session.refresh(app_session)
        history = []

    # Get AI response
    grant_dict = grant.model_dump()
    grant_dict["focus_areas"] = json.loads(grant.focus_areas or "[]")

    reply = chat_with_assistant(grant_dict, history, request.message)

    # Update history
    history.append({"role": "user", "content": request.message})
    history.append({"role": "assistant", "content": reply})

    app_session.messages = json.dumps(history)
    app_session.updated_at = datetime.utcnow().isoformat()
    session.add(app_session)
    session.commit()

    return {
        "session_id": app_session.id,
        "reply": reply,
        "message_count": len(history),
    }


@app.get("/api/apply/sessions/{session_id}")
def get_session_history(session_id: int, session: Session = Depends(get_session)):
    """Get the message history for an application session."""
    app_session = session.get(ApplicationSession, session_id)
    if not app_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": app_session.id,
        "grant_id": app_session.grant_id,
        "messages": json.loads(app_session.messages or "[]"),
        "created_at": app_session.created_at,
    }


@app.get("/api/apply/grant/{grant_id}/sessions")
def list_grant_sessions(grant_id: int, session: Session = Depends(get_session)):
    """List all application sessions for a grant."""
    sessions = session.exec(
        select(ApplicationSession)
        .where(ApplicationSession.grant_id == grant_id)
        .order_by(ApplicationSession.updated_at.desc())
    ).all()
    return [
        {
            "session_id": s.id,
            "message_count": len(json.loads(s.messages or "[]")),
            "updated_at": s.updated_at,
        }
        for s in sessions
    ]


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve built React frontend (production)
_frontend = os.path.join(os.path.dirname(__file__), "frontend_dist")
if os.path.isdir(_frontend):
    app.mount("/assets", StaticFiles(directory=os.path.join(_frontend, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        return FileResponse(os.path.join(_frontend, "index.html"))
