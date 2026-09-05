"""
GLU Agent — AG-UI streaming endpoint
Goal · Limits · Utilities

Implements the AG-UI protocol (SSE) over FastAPI.

Five-stage runtime pipeline:
  RESOLVE → FILTER → AUTHORIZE → EXECUTE → VERIFY

State includes:
  context_projection  — registry funnel counts
  decision_paths      — per-utility authorization decisions
  observations        — raw HTTP results
  evidence            — evaluated evidence requirements
"""

from __future__ import annotations

import asyncio
import json
import os
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

# ---------------------------------------------------------------------------
# SDK path
# ---------------------------------------------------------------------------

SDK_PATH = Path(__file__).resolve().parents[4] / "sdk" / "python"
sys.path.insert(0, str(SDK_PATH))

from gluless.compiler import GluLessCompiler, CompileError
from gluless.models import Contract, Utility, UtilityType, UtilityTransport, SideEffectType

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(title="GLU Agent", version="0.2.0")

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

GASCITY_BASE  = os.getenv("GASCITY_BASE_URL", "http://localhost:8000/v0")
GASCITY_TOKEN = os.getenv("GASCITY_TOKEN", "")

# ---------------------------------------------------------------------------
# Default GLU contract
# ---------------------------------------------------------------------------

DEFAULT_CONTRACT_YAML = """
id: glu-demo-contract
goals:
  - id: goal-list-cities
    expression: "cities.listed == true"
    description: "Retrieve all registered cities from GasCity"
limits:
  - id: limit-deny-all
    action_pattern: "deny *"
    description: "Deny any action not explicitly permitted"
  - id: limit-allow-list
    action_pattern: "allow GasCity.cities.list"
    description: "Permit listing cities — read-only, no side effects"
utilities:
  - GasCity.cities.list
evidence_requirements:
  - id: ev-http-ok
    assertion: "response.status == 200"
    description: "GasCity responded with HTTP 200"
""".strip()

# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _enum_str(v) -> str:
    """Serialize an enum value to a clean lowercase string."""
    s = str(v)
    return s.split(".")[-1].lower().replace("_", "-") if "." in s else s.lower()


def _utility_meta(u: Utility) -> dict:
    """Return a JSON-serialisable representation of a Utility."""
    return {
        "id": u.id,
        "name": u.name,
        "namespace": u.namespace,
        "description": u.description,
        "type": _enum_str(u.type),
        "sideEffects": _enum_str(u.side_effects),
        "transport": {
            "method": u.transport.method,
            "path": u.transport.path,
        },
    }


# ---------------------------------------------------------------------------
# AG-UI event helpers
# ---------------------------------------------------------------------------

def _event(event_type: str, data: dict) -> str:
    """Format a single SSE event frame."""
    return f"data: {json.dumps({'type': event_type, **data})}\n\n"


def _ts() -> int:
    return int(time.time() * 1000)


# ---------------------------------------------------------------------------
# Limit evaluation
# ---------------------------------------------------------------------------

def _evaluate_limits(
    utility_id: str,
    contract: Contract,
) -> tuple[bool, str, str | None]:
    """
    Return (is_allowed, reason_phrase, limit_id).

    Evaluation order:
      1. For each limit in declaration order:
         - "allow <id>" → immediately permitted
         - "deny <id>"  → immediately denied
         - "deny *"     → denied (no matching allow found)
      2. If no limit matches → denied (no allow)
    """
    allow_limits = [
        l for l in contract.limits
        if l.action_pattern.startswith("allow ")
    ]
    deny_limits = [
        l for l in contract.limits
        if l.action_pattern.startswith("deny ")
    ]

    # Check explicit allow
    for lim in allow_limits:
        pattern = lim.action_pattern.replace("allow ", "").strip()
        if pattern == utility_id or pattern == "*":
            return True, lim.action_pattern, lim.id

    # Check explicit deny (catches "deny *" and "deny <id>")
    for lim in deny_limits:
        pattern = lim.action_pattern.replace("deny ", "").strip()
        if pattern == "*" or pattern == utility_id:
            return False, lim.action_pattern, lim.id

    return False, "no matching allow", None


# ---------------------------------------------------------------------------
# Core streaming generator
# ---------------------------------------------------------------------------

async def run_glu_agent(
    thread_id: str,
    run_id: str,
    user_message: str,
) -> AsyncGenerator[str, None]:
    """
    Five-stage GLU runtime, fully streamed via AG-UI SSE.

    Phases emitted to state:
      resolving  → filtering → authorizing → executing → verifying
      → proven | unresolved
    """

    async def flush():
        await asyncio.sleep(0)

    async def delay(ms: float = 0.05):
        await asyncio.sleep(ms)

    # ── 1. RUN_STARTED ──────────────────────────────────────────────────────
    yield _event("RUN_STARTED", {"threadId": thread_id, "runId": run_id})
    await flush()

    # ── 2. Narrative message stream ──────────────────────────────────────────
    msg_id = str(uuid.uuid4())
    yield _event("TEXT_MESSAGE_START", {"messageId": msg_id, "role": "assistant"})
    await flush()

    def chunk(text: str) -> str:
        return _event("TEXT_MESSAGE_CHUNK", {"messageId": msg_id, "delta": text})

    # ── 3. Compile ───────────────────────────────────────────────────────────
    yield chunk("⚙️  Compiling GLU contract…\n")
    await delay(0.05)

    contract_yaml = user_message.strip()
    if not contract_yaml.startswith("id:"):
        contract_yaml = DEFAULT_CONTRACT_YAML

    try:
        contract: Contract = GluLessCompiler.compile_yaml(
            contract_yaml, available_utilities=KNOWN_UTILITIES
        )
    except CompileError as e:
        yield chunk(f"❌ Compile error: {e}\n")
        await flush()
        yield _event("TEXT_MESSAGE_END", {"messageId": msg_id})
        yield _event("RUN_ERROR", {"message": str(e), "code": "COMPILE_ERROR"})
        return

    yield chunk(f"✅ Contract `{contract.id}` compiled\n")
    await delay(0.05)

    # ── 4. RESOLVE stage ─────────────────────────────────────────────────────
    # Report all utilities available in the registry.
    registry_total = len(KNOWN_UTILITIES)

    yield chunk(f"🔍 Resolving utilities from registry ({registry_total} registered)…\n")
    await delay(0.08)

    state: dict = {
        "contractId": contract.id,
        "phase": "resolving",
        "goals": [
            {"id": g.id, "expression": g.expression, "description": getattr(g, "description", "")}
            for g in contract.goals
        ],
        "limits": [
            {"id": l.id, "pattern": l.action_pattern, "description": getattr(l, "description", "")}
            for l in contract.limits
        ],
        "utilities": [_utility_meta(u) for u in contract.utilities],
        "context_projection": {
            "registry_total": registry_total,
            "goal_compatible": None,
            "limit_permitted": None,
        },
        "decision_paths": [],
        "plan": [],
        "observations": [],
        "evidence": [],
        "error": None,
    }
    yield _event("STATE_SNAPSHOT", {"snapshot": state})
    await flush()

    # ── 5. FILTER stage ──────────────────────────────────────────────────────
    # Narrow to utilities that satisfy the goal (declared in contract).
    declared_ids = {u.id for u in contract.utilities}
    goal_compatible = [u for u in KNOWN_UTILITIES if u.id in declared_ids]
    goal_compatible_count = len(goal_compatible)

    yield chunk(f"🎯 Goal-compatible: {goal_compatible_count} of {registry_total}\n")
    await delay(0.08)

    state["phase"] = "filtering"
    state["context_projection"]["goal_compatible"] = goal_compatible_count
    yield _event("STATE_DELTA", {"delta": [
        {"op": "replace", "path": "/phase", "value": "filtering"},
        {"op": "replace", "path": "/context_projection/goal_compatible", "value": goal_compatible_count},
    ]})
    await flush()

    # ── 6. AUTHORIZE stage ───────────────────────────────────────────────────
    # Evaluate each goal-compatible utility against declared limits.
    yield chunk("⚖️  Evaluating limits against candidates…\n")
    await delay(0.08)

    decision_paths = []
    permitted_count = 0

    for u in goal_compatible:
        is_allowed, reason, limit_id = _evaluate_limits(u.id, contract)
        if is_allowed:
            permitted_count += 1
        decision_paths.append({
            "utilityId": u.id,
            "name": u.name,
            "type": _enum_str(u.type),
            "sideEffects": _enum_str(u.side_effects),
            "decision": "authorized" if is_allowed else "denied",
            "reason": reason,
            "limitId": limit_id,
        })
        mark = "✅" if is_allowed else "⛔"
        yield chunk(f"   {mark} {u.id}: {reason}\n")
        await delay(0.05)

    state["phase"] = "authorizing"
    state["context_projection"]["limit_permitted"] = permitted_count
    state["decision_paths"] = decision_paths
    yield _event("STATE_DELTA", {"delta": [
        {"op": "replace", "path": "/phase", "value": "authorizing"},
        {"op": "replace", "path": "/context_projection/limit_permitted", "value": permitted_count},
        {"op": "replace", "path": "/decision_paths", "value": decision_paths},
    ]})
    await flush()

    # ── 7. EXECUTE stage ─────────────────────────────────────────────────────
    plan = [
        {"step": i + 1, "utilityId": d["utilityId"], "status": "pending"}
        for i, d in enumerate(decision_paths)
        if d["decision"] == "authorized"
    ]

    state["phase"] = "executing"
    state["plan"] = plan
    yield _event("STATE_DELTA", {"delta": [
        {"op": "replace", "path": "/phase", "value": "executing"},
        {"op": "replace", "path": "/plan", "value": plan},
    ]})
    await flush()

    observations = []
    all_executed = len(plan) > 0

    headers = {}
    if GASCITY_TOKEN:
        headers["X-GasCity-Token"] = GASCITY_TOKEN

    async with httpx.AsyncClient(base_url=GASCITY_BASE, timeout=10.0) as client:
        for step in plan:
            util_id = step["utilityId"]
            util = UTILITY_MAP.get(util_id)
            if not util:
                continue

            yield chunk(f"▶  Executing {util_id} ({util.transport.method} {util.transport.path})…\n")
            await delay(0.08)

            try:
                if util.transport.method == "GET":
                    resp = await client.get(util.transport.path, headers=headers)
                else:
                    resp = await client.post(util.transport.path, headers=headers, json={})

                obs = {
                    "utilityId": util_id,
                    "status": resp.status_code,
                    "body": resp.text[:500],
                    "timestamp": _ts(),
                }
                observations.append(obs)
                step["status"] = "complete"

                yield chunk(f"   ↩  HTTP {resp.status_code}\n")
                await delay(0.05)

            except httpx.ConnectError:
                obs = {
                    "utilityId": util_id,
                    "status": 0,
                    "body": "Connection refused — GasCity not running",
                    "timestamp": _ts(),
                }
                observations.append(obs)
                step["status"] = "error"

                yield chunk(f"   ⚠️  GasCity unreachable — observation recorded (status 0)\n")
                await delay(0.05)

    # ── 8. VERIFY stage ──────────────────────────────────────────────────────
    yield chunk("🔬 Verifying evidence requirements…\n")
    await delay(0.08)

    state["phase"] = "verifying"
    state["observations"] = observations
    yield _event("STATE_DELTA", {"delta": [
        {"op": "replace", "path": "/phase", "value": "verifying"},
        {"op": "replace", "path": "/observations", "value": observations},
    ]})
    await flush()

    evidence = []
    all_passed = True

    for obs in observations:
        for ev_req in contract.evidence_requirements:
            passed = obs["status"] == 200
            if not passed:
                all_passed = False
            ev = {
                "requirementId": ev_req.id,
                "assertion": ev_req.assertion,
                "description": getattr(ev_req, "description", ""),
                "passed": passed,
                "utilityId": obs["utilityId"],
                "httpStatus": obs["status"],
                "timestamp": obs.get("timestamp"),
            }
            evidence.append(ev)
            mark = "✅" if passed else "❌"
            verdict = "PASS" if passed else f"FAIL (HTTP {obs['status']})"
            yield chunk(f"   {mark} {ev_req.id}: {ev_req.assertion} → {verdict}\n")
            await delay(0.05)

    if not observations:
        # No utilities were authorized and executed
        all_passed = False

    # ── 9. Final state ────────────────────────────────────────────────────────
    final_phase = "proven" if all_passed else "unresolved"
    state["phase"] = final_phase
    state["evidence"] = evidence
    state["plan"] = plan

    yield _event("STATE_SNAPSHOT", {"snapshot": state})
    await flush()

    # ── 10. Close message ─────────────────────────────────────────────────────
    verdict_line = "🎯 PROVEN" if all_passed else "⚠️  UNRESOLVED"
    yield chunk(f"\n{verdict_line}\n")
    await delay(0.05)

    yield _event("TEXT_MESSAGE_END", {"messageId": msg_id})
    await flush()

    if all_passed:
        yield _event("RUN_FINISHED", {"threadId": thread_id, "runId": run_id})
    else:
        yield _event("RUN_FINISHED", {
            "threadId": thread_id,
            "runId": run_id,
            "warning": "Evidence requirements not satisfied — GasCity may be unreachable",
        })


# ---------------------------------------------------------------------------
# FastAPI endpoints
# ---------------------------------------------------------------------------

@app.post("/agent")
async def agent_endpoint(request: Request) -> StreamingResponse:
    body = await request.json()
    thread_id = body.get("threadId", str(uuid.uuid4()))
    run_id    = body.get("runId",    str(uuid.uuid4()))
    messages  = body.get("messages", [])

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
    return {
        "status": "ok",
        "agent": "glu-agent",
        "version": "0.2.0",
        "registry": len(KNOWN_UTILITIES),
    }


@app.get("/utilities")
async def list_utilities() -> list:
    return [_utility_meta(u) for u in KNOWN_UTILITIES]
