# GLU Agent

**Identity**: `glu-agent`  
**Version**: 0.1.0  
**Protocol**: AG-UI (streaming SSE)  
**Runtime**: GluLess Execution Plane  

---

## Mission

The GLU Agent is the reference implementation of a GluLess-native agent.

It:
- Accepts a GLU contract (Goal · Limits · Utilities) via the AG-UI `/run` endpoint
- Compiles the contract using the Python GluLess SDK
- Plans an execution path respecting declared Limits
- Executes each step using declared Utilities only
- Streams AG-UI events back to the client in real time
- Reports Evidence on completion

> The agent never executes outside declared utilities.  
> The agent never acts outside declared limits.  
> The agent never claims completion without verifiable evidence.

---

## AG-UI Wire Contract

### Endpoint

```
POST /agent
Content-Type: application/json
Accept: text/event-stream
```

### Input (RunAgentInput)

```json
{
  "threadId": "<uuid>",
  "runId": "<uuid>",
  "messages": [
    {
      "role": "user",
      "content": "<GLU contract YAML as string, or a natural language goal>"
    }
  ],
  "context": [],
  "tools": [],
  "state": null
}
```

### Streamed AG-UI Events (SSE)

| Event Type          | When                                    |
|---------------------|-----------------------------------------|
| `RUN_STARTED`       | Immediately on run start                |
| `TEXT_MESSAGE_START`| Before streaming any text chunk         |
| `TEXT_MESSAGE_CHUNK`| Each planning/execution narrative chunk |
| `TEXT_MESSAGE_END`  | After last chunk for a message          |
| `STATE_SNAPSHOT`    | When contract is compiled (full state)  |
| `STATE_DELTA`       | On each utility execution result        |
| `RUN_FINISHED`      | On successful completion with evidence  |
| `RUN_ERROR`         | On any limit violation or fatal error   |

---

## GLU Contract Format

The agent accepts a YAML contract as the user message:

```yaml
id: my-contract
goals:
  - id: goal-1
    expression: "cities.listed == true"
    description: "Retrieve all registered cities from GasCity"
limits:
  - id: limit-1
    action_pattern: "deny *"
    description: "Deny any action not explicitly in utilities"
  - id: limit-2
    action_pattern: "allow GasCity.cities.list"
    description: "Allow listing cities"
utilities:
  - GasCity.cities.list
evidence_requirements:
  - id: ev-1
    assertion: "response.cities.length > 0"
    description: "At least one city was returned"
```

---

## State Shape (broadcast via STATE_SNAPSHOT / STATE_DELTA)

```typescript
interface GluAgentState {
  contractId: string | null;
  phase: "idle" | "compiling" | "planning" | "executing" | "complete" | "error";
  goals: Goal[];
  limits: Limit[];
  utilities: Utility[];
  plan: PlanStep[];
  observations: Observation[];
  evidence: Evidence[];
  error: string | null;
}
```

---

## Skills Used

| Skill                    | Purpose                                      |
|--------------------------|----------------------------------------------|
| `ag-ui-a2ui-integration` | Wire A2UI surfaces from agent output         |
| `agui-playwright-validate` | E2E verify the streaming path works         |
| `agui-cross-sdk-parity`  | Ensure TypeScript/Python event parity        |

---

## Files

| File                    | Purpose                                      |
|-------------------------|----------------------------------------------|
| `AGENT.md`              | This file — agent contract and wire spec     |
| `agent.py`              | FastAPI server implementing the AG-UI endpoint |
| `contract.yaml`         | Example GLU contract for GasCity demo        |
| `requirements.txt`      | Python dependencies                          |

---

## Running

```bash
# From [WORKSPACE-ROOT]/POCs/Gluless/.agents/agents/glu-agent/
pip install -r requirements.txt
uvicorn agent:app --reload --port 8080
```

The demo UI connects to `http://localhost:8080/agent`.

---

## Evidence Template

```
GOAL=        contract goal expression
UTILITY=     utility id invoked
LIMITS_CHECKED= limit patterns evaluated
REQUEST=     HTTP request made
REAL_RESPONSE= raw JSON response
TEST=        evidence assertion
RESULT=      pass/fail
EVIDENCE=    observable proof (response hash, status code, event count)
```
