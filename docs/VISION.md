# GluLess Project Vision & MVP Directive

**GluLess** is an agent-native executable contract language and runtime.

**GLU = Goal · Limits · Utilities**

> **The contract is the program. No glue required.**

GluLess lets humans and agents declare what must become true, what limits govern execution, and what capabilities are available. The runtime determines the execution path.

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

## API First

Every service must have a clear interface.

Prefer:
```text
Application → Shared Client → Stable API → Service
```
not:
```text
Application → shell → filesystem → database → hidden implementation detail
```

Use CRUD where the domain is naturally resource-oriented:
* `LIST`
* `GET`
* `CREATE`
* `UPDATE`
* `DELETE`

Use explicit actions only where CRUD does not represent the operation correctly.

Gas City is the foundation for Gas City behavior. If the Gas City API is missing something required by the MVP, improve the shared Gas City interface rather than bypassing it.

---

## Shared Ownership

Put behavior in the correct owner:
* UI-specific behavior → **UI**
* shared presentation behavior → **shared UI component**
* service contract → **shared client / SDK**
* endpoint/configuration → **canonical configuration**
* business capability → **owning service**
* cross-service execution → **governed runtime**

Do not make individual screens or features own platform concerns.

DRY is not just fewer lines of code. DRY means **one authoritative owner for each concept**.

---

## TDD and SOLID

For semantic changes:
1. add or update a failing test
2. prove the failure
3. make the smallest correction
4. prove the test passes
5. run the broader suite
6. prove real integration behavior where required

Keep boundaries explicit. Prefer small components with clear responsibilities over large orchestration classes.

Reuse common:
* configuration
* API clients
* models
* auth handling
* error translation
* retry behavior
* event handling
* state handling
* CI components

---

## DevOps and CI

Optimize for low-friction delivery. CI should be:
* deterministic
* reusable
* fast
* observable
* shared where possible
* ordered from cheap checks to expensive checks

Do not duplicate CI logic if a shared component already owns it. Do not introduce repo-local workarounds for shared platform problems. Fix the correct owner.

---

## Evidence

Completion requires proof.

For each capability report:
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

For mutations:
```text
AUTHORITY=
SIDE\_EFFECT=
STATE\_BEFORE=
STATE\_AFTER=
EVIDENCE=
```

For streams:
```text
CONNECTED=
EVENT\_RECEIVED=
EVENT\_RENDERED=
RECONNECT=
```

A compile is not proof. A rendered screen is not proof. An agent saying “done” is not proof.

---

## MVP Priority

The objective is not more infrastructure, more planning, or more abstraction.

The objective is:

**Ship the smallest complete path from Goal → Utility → Execution → Evidence.**

Each completed slice should:
1. use real APIs
2. reuse existing capabilities
3. reduce glue
4. improve shared ownership
5. leave behind tests
6. leave behind observable evidence
7. reduce future operational work
8. make the next slice easier

That is the standard.
