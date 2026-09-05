"""
GasCity Mock Server
===================

A minimal FastAPI server that satisfies the GasCity OpenAPI contract defined in
api/openapi.yaml. This is the target system for the GluLess end-to-end canary.

Run on port 8000 (the default GasCity endpoint expected by the GLU agent):

    cd mock/
    pip install fastapi uvicorn
    uvicorn gascity_server:app --reload --port 8000

The GLU agent runs on port 8080. Both must be running for a successful PROVEN run.
"""

from __future__ import annotations

import time
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="GasCity Mock",
    version="0.2.0",
    description="Mock GasCity API for GluLess end-to-end canary runs.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_START = time.time()

# ── Data ──────────────────────────────────────────────────────────
# Canonical city registry for the demo.  Real names match bluefly estate.
_CITIES: dict[str, dict] = {
    "blucity": {
        "name": "blucity",
        "health": "healthy",
        "version": "v0.1.4",
        "agents": 3,
    },
    "gas-town": {
        "name": "gas-town",
        "health": "degraded",
        "version": "v0.1.2",
        "agents": 1,
    },
    "contextcontrol": {
        "name": "contextcontrol",
        "health": "healthy",
        "version": "v0.1.3",
        "agents": 2,
    },
}


# ── Request / Response models ─────────────────────────────────────
class CityCreate(BaseModel):
    health: str = "healthy"


class NudgeRequest(BaseModel):
    force: bool = False


# ── Routes ────────────────────────────────────────────────────────

@app.get("/v0/health")
def health_check():
    return {
        "status": "ok",
        "version": "0.2.0",
        "uptime": int(time.time() - _START),
    }


@app.get("/v0/cities")
def list_cities():
    """
    GET /v0/cities — satisfies GasCity.cities.list (read, no side effects).

    This is the primary utility in the demo contract.  A successful 200 response
    with at least one city satisfies the goal predicate: cities.listed == true.
    """
    return list(_CITIES.values())


@app.post("/v0/cities/{name}", status_code=201)
def create_city(name: str, body: CityCreate):
    """
    POST /v0/cities/{name} — satisfies GasCity.city.create (mutation, create).

    This operation is DENIED under the demo contract's 'deny *' limit.
    The GluLess runtime will authorise GasCity.cities.list and reject this
    utility in the AUTHORIZE stage — it will never reach this endpoint.
    Its presence in the registry is what makes the denied-path evidence real.
    """
    if name in _CITIES:
        raise HTTPException(status_code=409, detail="City already exists")
    _CITIES[name] = {"name": name, "health": body.health, "version": "v0.0.1", "agents": 0}
    return _CITIES[name]


@app.post("/v0/sessions/{session_id}/nudge")
def nudge_session(session_id: str, body: NudgeRequest):
    """
    POST /v0/sessions/{id}/nudge — GasCity.sessions.nudge (mutation, external_message).
    Also DENIED by the demo contract.
    """
    return {
        "status": "nudged",
        "sessionId": session_id,
        "message": f"Session {session_id} nudged (force={body.force})",
    }
