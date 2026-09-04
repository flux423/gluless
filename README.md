# GluLess

**An agent-native executable contract language and runtime.**

**GLU = Goal · Limits · Utilities**

> **The contract is the program.**

GluLess exists to remove the integration glue between intent and execution.

Traditional programming languages are designed primarily for humans to describe how a computer should perform work. AI agents change that relationship. An agent often does not need every HTTP request, loop, wrapper, serializer, retry, state adapter, or orchestration step spelled out. It needs a precise description of the outcome, the boundaries governing execution, and the capabilities available to reach that outcome.

GluLess moves the abstraction layer upward.

Instead of forcing agents to continually generate and maintain glue code, humans and agents declare:

- the **Goal** — what must become true;
- the **Limits** — what authority, constraints, policies, approvals, and invariants govern execution;
- the **Utilities** — what APIs, tools, agents, services, models, resources, and event sources are available.

The runtime determines the execution path.

---

## Why GluLess

Modern application and agent code frequently looks like:

```text
intent
→ client library
→ API wrapper
→ auth plumbing
→ serializer
→ retry logic
→ model mapping
→ orchestration
→ state adapter
→ UI binding
```

Much of this is glue.

GluLess aims to reduce that layer by making stable capabilities and executable contracts the primary abstraction.

Instead of:

```python
response = requests.get("/v0/cities")
response.raise\_for\_status()
cities = response.json()

for city in cities:
    if city["health"] != "healthy":
        ...
```

GluLess should support something closer to:

```glu
goal BluCityHealthy {
    target:
        City("blucity").health == healthy

    limits:
        allow GasCity.health.read
        allow GasCity.sessions.inspect
        require approval for GasCity.sessions.restart

        never expose secrets
        preserve active\_work

    utilities:
        GasCity.health
        GasCity.sessions
        GasCity.events

    evidence:
        health
        actions
        events
}
```

The contract defines the outcome and boundaries.

The runtime determines how to satisfy it.

---

# GLU

## Goal

**What must become true?**

Goals describe desired outcomes rather than unnecessary implementation steps.

Examples:

```text
service is healthy
task is completed
artifact exists
incident is resolved
deployment succeeds
customer request is satisfied
```

A Goal is the destination.

---

## Limits

**What governs execution?**

Limits include:

```text
authority
permissions
constraints
policies
approvals
budgets
safety requirements
invariants
time boundaries
resource boundaries
```

Capability availability does not imply permission.

An agent may know how to perform an operation while still being prohibited from performing it.

Example:

```glu
limits {
    allow Work.read
    allow Work.claim

    require approval for Production.deploy

    deny Infrastructure.destroy
}
```

Limits are enforced by the runtime, not left to model judgment alone.

---

## Utilities

**What may the agent use?**

Utilities are stable capabilities exposed by the environment.

Examples:

```text
OpenAPI operations
HTTP APIs
MCP tools
A2A agents
event streams
models
repositories
search services
infrastructure services
databases behind governed APIs
human approval interfaces
```

A Utility describes what can be done, not how it is implemented internally.

For example:

```text
GasCity.sessions.list
```

may resolve to an HTTP API today and a different transport later without changing the GluLess contract.

---

# Architecture

```text
Human / Agent Intent
        |
        v
     GluLess
 Goal + Limits + Utilities
        |
        v
   Typed GluLess IR
        |
        v
   Execution Graph
        |
   +----+-----+---------+
   |          |         |
 OpenAPI     MCP       A2A
   |          |         |
 Service     Tool      Agent
   +----------+---------+
              |
              v
       Events / Evidence
              |
              v
            Result
```

GluLess sits above implementation languages.

Python, Swift, Rust, Go, JavaScript, Java, and other languages remain useful beneath stable service interfaces.

GluLess is not intended to replace them.

It makes them implementation details behind capabilities.

---

# API First

GluLess favors stable machine-readable interfaces.

Prefer:

```text
GluLess
→ Utility
→ API
→ Service
```

over:

```text
GluLess
→ shell
→ filesystem
→ internal process
→ undocumented database
```

Direct shell, filesystem, or database access may exist as explicit Utilities, but should not be the default integration model.

If an API exists, use it.

If incomplete, extend it.

Do not build around it.

---

# Interface Over Implementation

A contract should depend on:

```text
Work.list
GasCity.sessions.nudge
Memory.search
Deployment.inspect
```

not on:

```text
which framework implements it
which database stores it
which internal port serves it
which language it uses
which container runs it
```

Stable interfaces make implementations replaceable.

---

# Canonical IR

The GluLess Intermediate Representation is the real language contract.

Human-readable `.glu` source is one representation.

Agents may operate directly on structured IR.

The IR should be:

- typed;
- deterministic;
- serializable;
- versioned;
- inspectable;
- diffable;
- auditable;
- implementation-independent.

Conceptually:

```text
.glu source
    ↓
Parser
    ↓
Typed GluLess IR
    ↓
Validated Capability Graph
    ↓
Execution Graph
    ↓
Runtime
```

Human readability matters.

Machine-native structure matters more.

---

# Runtime Responsibilities

The runtime owns:

```text
parsing
type validation
Utility discovery
Utility resolution
authority checks
Limit enforcement
planning
execution
timeouts
retries
approvals
events
artifacts
evidence
results
```

The runtime should not own business-specific behavior that belongs in contracts or Utilities.

---

# Agent-Native, Not LLM-Everywhere

GluLess is designed for AI agents, but deterministic problems should remain deterministic.

Use deterministic systems for:

```text
parsing
typing
schema validation
authorization
Limit enforcement
serialization
execution accounting
```

Use AI for:

```text
planning
reasoning
Utility selection
interpretation
adaptation
recovery
```

A model may propose an action.

The runtime decides whether the action is valid and authorized.

---

# Authority and Approval

Authority is part of the executable contract.

Human approval is a first-class execution state.

An execution may enter:

```text
WAITING\_FOR\_APPROVAL
```

with:

```text
requested action
reason
actor
required approver
relevant context
expiration
```

Execution resumes only after valid approval.

Human-in-the-loop is governance, not an exception path.

---

# Events and Evidence

Agent execution must be observable.

Minimum event families may include:

```text
execution.started
execution.completed
execution.failed

goal.evaluated
goal.satisfied
goal.unsatisfied

utility.resolved
utility.started
utility.completed
utility.failed

limit.checked
limit.violated

approval.requested
approval.granted
approval.denied
```

Success is not:

```text
agent said "done"
```

A structured result should include:

```text
status
goal status
actions attempted
actions completed
events
artifacts
errors
evidence
```

The system should be able to answer:

```text
What happened?
Who acted?
What Goal were they pursuing?
What Utility was used?
Under what authority?
What changed?
What proves the result?
```

---

# Protocol Reuse

GluLess should compose existing protocols rather than recreate them.

Preferred integrations include:

```text
OpenAPI / HTTP
MCP
A2A
AG-UI
GraphQL
gRPC
CloudEvents
SSE
WebSocket
```

Conceptually:

```text
OpenAPI operation → Utility
MCP tool          → Utility
A2A agent/task    → Utility
GluLess event     → AG-UI
```

External systems do not need to use GluLess internally.

Interface compatibility is what matters.

---

# OpenAPI First

The first Utility adapter should be OpenAPI.

Given:

```text
GET  /v0/cities
POST /v0/sessions/{id}/nudge
```

GluLess should be able to expose:

```text
GasCity.cities.list
GasCity.sessions.nudge
```

The importer should derive where possible:

```text
operation id
HTTP method
path
parameters
request schema
response schema
authentication requirements
error responses
```

Do not hand-code duplicate models when the source interface already defines them.

---

# Initial MVP

The first implementation should remain intentionally small.

Initial scope:

```text
Parser
Typed IR
Validator
OpenAPI Utility importer
Utility registry
Goal evaluator
Limits validator
Simple planner
HTTP executor
Event log
Evidence/result model
CLI
Tests
```

Explicitly out of scope:

```text
IDE
visual programming
custom database
custom scheduler
custom message broker
custom authentication system
custom secrets manager
custom vector database
general-purpose UI framework
complex multi-agent orchestration
new transport protocols
```

Reuse existing systems instead.

---

# First Vertical Slice

Do not expand scope before this works:

```text
OpenAPI document
→ import operation
→ produce typed Utility
→ parse .glu contract
→ validate
→ resolve Utility
→ execute HTTP request
→ validate response
→ evaluate Goal
→ emit events
→ produce evidence
→ return structured result
```

Example:

```glu
goal BluCityExists {
    utilities:
        GasCity.cities.list

    success:
        cities.exists(name == "blucity")
}
```

Required proof:

```text
PARSE=PASS
TYPECHECK=PASS
UTILITY\_IMPORT=PASS
UTILITY\_RESOLUTION=PASS
HTTP\_EXECUTION=PASS
RESPONSE\_VALIDATION=PASS
GOAL\_EVALUATION=PASS
EVENTS=PASS
EVIDENCE=PASS
RESULT=PASS
```

Only after this vertical slice is solid should additional protocols or advanced planning be added.

---

# Design Principles

Use this decision order:

```text
DELETE
→ CONFIGURE
→ COMPOSE
→ REUSE
→ EXTEND
→ CREATE
```

Before adding code, ask:

```text
DOES\_STANDARD\_EXIST=
DOES\_PROTOCOL\_EXIST=
DOES\_LIBRARY\_EXIST=
DOES\_API\_EXIST=
DOES\_SHARED\_OWNER\_EXIST=
CAN\_EXISTING\_OWNER\_BE\_EXTENDED=
```

Only create something new after a real gap is established.

---

# Testing

Use test-driven development for semantic behavior.

For defects:

1. add a failing test;
2. prove failure;
3. implement the smallest correction;
4. prove the test passes;
5. run the broader suite.

Core test areas:

```text
parser
IR serialization
type validation
Utility import
Utility resolution
Limits enforcement
authority
Goal evaluation
HTTP execution
error translation
events
approval lifecycle
evidence
results
```

Core tests should not depend on live external services.

---

# Security

Never put secrets in GluLess source.

Integrate with established identity and secret providers.

Do not build a secrets manager.

Never print secrets in:

```text
logs
events
results
traces
tests
snapshots
```

---

# Status

GluLess is currently a concept and proposed language/runtime architecture.

The first implementation should prove three things:

1. APIs can become typed Utilities.
2. Goals and Limits can govern agent-selected execution.
3. Execution can remain observable and auditable without requiring humans to specify every implementation step.

If those hold, GluLess should grow from evidence rather than speculation.

---

# Working Principle

**GLU = Goal · Limits · Utilities**

> **The contract is the program.**

**No glue required.**
