import json
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from database import create_db_and_tables, get_session, engine
from models import (
    Grant,
    GrantStatus,
    GrantUpdate,
    SearchJob,
    ApplicationSession,
    SearchRequest,
    ChatRequest,
)
from agent import search_grants_sync, chat_with_assistant


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

def run_grant_search(job_id: int, focus_areas: list[str]):
    with Session(engine) as session:
        job = session.get(SearchJob, job_id)
        if not job:
            return
        job.status = "running"
        session.add(job)
        session.commit()

        try:
            grants = search_grants_sync(focus_areas)

            count = 0
            for g in grants:
                # Avoid exact duplicates by title+funder
                existing = session.exec(
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
                    max_amount=g.get("max_amount"),
                    min_amount=g.get("min_amount"),
                    focus_areas=json.dumps(focus_list if isinstance(focus_list, list) else []),
                    eligibility_notes=g.get("eligibility_notes"),
                )
                session.add(grant)
                count += 1

            session.commit()

            job = session.get(SearchJob, job_id)
            job.status = "complete"
            job.grants_found = count
            job.completed_at = datetime.utcnow().isoformat()
            session.add(job)
            session.commit()

        except Exception as e:
            job = session.get(SearchJob, job_id)
            job.status = "failed"
            job.error = str(e)
            session.add(job)
            session.commit()


# --- Grant search endpoints ---

@app.post("/api/search", status_code=202)
def start_grant_search(
    request: SearchRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Start a background grant search job."""
    job = SearchJob(focus_areas=json.dumps(request.focus_areas))
    session.add(job)
    session.commit()
    session.refresh(job)

    background_tasks.add_task(run_grant_search, job.id, request.focus_areas)

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

    return {
        "total_grants": total,
        "by_status": by_status,
        "total_potential_value": total_potential,
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
