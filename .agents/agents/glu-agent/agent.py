"""
GLU Agent — AG-UI streaming endpoint
Goal · Limits · Utilities

Implements the AG-UI protocol (SSE) over FastAPI.
The agent accepts a GLU contract YAML or natural language,
compiles it, plans against declared utilities, and streams
AG-UI events back to the client.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
import uuid
from pathlib import Path
from typing import AsyncGenerator

import httpx
import yaml
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# Add the Python SDK to the path
SDK_PATH = Path(__file__).resolve().parents[4] / "sdk" / "python"
sys.path.insert(0, str(SDK_PATH))

from gluless.compiler import GluLessCompiler, CompileError
from gluless.models import Contract, Utility, UtilityType, UtilityTransport, SideEffectType

app = FastAPI(title="GLU Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Built-in utility registry (matches openapi.yaml)
# ---------------------------------------------------------------------------

KNOWN_UTILITIES: list[Utility] = [
    Utility(
        id="GasCity.cities.list",
        name="cities.list",
        namespace="GasCity",
        description="List all cities registered in GasCity",
        type=UtilityType.READ,
        side_effects=SideEffectType.NONE,
        transport=UtilityTransport(
            type="openapi",
            method="GET",
            path="/cities",
        ),
        auth=[{"type": "apiKey", "in": "header", "name": "X-GasCity-Token"}],
    ),
    Utility(
        id="GasCity.sessions.nudge",
        name="sessions.nudge",
        namespace="GasCity",
        description="Nudge a GasCity session by ID",
        type=UtilityType.MUTATION,
        side_effects=SideEffectType.EXTERNAL_MESSAGE,
        transport=UtilityTransport(
            type="openapi",
            method="POST",
            path="/sessions/{id}/nudge",
            parameters=[{"name": "id", "in": "path", "required": True}],
            request_body={"force": False},
        ),
        auth=[{"type": "apiKey", "in": "header", "name": "X-GasCity-Token"}],
    ),
]

UTILITY_MAP = {u.id: u for u in KNOWN_UTILITIES}

# GasCity base URL (override via env)
import os
GASCITY_BASE = os.getenv("GASCITY_BASE_URL", "http://localhost:8000/v0")
GASCITY_TOKEN = os.getenv("GASCITY_TOKEN", "")

# ---------------------------------------------------------------------------
# AG-UI event helpers
# ---------------------------------------------------------------------------

def _event(event_type: str, data: dict) -> str:
    """Format a single SSE event."""
    payload = json.dumps({"type": event_type, **data})
    return f"data: {payload}\n\n"


def _ts() -> int:
    return int(time.time() * 1000)


# ---------------------------------------------------------------------------
# Default GLU contract (used when user sends plain text, not YAML)
# ---------------------------------------------------------------------------

DEFAULT_CONTRACT_YAML = """
id: glu-demo-contract
goals:
  - id: goal-1
    expression: "cities.listed == true"
    description: "Retrieve all registered cities from GasCity"
limits:
  - id: limit-deny-all
    action_pattern: "deny *"
    description: "Deny any action not declared in utilities"
  - id: limit-allow-list
    action_pattern: "allow GasCity.cities.list"
    description: "Allow reading the city list"
utilities:
  - GasCity.cities.list
evidence_requirements:
  - id: ev-cities
    assertion: "response.status == 200"
    description: "GasCity responded with HTTP 200"
"""


# ---------------------------------------------------------------------------
# Core streaming generator
# ---------------------------------------------------------------------------

async def _chunk(msg_id: str, text: str) -> str:
    """Build a TEXT_MESSAGE_CHUNK event string."""
    return _event("TEXT_MESSAGE_CHUNK", {"messageId": msg_id, "delta": text})


async def run_glu_agent(
    thread_id: str,
    run_id: str,
    user_message: str,
) -> AsyncGenerator[str, None]:

    async def emit(event_str: str):
        """Yield + flush — lets the event loop push the SSE frame before continuing."""
        return event_str  # caller must yield then sleep

    # 1. RUN_STARTED
    yield _event("RUN_STARTED", {"threadId": thread_id, "runId": run_id})
    await asyncio.sleep(0)

    # 2. Open narrative message
    msg_id = str(uuid.uuid4())
    yield _event("TEXT_MESSAGE_START", {"messageId": msg_id, "role": "assistant"})
    await asyncio.sleep(0)

    yield await _chunk(msg_id, "⚙️  Compiling GLU contract…\n")
    await asyncio.sleep(0.05)

    # Try to parse as YAML contract; fall back to default
    contract_yaml = user_message.strip()
    if not contract_yaml.startswith("id:"):
        contract_yaml = DEFAULT_CONTRACT_YAML

    try:
        contract: Contract = GluLessCompiler.compile_yaml(
            contract_yaml, available_utilities=KNOWN_UTILITIES
        )
    except CompileError as e:
        yield await _chunk(msg_id, f"❌ Compile error: {e}\n")
        await asyncio.sleep(0)
        yield _event("TEXT_MESSAGE_END", {"messageId": msg_id})
        await asyncio.sleep(0)
        yield _event("RUN_ERROR", {"message": str(e), "code": "COMPILE_ERROR"})
        return

    yield await _chunk(msg_id, f"✅ Contract `{contract.id}` compiled\n")
    await asyncio.sleep(0.05)
    yield await _chunk(msg_id, f"   Goals: {len(contract.goals)}  Limits: {len(contract.limits)}  Utilities: {len(contract.utilities)}\n")
    await asyncio.sleep(0.05)

    # 3. Broadcast initial state
    state = {
        "contractId": contract.id,
        "phase": "planning",
        "goals": [{"id": g.id, "expression": g.expression} for g in contract.goals],
        "limits": [{"id": l.id, "pattern": l.action_pattern} for l in contract.limits],
        "utilities": [{"id": u.id, "name": u.name} for u in contract.utilities],
        "plan": [],
        "observations": [],
        "evidence": [],
        "error": None,
    }
    yield _event("STATE_SNAPSHOT", {"snapshot": state})
    await asyncio.sleep(0)

    # 4. Plan
    yield await _chunk(msg_id, "\n🧠 Planning execution against declared utilities and limits…\n")
    await asyncio.sleep(0.05)

    plan = []
    for util in contract.utilities:
        plan.append({"step": len(plan) + 1, "utilityId": util.id, "status": "pending"})

    state["phase"] = "executing"
    state["plan"] = plan
    yield _event("STATE_DELTA", {"delta": [
        {"op": "replace", "path": "/phase", "value": "executing"},
        {"op": "replace", "path": "/plan", "value": plan},
    ]})
    await asyncio.sleep(0)

    # 5. Execute each utility
    observations = []
    evidence = []
    all_passed = True

    async with httpx.AsyncClient(base_url=GASCITY_BASE, timeout=10.0) as client:
        for step in plan:
            util_id = step["utilityId"]
            util = UTILITY_MAP.get(util_id)
            if not util:
                continue

            yield await _chunk(msg_id, f"\n▶️  Executing utility `{util_id}`\u2026\n")
            await asyncio.sleep(0.08)

            # Enforce limits — only "allow" patterns pass
            allowed_ids = {
                l.action_pattern.replace("allow ", "").strip()
                for l in contract.limits
                if l.action_pattern.startswith("allow ")
            }
            if util_id not in allowed_ids:
                yield await _chunk(msg_id, f"⛔ Limit denied `{util_id}` — not in allow-list\n")
                await asyncio.sleep(0.05)
                step["status"] = "denied"
                all_passed = False
                continue

            # Execute
            headers = {}
            if GASCITY_TOKEN:
                headers["X-GasCity-Token"] = GASCITY_TOKEN

            try:
                if util.transport.method == "GET":
                    resp = await client.get(util.transport.path, headers=headers)
                else:
                    resp = await client.post(util.transport.path, headers=headers, json={})

                obs = {
                    "utilityId": util_id,
                    "status": resp.status_code,
                    "body": resp.text[:500],
                }
                observations.append(obs)
                step["status"] = "complete"

                yield await _chunk(msg_id, f"   ↩  HTTP {resp.status_code} from `{util.transport.path}`\n")
                await asyncio.sleep(0.05)

                # Evaluate evidence requirements
                for ev_req in contract.evidence_requirements:
                    passed = resp.status_code == 200
                    ev = {
                        "requirementId": ev_req.id,
                        "assertion": ev_req.assertion,
                        "passed": passed,
                        "observation": obs,
                    }
                    evidence.append(ev)
                    mark = "✅" if passed else "❌"
                    yield await _chunk(msg_id, f"   {mark} Evidence `{ev_req.id}`: {ev_req.assertion} \u2192 {'PASS' if passed else 'FAIL'}\n")
                    await asyncio.sleep(0.05)
                    if not passed:
                        all_passed = False

            except httpx.ConnectError:
                step["status"] = "error"
                all_passed = False
                obs = {"utilityId": util_id, "status": 0, "body": "Connection refused — GasCity not running"}
                observations.append(obs)
                yield await _chunk(msg_id, f"   ⚠️  GasCity unreachable — observation recorded\n")
                await asyncio.sleep(0.05)
                # Still record evidence (failed)
                for ev_req in contract.evidence_requirements:
                    evidence.append({
                        "requirementId": ev_req.id,
                        "assertion": ev_req.assertion,
                        "passed": False,
                        "observation": obs,
                    })
                    yield await _chunk(msg_id, f"   ❌ Evidence `{ev_req.id}`: {ev_req.assertion} → FAIL (no connection)\n")
                    await asyncio.sleep(0.05)

    # 6. Final state
    state["phase"] = "complete" if all_passed else "error"
    state["observations"] = observations
    state["evidence"] = evidence
    state["plan"] = plan

    yield _event("STATE_SNAPSHOT", {"snapshot": state})
    await asyncio.sleep(0)

    # 7. Summary chunk
    status_icon = "🎯" if all_passed else "⚠️"
    phase_str = state["phase"]
    yield await _chunk(msg_id, f"\n{status_icon} Phase: {phase_str}  │  Observations: {len(observations)}  │  Evidence: {len(evidence)}\n")
    await asyncio.sleep(0.05)

    yield _event("TEXT_MESSAGE_END", {"messageId": msg_id})
    await asyncio.sleep(0)

    if all_passed:
        yield _event("RUN_FINISHED", {
            "threadId": thread_id,
            "runId": run_id,
        })
    else:
        yield _event("RUN_FINISHED", {
            "threadId": thread_id,
            "runId": run_id,
            "warning": "Some evidence requirements failed — see observations",
        })


# ---------------------------------------------------------------------------
# FastAPI endpoint
# ---------------------------------------------------------------------------

@app.post("/agent")
async def agent_endpoint(request: Request) -> StreamingResponse:
    body = await request.json()
    thread_id = body.get("threadId", str(uuid.uuid4()))
    run_id = body.get("runId", str(uuid.uuid4()))
    messages = body.get("messages", [])
    user_message = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            content = m.get("content", "")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        user_message = part.get("text", "")
                        break
            else:
                user_message = content
            break

    return StreamingResponse(
        run_glu_agent(thread_id, run_id, user_message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "agent": "glu-agent", "version": "0.1.0"}


@app.get("/utilities")
async def list_utilities() -> list:
    return [
        {
            "id": u.id,
            "name": u.name,
            "namespace": u.namespace,
            "description": u.description,
            "type": u.type,
            "side_effects": u.side_effects,
        }
        for u in KNOWN_UTILITIES
    ]
