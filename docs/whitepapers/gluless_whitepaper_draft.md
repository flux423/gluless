# GluLess
## An Agent-Native Executable Contract Language and Runtime

**Draft 0.1 — Research Whitepaper**  
**September 2026**

> **GLU = Goal · Limits · Utilities**  
> **The contract is the program.**  
> **No glue required.**

---

## Abstract

Software systems have spent decades improving how humans specify procedures. Agentic systems introduce a different execution problem: an intelligent runtime can choose procedures, but it still needs a precise contract for what outcome is required, what actions are permitted, what capabilities exist, and what evidence proves completion.

GluLess proposes a small agent-native language and runtime built around three primitives: **Goal**, **Limits**, and **Utilities**. A GluLess contract describes the desired state or outcome, the authority and constraints governing execution, and the capabilities available to the executing agent. The runtime owns deterministic parsing, typing, validation, authorization, accounting, event emission, evidence collection, and result evaluation. AI is used where uncertainty is valuable: planning, capability selection, adaptation, recovery, and interpretation.

The central claim of this paper is intentionally narrow. GluLess should not replace OpenAPI, MCP, A2A, AG-UI, JSON Schema, Cedar, OPA, Temporal, CloudEvents, or existing API infrastructure. Those standards already own important parts of the stack. The unfilled layer is a **typed executable contract that composes outcome, authority, capabilities, execution, and proof into one canonical agent-facing program**.

This paper surveys adjacent technologies, defines the architectural gap GluLess targets, proposes a canonical intermediate representation, and outlines a minimal vertical slice capable of falsifying or validating the thesis.

---

## 1. The shift: from procedure specification to governed outcome execution

Traditional programming languages assume that the author provides the procedure. The runtime decides how to interpret machine-level details, but the program generally fixes the control flow: call this function, branch on this condition, iterate this collection, write this state.

Agentic execution changes the division of responsibility. A capable agent can often choose among multiple valid execution paths. It can inspect capabilities, reason over state, recover from errors, and adapt when one route fails. Requiring the contract author to prescribe every step can destroy much of that value. Conversely, allowing an agent to act from an underspecified prompt creates unacceptable ambiguity around authority, side effects, completion, and auditability.

This produces a new programming boundary:

```text
traditional program
= procedure + data + permissions embedded around procedure

agent-native contract
= desired outcome + governing limits + available capabilities
```

The agent-native runtime may choose a procedure, but it may not choose its own authority, rewrite the success criteria, silently invent capabilities, or declare completion without evidence.

GluLess therefore treats planning as an implementation detail of execution rather than the primary authored artifact.

### 1.1 The real program is the contract

The phrase **“the contract is the program”** has a concrete technical meaning:

1. The contract is typed and machine-verifiable before execution.
2. The contract names the state or outcome that must become true.
3. The contract establishes the authority boundary inside which any plan must remain.
4. The contract binds execution to discoverable capabilities.
5. The runtime can evaluate whether the outcome was achieved.
6. The runtime emits an evidence trail that is independent of an agent’s verbal claim.

A natural-language request may be an input to contract construction, but it is not the canonical executable artifact.

### 1.2 Agent-native does not mean “LLM everywhere”

A common error in agent architectures is to make probabilistic reasoning responsible for semantics that deterministic systems already solve better.

GluLess draws a strict line.

**Deterministic ownership:**

```text
parsing
schema validation
typing
serialization
authority evaluation
Limit enforcement
versioning
execution accounting
result validation
event envelopes
evidence binding
```

**AI ownership:**

```text
planning
reasoning
Utility selection
interpretation of underspecified state
adaptation
recovery
ranking valid alternatives
```

The result is not a “language for prompting an LLM.” It is a runtime contract inside which one or more intelligent planners may operate.

---

## 2. GLU: the minimal semantic model

GluLess starts with three top-level ideas rather than syntax constructs inherited from general-purpose programming languages.

### 2.1 Goal

A **Goal** defines what must become true.

A Goal should prefer observable postconditions over prescribed steps. Examples include:

```text
Deployment(version="2.4.1").status == healthy

Invoice(id="inv_481").state == paid

Repository("api").checks.required == passing

Customer("c_92").account.status == activated
```

A Goal can include success predicates, acceptable result schemas, deadlines, or confidence requirements, but it should not encode a procedural plan unless the procedure itself is part of the required outcome.

A useful test is:

> If two different execution paths produce the same permitted final state and evidence, should both satisfy the contract?

If yes, the difference belongs in planning rather than in the Goal.

### 2.2 Limits

**Limits** define what governs execution.

This category includes more than authorization. It includes:

```text
authority
permissions
explicit denials
approval gates
safety constraints
budgets
rate limits
time bounds
jurisdictional rules
invariants
required evidence
side-effect constraints
resource boundaries
```

A Utility being available does not imply that it is authorized.

A model selecting an action does not imply that the action is permitted.

The runtime must evaluate mutations against Limits before execution.

Example semantics:

```text
allow Work.read
allow Work.claim
require approval for Production.deploy
deny Infrastructure.destroy
budget money <= 500 USD
budget calls[Billing.charge] <= 1
```

Limits are not advisory text. They are executable constraints.

### 2.3 Utilities

**Utilities** are typed capabilities the runtime may invoke.

A Utility can originate from:

- an OpenAPI operation,
- an MCP tool,
- an A2A agent capability or task endpoint,
- a GraphQL operation,
- a gRPC method,
- an event stream,
- a model capability,
- an internal service API,
- a repository or infrastructure API,
- another GluLess contract exposed as a capability.

A Utility should expose a stable machine contract:

```text
IDENTITY=
INPUT=
OUTPUT=
AUTHORITY=
SIDE_EFFECTS=
ERRORS=
VERSION=
EVIDENCE=
```

The runtime should care about the capability contract, not whether the implementation behind it uses Python, Go, a hosted SaaS API, an MCP server, or another agent.

---

## 3. What already exists — and why GluLess should reuse it

A defensible GluLess architecture begins by refusing to recreate solved layers.

The most relevant standards and systems fall into several categories:

1. **Capability/interface description** — OpenAPI, JSON Schema, GraphQL, gRPC, MCP.
2. **Agent interoperability** — A2A.
3. **Agent/frontend interaction** — AG-UI.
4. **Policy and authorization** — Cedar, OPA/Rego.
5. **Durable orchestration** — Temporal, AWS Step Functions, LangGraph.
6. **Desired-state configuration** — Terraform and controller/reconciliation patterns.
7. **Planning languages** — PDDL and related automated planning formalisms.
8. **Events and provenance** — CloudEvents, W3C PROV and tracing systems.

None of these categories should be treated as competitors by default. They are potential implementation owners beneath or beside GluLess.

---

## 4. OpenAPI: a strong Utility source, not an execution contract

The OpenAPI Specification defines a language-agnostic description of HTTP API surfaces. Its primary value to GluLess is obvious: it already provides machine-readable operations, parameters, request bodies, response schemas, security schemes, servers, and error surfaces. An agent runtime should not require a bespoke wrapper around every REST API when a valid OpenAPI document already exists.[1]

Conceptually:

```text
OpenAPI Operation
      ↓ import
Typed GluLess Utility
```

A GluLess importer can derive:

```text
utility.id        <- operationId or canonical operation identity
utility.input     <- parameters + request body schema
utility.output    <- response schema(s)
utility.transport <- HTTP method + path + server metadata
utility.auth      <- referenced security requirements
utility.errors    <- non-success responses
```

The missing semantics are equally important. OpenAPI does not define the caller’s Goal, the runtime’s policy for selecting one operation over another, cross-operation authority, approval requirements, execution budgets, global invariants, or what evidence is sufficient to establish contract-level success.

Therefore:

> **OpenAPI should become a Utility source inside GluLess, not a dialect GluLess replaces.**

This is an example of the project’s decision order: reuse the interface standard, add only the execution-contract semantics that are absent.

---

## 5. MCP: capability exchange is becoming standardized

The Model Context Protocol defines a client-host-server architecture for connecting model applications with resources, prompts, and tools. Its specification also includes capability negotiation, lifecycle behavior, logging, progress, cancellation, authorization support for HTTP transports, and increasingly explicit task semantics.[2][3]

For GluLess, MCP is important because it makes a large category of agent capability discoverable through a standard protocol.

Conceptually:

```text
MCP tool → Utility
MCP resource → readable Utility/resource binding
MCP task → long-running Utility execution surface
```

MCP also demonstrates an architectural principle GluLess should preserve: **capability availability and capability authorization are separate concerns**. MCP advertises what a server can do, but the protocol’s own security guidance makes clear that implementers still need access controls, consent/authorization flows, validation, and auditing.[3]

That separation aligns closely with GLU:

```text
Utilities = what can be invoked
Limits    = whether a particular invocation is allowed
```

However, MCP is not itself a contract language for declaring an end-state across multiple capabilities. Its primary unit is protocol interaction with a server capability. A GluLess runtime can therefore consume MCP without attempting to absorb or fork it.

---

## 6. A2A: inter-agent protocol, not agent program semantics

The Agent2Agent protocol addresses interoperability among independent agent systems. Its current specification centers on capability discovery, tasks, messages, artifacts, streaming, and secure exchange without requiring one agent to expose its internal memory or implementation.[4]

This is exactly the sort of protocol GluLess should compose with.

A2A can answer:

```text
How do I discover another agent?
How do I send it work?
How is task state represented?
How are messages and artifacts exchanged?
```

GluLess must answer different questions:

```text
Why is this task being executed?
What outcome is required?
What Limits govern delegation?
Is delegation to this agent authorized?
What evidence from the delegated task satisfies the parent Goal?
```

A2A therefore maps naturally to the Utility layer:

```text
A2A Agent Card / capability
        ↓
      Utility
        ↓
A2A task execution
```

Delegation should not erase the parent contract’s Limits. A remote agent can choose its internal plan, but the GluLess runtime must preserve authority, budget, and evidence requirements across the boundary.

---

## 7. AG-UI: observability and interaction at the frontend boundary

AG-UI is an event-based protocol for connecting agents to user-facing applications. It standardizes lifecycle events, streamed messages, tool-call events, state snapshots and deltas, and other structures used to synchronize an agent runtime with a frontend.[5]

Even though GluLess is agent-native rather than human-interface-native, AG-UI remains valuable because a runtime needs an external observation surface. The important reuse pattern is:

```text
GluLess execution state/event
        ↓ adapter
      AG-UI
        ↓
observer / frontend
```

GluLess should not invent a new browser transport or UI synchronization protocol merely to show execution progress. It should emit a canonical internal event model and adapt that model to existing standards such as AG-UI, SSE, WebSocket, or CloudEvents depending on the boundary.

This keeps GluLess focused on contract semantics rather than presentation.

---

## 8. Cedar and OPA/Rego: policy is a component of Limits

Cedar and Open Policy Agent solve important pieces of the Limits problem.

Cedar is designed for authorization decisions based on principals, actions, resources, context, and policy. Its evaluation model is deterministic, with explicit permit/forbid behavior and default denial when no policy grants a request.[6]

OPA uses the declarative Rego language to evaluate policy over structured data. It is widely applicable to admission control, authorization, configuration, and other policy decisions.[7]

GluLess should not invent a full policy engine if Cedar or OPA can own the required rule semantics.

A useful architecture is:

```text
GluLess Limit
    ↓ compile/map
Policy decision request
    ↓
Cedar / OPA / native deterministic evaluator
    ↓
allow | deny | require approval | constraints
```

But Limits are broader than authorization alone. A contract may need to express:

- spend ceilings,
- execution deadlines,
- maximum attempts,
- mandatory evidence,
- model restrictions,
- data residency constraints,
- irreversible-action approvals,
- invariants that must remain true throughout execution.

Some of those can be delegated to existing policy engines; others belong to runtime accounting or contract validation.

The correct GluLess design is therefore **compositional**: reuse mature policy evaluators where their semantics fit, and keep the GluLess Limit model general enough to bind several enforcement mechanisms under one contract.

---

## 9. Temporal, Step Functions, and LangGraph: execution engines are not the contract

Temporal provides durable workflow execution that can resume through crashes and infrastructure failures.[8] AWS Step Functions defines workflows as state machines using Amazon States Language.[9] LangGraph provides a graph-based orchestration runtime with durable execution, state persistence, streaming, and human-in-the-loop mechanisms.[10]

These systems solve execution reliability and orchestration extremely well. GluLess should not recreate a durable workflow engine merely to demonstrate agent execution.

The distinction is control flow.

In a conventional workflow system, the workflow author generally defines the graph or sequence:

```text
A → B → choice → C or D → E
```

In GluLess, the authored contract can leave the execution path open:

```text
Goal    = state E is true
Limits  = actions X/Y forbidden, spend <= N, approval before Z
Utilities = {A, B, C, D, Z, ...}
```

The planner may construct different valid paths at runtime.

That means GluLess can use Temporal or another durable runtime beneath its executor while retaining a different programming model above it:

```text
GluLess Contract
      ↓
Planner chooses permitted plan
      ↓
Execution adapter
      ↓
Temporal / Step Functions / other runtime
```

LangGraph is closer to agentic execution because nodes may contain model reasoning and dynamic routing, but the graph remains an orchestration structure created by the application. GluLess aims to make **Goal + Limits + Utilities** the authored semantic core and allow graph structure to be a runtime product when appropriate.

---

## 10. Terraform and reconciliation: Goal has a useful precedent

Terraform’s language is declarative: it describes intended infrastructure rather than the imperative sequence used to create it.[11] Kubernetes-style controllers similarly operate through reconciliation between current and desired state.

This is one of the strongest precedents for the Goal concept.

The analogy is valuable but incomplete.

Desired-state infrastructure systems usually operate inside a bounded domain with providers, resources, dependency graphs, and relatively deterministic reconciliation semantics. Agentic Goals may span heterogeneous APIs, external agents, uncertain observations, semantic interpretation, and multiple acceptable solution paths.

GluLess can borrow several principles:

- compare observed state to desired state;
- make convergence explicit;
- preserve idempotency where possible;
- separate plan from desired state;
- record state transitions;
- detect drift;
- avoid treating a single successful API call as proof of Goal satisfaction.

But GluLess must add first-class authority and capability semantics because an intelligent planner can discover and select actions across a much broader surface.

---

## 11. PDDL: planning theory is relevant, but GluLess should not become a planner language

The Planning Domain Definition Language (PDDL) represents planning domains using predicates, actions, preconditions, effects, and problem goals. It is a major historical precedent for separating a desired goal from the planner that searches for an action sequence.[12]

The conceptual overlap with GluLess is real:

```text
PDDL domain actions      ~ Utilities
PDDL preconditions       ~ Utility applicability / state constraints
PDDL effects             ~ declared Utility effects
PDDL problem goal        ~ Goal
planner                  ~ GluLess planning component
```

However, PDDL assumes a formal planning domain whose actions and effects are modeled sufficiently for symbolic planning. Real API ecosystems rarely offer that completeness. Side effects can be partial, externally observable, delayed, probabilistic, undocumented, or dependent on opaque services.

GluLess should therefore learn from automated planning without requiring every Utility to become a fully formal action model.

A pragmatic Utility can expose increasing levels of semantic richness:

```text
Level 0: typed input/output
Level 1: side-effect classification
Level 2: preconditions / postconditions
Level 3: cost / latency / risk metadata
Level 4: formal effects suitable for deterministic planning
```

The runtime can exploit richer metadata when available and fall back to AI-assisted planning plus observation when it is not.

This graded model is more compatible with existing APIs than requiring the ecosystem to rewrite itself in a planning formalism.

---

## 12. CloudEvents and provenance: evidence must be structured

CloudEvents standardizes a common envelope for event data, improving interoperability across event producers and infrastructure.[13] W3C provenance models provide another useful conceptual vocabulary for relating entities, activities, and agents.

GluLess should distinguish **events** from **evidence**.

An event says something happened:

```text
UtilityInvocationStarted
UtilityInvocationSucceeded
ApprovalRequested
ApprovalGranted
GoalEvaluationCompleted
```

Evidence is a durable object used to substantiate a claim:

```text
HTTP response + digest
signed artifact
validated state observation
repository commit id
deployment revision
policy decision record
test result
external receipt
```

A run may emit many events but still lack sufficient evidence to prove the Goal.

This distinction prevents a common agent-system failure mode: equating internal narration or tool-call logs with successful external state change.

---

## 13. The gap: a typed contract across layers

The research landscape suggests that no single adjacent standard owns all of the following as one executable unit:

```text
1. an outcome that must become true
2. authority and constraints governing all execution paths
3. discoverable typed capabilities
4. planner freedom to choose among permitted paths
5. deterministic enforcement before mutations
6. observable execution events
7. evidence bound to effects and results
8. deterministic evaluation of contract completion where possible
```

This is the GluLess gap.

The product thesis is **not** that every individual element is new. Most are not. The thesis is that agentic systems need a canonical execution contract that composes these concerns without reducing them to prompt text or hard-coded orchestration graphs.

### 13.1 Comparison matrix

| System / standard | Goal semantics | Limits / policy | Capability description | Dynamic agent planning | Durable execution | Events | Evidence as completion proof |
|---|---|---|---|---|---|---|---|
| OpenAPI | No | API security metadata only | Strong for HTTP | No | No | No | No |
| MCP | Task/tool scoped | Transport/auth + host policy guidance | Strong for MCP capabilities | Model may select tools | Emerging task support | Progress/logging | Not contract-level |
| A2A | Task objective/message | Protocol security | Agent capabilities | Remote agent internal | Task lifecycle | Streaming/task state | Artifacts, but not parent contract proof |
| AG-UI | No | No | Tool/event surface | Observes agent | No | Strong UI event model | No |
| Cedar | No | Strong authorization | No | No | No | Decision diagnostics | Policy decision only |
| OPA/Rego | Desired policy decisions | Strong policy | No | No | No | Via integrations | Policy decision only |
| Temporal | Workflow completion | App-defined | Activities | App-defined | Strong | Strong history | Workflow result/history |
| Step Functions | State-machine terminal state | IAM + app rules | Service integrations | Limited to authored graph | Strong | Strong | Workflow state/history |
| LangGraph | Application-defined | Application-defined | Tools/nodes | Strong within graph | Strong | Streaming/tracing | App-defined |
| Terraform | Strong desired state | Provider/IAM outside language | Providers/resources | Deterministic planning | Apply/reconcile | Plan/apply logs | State + provider observation |
| PDDL | Strong formal goal | Constraints possible, not authority-centric | Formal actions | Strong planner model | Planner-dependent | Not primary | State satisfaction |
| **GluLess target** | **First-class** | **First-class** | **Imports existing standards** | **First-class** | **Delegated/reused** | **Canonical + adapters** | **First-class** |

The most important column is the last one. GluLess treats evidence not as optional telemetry, but as part of the execution contract.

---

## 14. The canonical IR is the language

The human-readable syntax should not be the normative core of GluLess.

The normative artifact should be a versioned, deterministic, serializable intermediate representation.

This is especially important for an agent-native language because agents can construct, inspect, transform, validate, and negotiate structured IR directly. A textual surface syntax becomes one optional encoding among several.

### 14.1 Example conceptual IR

```json
{
  "gluVersion": "0.1",
  "contract": {
    "id": "contract:deploy-api",
    "goal": {
      "kind": "predicate",
      "subject": "service:api",
      "assert": {
        "version": "2.4.1",
        "health": "healthy"
      }
    },
    "limits": [
      {
        "kind": "authority",
        "effect": "allow",
        "action": "Production.read"
      },
      {
        "kind": "approval",
        "action": "Production.deploy",
        "required": true
      },
      {
        "kind": "deny",
        "action": "Infrastructure.destroy"
      }
    ],
    "utilities": [
      {
        "ref": "openapi:deployments#createDeployment"
      },
      {
        "ref": "openapi:deployments#getDeployment"
      }
    ],
    "evidence": {
      "required": [
        "deployment.revision",
        "deployment.healthObservation"
      ]
    }
  }
}
```

The exact field names are not the point at this stage. The important architectural requirement is that the IR can be validated without asking a language model what it means.

### 14.2 Required IR properties

The canonical IR should be:

- **typed** — every semantic object has a known type;
- **deterministic** — equivalent source produces equivalent IR;
- **serializable** — stable machine encoding;
- **versioned** — semantics are tied to a declared version;
- **inspectable** — agents and tools can query contract structure;
- **auditable** — execution can reference immutable contract identities;
- **implementation-independent** — no runtime-specific classes in the language contract;
- **canonicalizable** — hashes/signatures can bind approvals and evidence to a precise contract.

Canonicalization becomes especially important if approvals or delegated execution must prove exactly which Goal and Limits were authorized.

---

## 15. Utility model: import, normalize, enrich

The strongest MVP route is to make an existing API operation executable as a typed Utility with minimal glue.

### 15.1 Import pipeline

```text
OpenAPI document
→ parse
→ select operation
→ normalize schemas
→ derive Utility identity
→ derive input/output
→ derive transport binding
→ derive auth requirements
→ attach side-effect metadata
→ validate Utility
→ register/resolve
```

The importer should preserve provenance back to the original API description.

### 15.2 Utility identity

A Utility identity must be stable enough for Limits to target it.

Bad:

```text
POST /v1/thing
```

Better:

```text
crm.contacts.create@v1
```

Best is likely a canonical identity that can retain provider namespace, interface type, source revision, operation identity, and semantic versioning without making human naming conventions normative.

### 15.3 Side effects are first-class metadata

Input/output schemas are insufficient for governed execution. The runtime needs to distinguish reads from mutations and ideally understand classes of mutation.

A minimal side-effect taxonomy might include:

```text
none
read
create
update
delete
external_message
financial
privilege_change
infrastructure
unknown
```

`unknown` must be meaningful. Unknown side effects should not silently inherit the authority of harmless reads.

### 15.4 Utility descriptions are not authority

An imported API specification or MCP tool can describe itself, but self-description should never grant permission.

This yields a critical invariant:

```text
CAPABILITY_METADATA != AUTHORITY
```

The runtime may use metadata for planning. Limits determine whether invocation is permitted.

---

## 16. Limits as executable governance

Limits must be evaluated at several phases, not once.

### 16.1 Validation-time Limits

Before planning:

- Is the contract internally contradictory?
- Does it reference prohibited capability classes?
- Is required approval policy resolvable?
- Is a requested budget invalid?

### 16.2 Plan-time Limits

When evaluating candidate plans:

- Does the plan include a denied Utility?
- Does projected spend exceed budget?
- Does the plan require an approval boundary?
- Does delegation exceed granted authority?

### 16.3 Invocation-time Limits

Immediately before every mutation:

- Is this exact invocation authorized now?
- Has state changed since planning?
- Has approval been granted for the canonical action?
- Has the budget already been consumed?
- Is the credential scope valid for the target?

### 16.4 Postcondition Limits

After mutation:

- Were required invariants preserved?
- Did the Utility produce a result within its declared contract?
- Did evidence satisfy the required proof policy?

This makes authority an execution invariant rather than a prompt instruction.

---

## 17. Planning: freedom inside a hard boundary

GluLess planning should not be defined as “the LLM writes steps.”

The planner consumes:

```text
Goal
current observations
resolved Utilities
Limits
execution history
cost/risk metadata
prior failures
```

and produces a candidate plan or next action.

The runtime then validates the candidate against deterministic constraints.

Conceptually:

```text
agent proposes
runtime disposes
```

More precisely:

```text
PROPOSE → TYPECHECK → AUTHORIZE → EXECUTE → OBSERVE → EVALUATE
```

The planner may be replaced, upgraded, specialized, or composed with symbolic planning without changing contract semantics.

This separation is a core architectural defense against model drift.

---

## 18. Goal evaluation: success must be observable

A contract is not complete because all planned steps ran.

It is complete when the Goal is satisfied under the required evidence policy.

That means GluLess needs explicit Goal evaluation.

### 18.1 Deterministic evaluation

Prefer deterministic evaluation when the state can be typed and observed:

```text
observed.version == requested.version
AND observed.health == "healthy"
```

### 18.2 Evaluator Utilities

Some Goals require querying an external system. In those cases the evaluator may invoke read-only Utilities to observe current state.

### 18.3 AI-assisted evaluation

Some outcomes are semantic rather than purely structural. For example, “the incident report contains a complete root-cause analysis supported by cited telemetry.”

AI may assist evaluation, but the contract should record:

- which evaluator/model was used;
- what evidence it inspected;
- what structured judgment it produced;
- any required threshold or secondary deterministic checks.

AI evaluation should be explicit evidence, not hidden runtime intuition.

---

## 19. Events, results, artifacts, and evidence

GluLess should define separate types for four concepts that agent frameworks often blur together.

### 19.1 Event

A fact about runtime progression.

```text
RunStarted
UtilityResolved
PlanProposed
InvocationAuthorized
InvocationStarted
InvocationCompleted
GoalSatisfied
RunFailed
```

### 19.2 Result

The structured terminal outcome of the contract run.

```text
status
final goal evaluation
outputs
cost/accounting
referenced artifacts
evidence set
failure reason if any
```

### 19.3 Artifact

A durable product created during execution:

```text
file
build
report
patch
deployment
message
record
```

### 19.4 Evidence

A record that substantiates an asserted fact.

Evidence should be addressable and preferably content-bound by digest or external immutable identity.

This supports the runtime’s core questions:

```text
What happened?
Who or what acted?
What Goal was being pursued?
Which Utility was used?
Under what authority?
What changed?
What proves the result?
```

---

## 20. Security model: authority must survive agent autonomy

Agent autonomy raises the cost of ambiguous authority because the runtime can discover paths the contract author never explicitly imagined.

GluLess should therefore adopt several non-negotiable invariants.

### 20.1 Deny is enforceable, not advisory

If a Limit denies an operation class, planner output cannot override it.

### 20.2 Approval binds to a precise action

Approval should be bound to canonical contract/action data rather than a vague conversation turn.

Where appropriate, approval records can include hashes of:

```text
contract version
Utility identity
normalized arguments
side-effect class
relevant state snapshot
```

### 20.3 Secrets are external

Credentials and secret values should not live in GluLess source. Utility resolution should use established secret and identity providers.

### 20.4 Delegation does not amplify authority

An agent delegated a task through A2A or another mechanism must receive no greater authority than the parent execution can grant.

### 20.5 Evidence and logs must not leak secrets

Observability is not permission to serialize credentials, tokens, private payloads, or sensitive intermediate model context.

Evidence must be intentionally constructed, redacted where required, and policy-aware.

---

## 21. Sovereignty, Statelessness, and Agnosticism Invariants

The architecture of GluLess is governed by a core Sovereignty Model and a strict separation of execution and storage concerns. These principles ensure that GluLess remains a portable layer above existing systems rather than a new platform dependency.

### 21.1 Stateless Core: Refusing State Custody

The GluLess runtime must never become the authoritative owner of application state. Durable domain state remains under the custody of its respective system of record (e.g., Customer state in CRM, Issue state in Git, Deployment state in Kubernetes). The runtime holds only transient execution state, including the active contract, observation history, and evidence references.

$$\text{WORLD_STATE} \neq \text{EXECUTION_STATE}$$

### 21.2 Data Sovereignty: Access does not equal Custody

Treating data under authority domains is fundamental. An executing agent having access to resources does not transfer custody of those resources to the GluLess runtime. 

*   **Access vs Ownership**: $\text{ACCESS} \neq \text{OWNERSHIP}$.
*   **Observation vs Possession**: $\text{OBSERVATION} \neq \text{POSSESSION}$.
*   **Context vs Persistence**: $\text{CONTEXT} \neq \text{PERSISTENCE}$. An agent can reason over information in its context window without the runtime assuming permanent persistence or custody.

### 21.3 Language & Protocol Agnosticism

GluLess is host-language and protocol agnostic by construction. Host-language abstractions (such as Python classes or Rust structs) are generated projections, never the defining authority of the language.

$$\text{HOST_TYPE_SYSTEM} \neq \text{GLULESS_TYPE_SYSTEM}$$

Similarly, capabilities and transport are decoupled from the core contract semantics:

$$\text{PROTOCOL} \neq \text{SEMANTICS}$$
$$\text{TRANSPORT} \neq \text{CONTRACT}$$

### 21.4 The Invariant Taxonomy

To preserve these boundaries under autonomous agent execution, the runtime enforces the following non-negotiable invariants:

*   **AUTHORITY**:
    *   $\text{CAPABILITY} \neq \text{AUTHORITY}$
    *   $\text{UTILITY_AVAILABLE} \neq \text{UTILITY_PERMITTED}$
    *   $\text{DELEGATION} \neq \text{AUTHORITY_AMPLIFICATION}$
*   **SEMANTICS**:
    *   $\text{PLAN} \neq \text{CONTRACT}$
    *   $\text{MODEL_OUTPUT} \neq \text{POLICY_DECISION}$
    *   $\text{SURFACE_SYNTAX} \neq \text{CANONICAL_SEMANTICS}$
*   **EVIDENCE**:
    *   $\text{EVENT} \neq \text{EVIDENCE}$
    *   $\text{OBSERVATION} \neq \text{POSSESSION}$
    *   $\text{ACCESS} \neq \text{OWNERSHIP}$
*   **STATE**:
    *   $\text{WORLD_STATE} \neq \text{EXECUTION_STATE}$
    *   $\text{CONTEXT} \neq \text{PERSISTENCE}$
    *   $\text{EXECUTOR} \neq \text{OWNER}$
*   **PORTABILITY**:
    *   $\text{IMPLEMENTATION_LANGUAGE} \neq \text{GLULESS_LANGUAGE}$
    *   $\text{HOST_TYPE_SYSTEM} \neq \text{GLULESS_TYPE_SYSTEM}$
    *   $\text{PROTOCOL} \neq \text{SEMANTICS}$
    *   $\text{TRANSPORT} \neq \text{CONTRACT}$
    *   $\text{UTILITY_BINDING} \neq \text{DATA_CUSTODY}$
    *   $\text{DATA_LOCATION} \neq \text{RUNTIME_LOCATION}$

---

## 22. Agent-Native Composition and Execution

To scale under autonomous agent operation, GluLess optimizes for contract assembly, modification, and evaluation directly by intelligent systems rather than manual human authoring.

### 22.1 Componentization: Composing Orthogonal Primitives

A contract is not a monolithic script, but a composition of independently addressable, versioned, and schema-validated components: Goals, Limits, Utilities, and EvidenceRequirements. Each primitive remains strictly orthogonal. A Goal specifies truth but never procedural actions; a Utility describes capability but never authorization; a Limit governs execution but never transport.

### 22.2 Utility vs. Binding Separation

A fundamental boundary separates a capability's identity and contract from its environment-specific transport configuration.

$$\text{UTILITY} \neq \text{BINDING}$$

*   **Utility**: Defines the semantic capability signature (input, output, side effects, required evidence) and is referenced inside the contract.
*   **Binding**: Defines the transport-specific implementation (an OpenAPI path, an MCP tool, or an A2A endpoint) resolved and bound dynamically by the runtime at the execution boundary.

### 22.3 Semantic Capability Selection

Runtimes support semantic query selection rather than explicit endpoint enumeration. Planners query the capability space (e.g., selecting utilities that match a domain and carry specific side-effect limits), allowing the runtime to substitute equivalent providers dynamically:

$$\text{CAN_SATISFY}(\text{required_capability}, \text{candidate_utility})$$

### 22.4 Next-Valid-Action Reasoning and Disposable Plans

GluLess does not require pre-determining an entire workflow graph before starting execution. The preferred agent execution loop evaluates next-valid-actions iteratively:

$$\text{Observe} \rightarrow \text{Propose} \rightarrow \text{Typecheck} \rightarrow \text{Authorize} \rightarrow \text{Execute} \rightarrow \text{Observe}$$

This loop repeats dynamically until the Goal evaluates to satisfied. Plans are disposable runtime artifacts:

$$\text{PLAN_IDENTITY} \neq \text{CONTRACT_IDENTITY}$$
$$\text{PLAN_FAILURE} \neq \text{CONTRACT_FAILURE}$$

A failed or discarded plan does not imply a failed contract; the runtime remains free to re-plan or resolve alternative paths.

### 22.5 Structural Reuse and Density

GluLess avoids class inheritance and super-interfaces. Components are composed structurally through composition, selection, and references. The language and IR are designed to maximize semantic density and minimize verbosity:

$$\text{SERIALIZATION} \neq \text{LANGUAGE}$$

Grammar rules that exist purely for textual convenience are excluded from the canonical IR.

---

## 23. Why not just use prompts, tool calling, or an agent framework?

Because each leaves critical semantics implicit in application code or model context.

### Prompt + tools

A prompt may tell an agent to “deploy version 2.4.1, but never delete infrastructure.” Unless an external deterministic runtime enforces that denial, the restriction is only an instruction competing with other model inputs.

### Agent framework

A framework can provide tool abstractions, graphs, checkpoints, and tracing. The application still owns the meaning of success, authorization, and evidence unless the framework defines those semantics explicitly.

### Workflow engine

A workflow engine can enforce a predetermined sequence reliably. It does not automatically define a planner-independent outcome contract or allow an agent to choose among capabilities while remaining inside a unified authority boundary.

GluLess is useful only if it moves these semantics out of ad hoc application glue and into a portable contract.

---

## 24. Why not make GluLess a general-purpose programming language?

Because that would destroy the leverage of the idea.

General-purpose languages already exist and are optimized for procedural implementation. Recreating variables, loops, classes, package management, networking, concurrency primitives, file APIs, and standard libraries would create years of work without proving the GluLess thesis.

The runtime should instead call existing software through stable interfaces.

The design test is:

```text
Does this language feature express Goal, Limits, Utility composition,
execution governance, observation, or evidence?
```

If not, the feature probably belongs in an existing implementation language or service.

---

## 25. MVP: the smallest falsifiable vertical slice

The initial MVP should prove one complete contract over one real API.

### 25.1 Required vertical slice

```text
OpenAPI document
→ import operation
→ typed Utility
→ parse contract
→ canonical IR
→ validate
→ resolve Utility
→ evaluate Limits
→ choose/construct execution action
→ execute HTTP request
→ validate response
→ observe resulting state
→ evaluate Goal
→ emit events
→ produce evidence
→ return result
```

The value of this slice is not feature count. It tests whether a contract can actually remove glue between intent, capability, authority, execution, and proof.

### 25.2 What the MVP should avoid

```text
IDE
custom database
custom scheduler
custom broker
custom auth system
custom secrets manager
new transport protocol
complex multi-agent runtime
large plugin ecosystem
visual workflow builder
proprietary event transport
```

If the slice requires one of those, first test whether an existing owner can be configured or composed.

### 25.3 A strong MVP scenario

A good demonstration has:

- at least one read Utility;
- at least one mutation Utility;
- a measurable Goal;
- one explicit denied action or approval requirement;
- observable state before and after;
- evidence independent of the planner’s narration.

For example:

```text
Goal:
  issue #418 is in state "closed" with label "verified"

Limits:
  allow issue.read
  allow issue.update
  deny repository.delete
  require evidence of final issue state

Utilities:
  imported from an OpenAPI document
```

The exact domain matters less than the completeness of the contract lifecycle.

---

## 26. The decision order should be part of runtime engineering culture

GluLess development itself should follow the same anti-glue discipline the language promotes.

```text
DELETE
→ CONFIGURE
→ COMPOSE
→ REUSE
→ EXTEND
→ CREATE
```

Before creating a new runtime subsystem:

```text
DOES_STANDARD_EXIST=
DOES_PROTOCOL_EXIST=
DOES_LIBRARY_EXIST=
DOES_API_EXIST=
CAN_EXISTING_OWNER_BE_EXTENDED=
```

This is not merely an engineering style preference. It protects the project thesis.

If GluLess needs to invent its own API description format, task protocol, event transport, secrets system, durable scheduler, and policy engine before it can execute a single contract, then it has become another platform rather than a contract layer.

---

## 27. Falsifiability: how GluLess could be wrong

A serious architecture needs conditions under which its central claim should be rejected or narrowed.

GluLess may not deserve to exist as a distinct language/runtime if any of the following become true.

### 27.1 Existing protocols converge on the complete contract

If MCP, A2A, or another broadly adopted standard gains portable first-class semantics for Goals, cross-capability Limits, planner freedom, deterministic enforcement, and evidence-backed completion, a separate GluLess layer may become redundant.

The correct response would be to contribute to or adopt the standard, not preserve GluLess by inventing artificial differentiation.

### 27.2 Goal semantics are too domain-specific

If useful Goals cannot be normalized beyond application-specific code, the language may collapse into a thin metadata wrapper around custom evaluators.

The MVP must therefore prove at least one reusable Goal/evaluator pattern.

### 27.3 Utility metadata is too weak for safe planning

If real APIs cannot provide enough side-effect, precondition, and result information for an agent to choose actions safely, GluLess may require more semantic annotation than the ecosystem will realistically maintain.

The graded Utility model should be tested directly rather than assumed sufficient.

### 27.4 Limits cannot remain portable

If authorization, approval, budget, and invariant semantics are inseparable from each deployment environment, the canonical Limit model may need to be much smaller than envisioned.

### 27.5 Evidence becomes pure application convention

If GluLess cannot define portable evidence binding and every domain simply emits arbitrary logs, then “evidence-backed execution” is branding rather than a language property.

These are valuable failure modes because they force the MVP to prove semantics rather than presentation.

---

## 28. Research questions for the language design

The following questions should remain open until implementation pressure produces evidence.

### Goal model

- Is a Goal always a predicate over observed state, or can it be a typed evaluator reference?
- How should partial satisfaction be represented?
- How are temporal Goals expressed: eventually, always, before deadline, remains true for duration?
- Can one contract contain multiple weighted alternatives, or should that remain planner policy?

### Limits model

- Which Limit primitives must be built in versus delegated to Cedar/OPA?
- How are budgets accounted across delegated agents?
- How are approval scopes canonicalized?
- How are invariants checked during long-running operations?

### Utility model

- What is the minimum metadata required before a mutation Utility may be used autonomously?
- How should Utility version compatibility work?
- Can OpenAPI links/callbacks and MCP task semantics enrich planning automatically?
- How are equivalent capabilities from multiple providers ranked without embedding provider policy in the contract?

### Evidence model

- What is the canonical evidence envelope?
- When is an HTTP response evidence, and when must the runtime re-observe state independently?
- Should evidence be content-addressed by default?
- How should evidence redaction interact with auditability?

### Planner interface

- Should planning be “next action” iterative by default or produce bounded multi-step plans?
- What planner state belongs in canonical events versus private model reasoning?
- How does the runtime safely recover when the world violates declared Utility effects?

These questions should be driven by failing tests and real execution traces, not speculative syntax design.

---

## 29. A proposed runtime boundary

A minimal implementation can preserve clean ownership through a small set of interfaces.

```text
Parser
  source -> IR

Validator
  IR -> valid | diagnostics

UtilityImporter
  external interface description -> Utility definitions

UtilityResolver
  Utility reference -> executable binding

LimitEvaluator
  contract + proposed invocation + state -> decision

Planner
  Goal + Limits + Utilities + observations -> candidate action/plan

Executor
  authorized invocation -> execution outcome

Observer
  system state -> typed observation

GoalEvaluator
  Goal + observation + evidence -> satisfied | unsatisfied | indeterminate

EventSink
  canonical runtime event -> transport/storage adapter

EvidenceStore
  evidence object -> durable reference
```

The interfaces matter more than class names. Their purpose is to keep deterministic semantic ownership separate from model-driven planning.

---

## 30. Testing model

Semantic changes should use test-driven development.

Required areas include:

```text
parser
IR canonicalization
schema/type validation
Utility import
Utility resolution
Limit evaluation
authority
approval handling
Goal evaluation
execution
response validation
events
evidence
results
```

A useful test discipline is:

```text
1. add failing semantic test
2. prove failure
3. implement smallest correction
4. prove targeted pass
5. run broader suite
6. run real integration where behavior crosses a protocol boundary
7. retain evidence
```

Completion reports should prefer evidence over confidence language:

```text
TEST=
RESULT=
EVIDENCE=
```

For mutations:

```text
AUTHORITY=
SIDE_EFFECT=
STATE_BEFORE=
STATE_AFTER=
EVIDENCE=
```

This makes the project’s own development process consistent with its runtime philosophy.

---

## 31. Positioning: what GluLess is and is not

### GluLess is

- an agent-native executable contract language;
- a typed canonical IR;
- a runtime for governed capability selection and execution;
- a composition layer over existing APIs and agent protocols;
- a place to bind Goal, Limits, Utilities, execution events, and evidence;
- planner-agnostic by design;
- protocol-reuse-first.

### GluLess is not

- another general-purpose programming language;
- an API description standard replacing OpenAPI;
- a tool transport replacing MCP;
- an agent communication protocol replacing A2A;
- a frontend protocol replacing AG-UI;
- a new policy engine replacing Cedar or OPA;
- a workflow engine replacing Temporal;
- a secrets manager;
- a database;
- a message broker;
- a requirement that humans hand-author a new syntax.

This boundary is the project’s strongest defense against scope expansion.

---

## 32. The deeper thesis: APIs are becoming the instruction set for agents

Modern software already exposes enormous portions of the world through typed or semi-typed APIs. OpenAPI describes HTTP operations. MCP exposes model-facing tools and resources. A2A exposes other agents. Cloud platforms expose infrastructure. Git providers expose repositories, reviews, issues, builds, and deployments. SaaS systems expose business state.

From an agent’s perspective, these capabilities increasingly resemble an instruction set.

But an instruction set alone is not a program.

An agent still needs:

```text
what must become true
what it may and may not do
which capabilities are in scope
how execution is accounted
what proves completion
```

That is the role GluLess is attempting to formalize.

The language therefore need not be large. Its leverage comes from connecting existing capability ecosystems to a small, stable execution contract.

---

## 33. Conclusion

The emerging agent stack is already rich in protocols and runtimes. OpenAPI describes APIs. MCP exposes tools and context. A2A lets independent agents interoperate. AG-UI connects agent runtimes to interactive frontends. Cedar and OPA provide deterministic policy evaluation. Temporal and related systems provide durable execution. CloudEvents standardizes event envelopes. Terraform and PDDL demonstrate useful ideas around desired state and planning.

GluLess should not reproduce these systems.

Its opportunity is the layer between them:

```text
GOAL
what must become true

LIMITS
what governs every possible execution path

UTILITIES
what typed capabilities can be used

EXECUTION
what permitted path an agent selects

EVIDENCE
what proves the Goal was actually achieved
```

If that layer can be made typed, portable, deterministic where it must be deterministic, intelligent where intelligence adds value, and thin enough to compose existing standards, then GluLess becomes more than an agent framework convention.

It becomes an executable contract model for autonomous software.

**GLU = Goal · Limits · Utilities.**

**The contract is the program.**

**No glue required.**

---

# References and primary sources

[1] OpenAPI Initiative. *OpenAPI Specification v3.1.1.* https://spec.openapis.org/oas/v3.1.1.html

[2] Model Context Protocol. *Specification, revision 2025-11-25.* https://modelcontextprotocol.io/specification/2025-11-25

[3] Model Context Protocol. *Authorization and Tools specifications.* https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization and https://modelcontextprotocol.io/specification/2025-11-25/server/tools

[4] Agent2Agent Protocol. *A2A Protocol Specification 1.0.0.* https://a2a-protocol.org/dev/specification/

[5] AG-UI Protocol. *Events and State Management documentation.* https://github.com/ag-ui-protocol/ag-ui and https://docs.ag-ui.com/

[6] Cedar Policy Language. *Reference Guide and Authorization semantics.* https://docs.cedarpolicy.com/

[7] Open Policy Agent. *Policy Language / Rego.* https://www.openpolicyagent.org/docs/policy-language

[8] Temporal Technologies. *Temporal Platform Documentation.* https://docs.temporal.io/

[9] Amazon Web Services. *AWS Step Functions state machines.* https://docs.aws.amazon.com/step-functions/latest/dg/concepts-statemachines.html

[10] LangChain. *LangGraph overview and persistence documentation.* https://docs.langchain.com/oss/python/langgraph/overview

[11] HashiCorp. *Terraform Configuration Language Overview.* https://developer.hashicorp.com/terraform/language

[12] Planning.wiki. *Planning Domain Definition Language (PDDL) reference.* https://planning.wiki/guide/whatis/pddl

[13] Cloud Native Computing Foundation. *CloudEvents.* https://cloudevents.io/

Additional relevant standards:

- JSON Schema Draft 2020-12: https://json-schema.org/draft/2020-12
- gRPC: https://grpc.io/docs/
- W3C SHACL: https://www.w3.org/TR/shacl/
- W3C PROV: https://www.w3.org/TR/prov-overview/
- OMG Decision Model and Notation (DMN): https://www.omg.org/dmn/

---

## Editorial notes for curation

This draft deliberately makes several choices that should remain subject to implementation evidence:

1. **“Language” means canonical contract semantics, not necessarily a human-authored syntax.** A future surface language can be optional.
2. **GluLess is positioned above protocols rather than against them.** If an existing standard grows to own a GluLess semantic cleanly, GluLess should reuse it.
3. **Evidence is elevated to a first-class concept.** This is one of the most differentiating claims and should be tested in the first vertical slice.
4. **The MVP should import OpenAPI first.** This provides the fastest path from an established typed interface to a real Utility invocation.
5. **Limits are broader than authorization.** Policy-engine reuse is encouraged, but budgets, approvals, invariants, and evidence requirements may require runtime-native enforcement.
6. **The paper intentionally avoids inventing final syntax.** Syntax should follow the IR and runtime semantics, not lead them.
