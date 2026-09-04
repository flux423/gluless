# AGENTS.md

## Project

**GluLess** is an agent-native executable contract language and runtime.

**GLU = Goal · Limits · Utilities**

The core thesis is:

> **The contract is the program. No glue required.**

GluLess lets humans and agents declare:
- the **Goal** — what must become true;
- the **Limits** — what authority, constraints, policy, approvals, and invariants govern execution;
- the **Utilities** — what APIs, tools, agents, services, models, resources, and event sources are available.

The runtime determines the execution path.

---

## MVP Engineering Directive

Build the MVP using the **GluLess principle**:

**GLU = Goal · Limits · Utilities**

The engineering objective is not to generate more code. It is to reduce glue between intent and execution.

### Goal

Ship the smallest working vertical slice that creates real product value, proves real agent execution, and makes the next capability easier to add than the first.

Favor:
* working outcomes over architecture expansion
* API-first execution
* CRUD and stable interfaces
* reusable shared components
* test-driven development
* deterministic CI/CD
* observable execution
* low operational burden
* evidence-backed completion

Do not confuse infrastructure growth with product progress.

### Limits

Stay inside these engineering constraints:
* Do not build around Gas City. **Use and improve Gas City APIs and services.**
* Do not create scripts, services, databases, wrappers, or side paths when an existing interface can do the job.
* Do not couple application behavior directly to filesystem layout, shell commands, databases, internal ports, or implementation details when a stable API can own that contract.
* Do not duplicate schemas, API clients, auth logic, error handling, configuration, models, or UI behavior.
* Do not introduce a new abstraction unless it removes real duplication or establishes a necessary stable boundary.
* Do not accept “should work” as completion. Prove behavior with tests and runtime evidence.
* Do not make Thomas the orchestration layer. Automate repeatable work behind governed interfaces.

Use this decision order:
```text
DELETE
→ CONFIGURE
→ COMPOSE
→ REUSE
→ EXTEND
→ CREATE
```

Before creating anything new, answer:
```text
DOES\_API\_EXIST=
DOES\_SERVICE\_EXIST=
DOES\_SHARED\_COMPONENT\_EXIST=
DOES\_GAS\_CITY\_CAPABILITY\_EXIST=
DOES\_STANDARD\_OR\_PROTOCOL\_EXIST=
CAN\_EXISTING\_OWNER\_BE\_EXTENDED=
```

If yes, use it. If incomplete, extend it. Only create something new when a real gap is proven.

### Utilities

Treat every existing service, API, tool, agent, library, shared component, and protocol as a potential **Utility**.

Prefer stable capabilities such as:
```text
GasCity.sessions.list
GasCity.sessions.nudge
GasCity.events.stream
GitLab.mergeRequest.create
Execution.run
Memory.search
```
over implementation-specific behavior such as:
```text
run shell command
read internal file
query database directly
call undocumented port
duplicate REST wrapper
create another local service
```

Utilities should expose clear contracts:
```text
INPUT=
OUTPUT=
AUTHORITY=
SIDE\_EFFECTS=
ERRORS=
VERSION=
```
The client should care about the capability, not the implementation behind it.

---

## Engineering Model

Think in this order:
```text
GOAL
What must become true?

LIMITS
What rules, authority, constraints, and approvals apply?

UTILITIES
What existing capabilities can achieve it?

EXECUTION
What is the smallest valid path?

EVIDENCE
What proves it worked?
```

Do not begin with: **"What code should I write?"**  
Begin with: **"What capability already exists that moves the Goal forward?"**

---

## Agent Working Rules

When modifying this repository:

1. inspect current source before proposing architecture;
2. identify the existing owner of behavior;
3. reuse before creating;
4. write/update tests first for semantic changes (TDD);
5. make the smallest implementation change;
6. run relevant tests (pytest);
7. run the full suite before completion;
8. update docs when semantics change;
9. report evidence, not confidence.

---

## Evidence Reporting (Hard Rule)

Completion requires proof. For each task report, you must include the following metadata:

### For each capability report:
```text
GOAL=
UTILITY=
LIMITS\_CHECKED=
REQUEST=
REAL\_RESPONSE=
TEST=
RESULT=
EVIDENCE=
```

### For mutations:
```text
AUTHORITY=
SIDE\_EFFECT=
STATE\_BEFORE=
STATE\_AFTER=
EVIDENCE=
```

### For streams:
```text
CONNECTED=
EVENT\_RECEIVED=
EVENT\_RENDERED=
RECONNECT=
```

A compile is not proof. A rendered screen is not proof. An agent saying “done” is not proof.

---

## Decision Rule

When uncertain, favor the option that creates:
- fewer concepts;
- fewer dependencies;
- fewer services;
- fewer hidden behaviors;
- stronger interfaces;
- better tests;
- clearer authority;
- easier replacement;
- more observable execution.

GluLess should remove glue, not become another layer of it.
