# gluless Specification (v0.1.0)

## 1. Philosophy
gluless is a typed, declarative contract system for describing desired state, authority, utilities, and evidence, from which intelligent runtimes derive and execute permitted plans.

Unlike traditional agent frameworks that focus on orchestrating prompt flows or tool calls, gluless separates **intent and boundaries** from **execution logic**. It defines the boundaries of a solution space. Agents may reason freely inside that space, but every consequential action must resolve to a typed, authorized, observable utility.

---

## 2. Computational Model & The Three Planes

GluLess execution is organized across three distinct, decoupled planes:

### 2.1 The Three Planes

```text
                 CONTRACT PLANE
          Goal · Limits · Utilities
                       │
                       ▼
                 KNOWLEDGE PLANE
         Registry · Bindings · Experience
                       │
                       ▼
                 EXECUTION PLANE
 Context → Plan → Authorize → Execute → Observe
                       │
                       ▼
               Evidence · Result
                       │
                       └──► Experience
```

*   **Contract Plane**: Declares semantic requirements: Goals, Limits, Utility specifications, and Evidence criteria.
*   **Knowledge Plane**: Stores durable capability mappings: the Utility Registry (normalized specs), Bindings (transports), and the Experience Index (empirical performance telemetry).
*   **Execution Plane**: Compiles the transient Context Projection, executes the next-valid-action planning loop, routes actions through the LimitEvaluator, gathers observations, and verifies outcomes.

### 2.2 Execution Model Loop

The core execution flow follows this data and authority pipeline:

```text
                 GLULESS CONTRACT
            Goal · Limits · Utilities
                         │
                         ▼
                  Context Resolver
                         │
            ┌────────────┼────────────┐
            │            │            │
      UtilityRegistry Observations ExperienceIndex
            │            │            │
            └────────────┼────────────┘
                         ▼
                 ContextProjection
                         │
                         ▼
                       Agent
                         │
                  candidate action
                         │
                         ▼
                   LimitEvaluator
                         │
                         ▼
                       Binding
                         │
                         ▼
                      Executor
                         │
                         ▼
                  External System
                         │
                         ▼
                      Observer
                         │
                         ▼
                      Evidence
                    ┌────┴─────┐
                    │          │
             GoalEvaluator  ExperienceIndex
                    │
                    ▼
                  Result
```

---

## 3. Core Ontology

GluLess strictly aligns its language model around the following hierarchy of primitives, supporting the core thesis of **GLU (Goal · Limits · Utilities)**:

### 3.1 Primary Contract Semantics
*   **Goal**: The target success state definition or condition the runtime must bring about.
*   **Limits**: Declarative restrictions governing all execution paths, defining the boundaries of permitted behavior.
*   **Utilities**: Typed, abstract capability interfaces that are declared in the contract and can be invoked.

### 3.2 Supporting Runtime Semantics
*   **Observation**: Structured, raw telemetry measurements of system state.
*   **Evidence**: Verifiable proof (e.g. hash, cryptographic check, git commit SHA) demonstrating state transitions.
*   **Event**: Immutable ledger record representing a milestone in runtime execution.
*   **Result**: The final verified outcome of the contract run.
*   **Artifact**: Any file or output generated as a side-effect of execution.
*   **Binding**: The environment-specific transport configuration realizing a Utility interface.
*   **Approval**: A security gate requiring manual or system authorization for a specific plan or execution step.
*   **Identity**: A verified cryptographic actor or principal executing under the contract.

### 3.3 Limit Subtypes
*   **Authority**: Permissive or restrictive declarations matching utility patterns (e.g., `allow` / `deny`).
*   **Policy**: Globally inherited platform rules restricting execution parameters.
*   **Constraint**: Hardware or budget boundaries (e.g., maximum cost, time limits).
*   **Invariant**: Conditions that must evaluate to `true` at every step of execution.
*   **Budget**: Financial or resource limits allocated for the plan.
*   **ApprovalRequirement**: Conditions specifying when an explicit approval is needed.
*   **EvidenceRequirement**: Declarations of what proof is required to verify state transitions.

---

## 4. Type System

All elements, including goals, utility schemas, limit definitions, and evidence in gluless are strictly typed. This prevents runtime interpretation errors and ensures static validation is mathematically provable.

Types include:
*   Primitive types (`string`, `boolean`, `integer`, `float`, `datetime`).
*   Domain types (defined by schemas representing platform resources).
*   State types (representing finite state machine statuses).

---

## 5. Identity Model

All actors—including human operators, planner runtimes, and fanned-out specialist agents—must execute under a clear, verifiable identity. Identities are bound to specific cryptographic keys or platform principals and carry semantic names (e.g., `GITLAB\_OPERATOR\_IDENTITY`).

---

## 6. Capability, Utility, and Binding Model

A **Capability** is a semantic property describing *what* can be achieved (e.g. `issue.read`), while a **Utility** is a typed interface that provides that capability. A **Binding** realizes the utility for a specific transport endpoint (e.g. GitLab REST or MCP).

Example:
*   **Capability / Goal Requirement:** `issue.read`
*   **Utility:** `GitLab.Issues.get` (declared schema)
*   **Binding:** `https://gitlab.example.com/api/v4/projects/{id}/issues/{issue\_iid}` (HTTP transport)

---

## 7. Authority Model

Authority is declarative, defining the contract's Limits, and evaluated prior to execution. The planner proposes candidate actions, but a deterministic LimitEvaluator approves or denies them.

*   `allow <utility>`: Permits the utility invocation.
*   `allow <utility> when <condition>`: Conditional authorization.
*   `require approval for <utility>`: Inserts a human-in-the-loop gate.
*   `deny <utility>`: Explicitly forbids the utility under any planning tree.

---

## 8. State Model

The system operates as a state transition machine. Every utility execution takes the system from state $S\_n$ to $S\_{n+1}$. Transitions are valid only if they conform to the Limits.

---

## 9. Policy Model

Policies represent globally inherited Limits enforced across projects, runtimes, and teams at the organization or platform level. Even if a local contract permits a utility, global policies can override and block the execution.

---

## 10. Goal and Invariant Semantics

*   **Goal**: Evaluates to `true` when the desired state is reached. Runtimes plan next-valid-actions to satisfy the Goal.
*   **Invariant (a Limit subtype)**: Must evaluate to `true` at every step of the execution graph. If any candidate action violates an invariant, that path is blocked.

---

## 11. Event Model

The runtime emits structured, typed events for every transition, plan evaluation, and execution step. Events are written to an immutable stream, providing traceability.

---

## 12. Evidence Model

Success is not declared by the executor; it is verified independently via evidence. Evidence consists of cryptographic signatures, API query results, or check hashes demonstrating that the goal state has actually been achieved.

---

## 13. Planner Contract

The planner takes the gluless contract, current state, context projection, and active limits, and solves for a valid execution path.

```
Current State + Goal + Utilities + Limits = Execution Plan
```

If the contract is unsatisfiable (e.g., a required utility has no compatible binding or is blocked by limits), compilation fails statically.

---

## 14. Execution Graph

The Execution Graph is the concrete plan derived by the planner for a specific state of the world. While the gluless contract is declarative and long-lived, the execution graph is imperative, detailed, and ephemeral.

---

## 15. Runtime Contract

The runtime executes the execution graph step-by-step. If a step fails, the runtime halts, updates the current state, and invokes the planner to derive a recovery execution path, ensuring no limits are violated during recovery.

---

## 16. Protocol Bindings & Adapters

Protocol adapters (e.g., MCP servers, A2A messaging, HTTP clients, SQL databases) realize the concrete Bindings for abstract Utilities. They are pluggable and independent of the core gluless language.

---

## 17. Human Approval Semantics

When a utility execution step requires approval under its Limits, the runtime pauses execution, serializes its current state and proposed action, and exposes a human-interface gate. The human review is supported by the generated evidence and proposed step.

---

## 18. Failure Semantics

Failure is typed. If a utility invocation fails, the system classifies the failure (e.g., `AUTHORIZATION\_DENIED`, `RESOURCE\_NOT\_FOUND`, `NETWORK\_TIMEOUT`) and triggers fallback paths defined in the Limits or execution engine.

---

## 19. Versioning

Contracts carry semantic versions (e.g., `v0.1.0`). If a utility interface or schema updates, the contract must be recompiled to verify that dependencies and utility signatures remain valid.

---

## 20. Sovereignty Model

gluless enforces a multi-dimensional Sovereignty Model to protect state, data, and execution independence:

*   **Contract Sovereignty**: The gluless contract remains portable and independent of a particular executor.
*   **Data Sovereignty**: Data stays under the authority, location, retention, and access rules of its actual owner.
*   **Runtime Sovereignty**: A gluless runtime can operate independently; no canonical centralized gluless service is required.
*   **Implementation Sovereignty**: Utilities and runtimes may use any implementation language, protocol, platform, model, or infrastructure as long as they satisfy the canonical contract.

---

## 21. Non-Negotiable Invariant Families

All gluless implementations, tools, and runtimes must enforce these invariants at all times, organized by core architectural families:

### AUTHORITY
*   **UTILITY\_AVAILABLE != UTILITY\_PERMITTED**: The discovery or availability of a capability binding does not grant authority to invoke it.
*   **DELEGATION != AUTHORITY\_AMPLIFICATION**: Delegated agents or fanned-out sub-task execution receive no more authority than the parent contract allows.
*   **PAST\_SUCCESS != CURRENT\_AUTHORITY**: Telemetry and historical success rate statistics may optimize choice ranking; they never expand authorization or override Limits.
*   **EXPERIENCE != POLICY**: Telemetry indexes inform planning priority; Limits enforce hard boundary policy rules.
*   **AVAILABLE\_CREDENTIAL != AUTHORIZED\_ACTION**: The runtime resolves the minimum authority required for the exact permitted invocation.

### SEMANTICS
*   **PLAN != CONTRACT**: A proposed execution plan is an ephemeral implementation detail. Only the contract defines the authoritative Goal and Limits.
*   **MODEL\_OUTPUT != POLICY\_DECISION**: AI-driven planners suggest candidate next actions; authorization and Limits enforcement are decided deterministically by the runtime.
*   **SURFACE\_SYNTAX != CANONICAL\_SEMANTICS**: The canonical language is the Intermediate Representation (IR). All text formats (like `.glu` or YAML) are non-normative projections.
*   **SERIALIZATION != LANGUAGE**: The semantic model is the typed relationship graph; serialization formats (JSON, CBOR, etc.) are projections.
*   **DERIVED\_SUBGOAL != CONTRACT\_GOAL**: Planner-derived intermediate subgoals are distinct from contract-level Goals.

### KNOWLEDGE
*   **KNOWLEDGE != CONTEXT**: Durable capability catalogs and experience telemetry persist across execution runs; reasoning context remains minimal and run-scoped.
*   **DECLARED\_SEMANTICS != OBSERVED\_BEHAVIOR**: Declare schemas and contract limits statically; record observed execution anomalies dynamically under separate observed layers.
*   **INFERENCE != FACT**: Empirical inferences generated by model execution must not silently mutate canonical registry definitions without formal promotion rules.

### CONTEXT
*   **CONTEXT != SOURCE\_OF\_TRUTH**: Projected context is discardable, run-scoped, and non-authoritative.
*   **CONTEXT != PERSISTENCE**: An agent can reason over information in its context window without the runtime assuming permanent custody or storage.

### EVIDENCE
*   **EVENT != EVIDENCE**: An event ledger captures telemetry of what was attempted; only evidence provides independent verification of the actual outcome.
*   **OBSERVATION != POSSESSION**: An agent can observe something without gluless copying the underlying database or files into permanent store.
*   **ACCESS != OWNERSHIP**: The agent having access to data does not mean the runtime acquires ownership of it.
*   **EXECUTION\_LOG != COMPLETION\_PROOF**: An execution log captures actions; it does not prove goal satisfaction.

### STATE
*   **WORLD\_STATE != EXECUTION\_STATE**: The gluless runtime holds transient execution state (references, observations, history) but does not duplicate or assume ownership of the world's authoritative domain state.
*   **REGISTRY != EXECUTION\_STATE**: Registry catalogs capability schemas; runtime ledger tracks transient run states.
*   **EXECUTOR != OWNER**: gluless governs the invocation and evaluates results; it does not have to own or run the executor.

### PORTABILITY
*   **IMPLEMENTATION\_LANGUAGE != GLULESS\_LANGUAGE**: Runtimes and adapters may use Python, Rust, Go, etc., but the gluless language remains independent of host language types.
*   **HOST\_TYPE\_SYSTEM != GLULESS\_TYPE\_SYSTEM**: Host-language types are generated projections of gluless types, not the defining authority.
*   **PROTOCOL != SEMANTICS**: OpenAPI, MCP, A2A, gRPC are capability sources or transport protocols; they do not define gluless semantics.
*   **TRANSPORT != CONTRACT**: The transport is replaceable; the contract remains immutable.
*   **UTILITY != BINDING**: The utility defines capability semantics; the binding defines environment-specific transport details.
*   **CAPABILITY\_IDENTITY != PROVIDER\_IDENTITY**: Contracts target logical capability requirements rather than provider-specific endpoint identities.

### EXECUTION
*   **PLAN\_FAILURE != CONTRACT\_FAILURE**: A failed plan does not imply a failed contract; the runtime may resolve alternative paths.
*   **CONCURRENCY != CONTRACT\_SEMANTICS**: Runtimes infer concurrency from dependency independence; scheduling is decoupled from contract declaration.
*   **STATELESS\_RUNTIME != NO\_PERSISTENCE**: Runtimes remain stateless and reconstructable; discovery catalogs and experience indexes may be persistent.

---

## 22. Agent-Native Composition Model

The gluless language and runtime are designed for automated composition, inspection, and manipulation by AI agents. Human authoring and reading syntax are optional projections.

### 22.1 Component-Based Unit
The basic building blocks of gluless are discrete, typed components:
*   **Goal**: The target success state definition.
*   **Limit**: An executable constraint or policy.
*   **Utility**: An atomic capability definition.
*   **Observation**: A structured state measurement.
*   **EvidenceRequirement**: A condition verifying state transitions.

Each component carries a unique `IDENTITY`, `TYPE`, `SCHEMA`, `VERSION`, `DEPENDENCIES`, `CONSTRAINTS`, and `PROVENANCE`. A contract is a composed set of these components rather than a monolithic document.

### 22.2 Reference-Based Composition
Rather than copying full definitions, agents compose contracts by reference:
```text
goal: ref(goal://deployment/healthy@1)
limits:
  - ref(limit://production/default@3)
  - ref(limit://budget/low-risk@1)
utilities:
  - select(capability: deployment.read)
```

### 22.3 Utility vs. Binding Separation
A **Utility** represents a capability atom (e.g. `issue.read`, `deployment.create`) and defines its semantic interface. A **Binding** defines the transport details (e.g., OpenAPI HTTP, MCP, A2A) required to reach that capability in a specific environment. Contracts reference Utilities; runtimes resolve Bindings.

### 22.4 Semantic Utility Selection
Runtimes support selecting utilities via semantic capability queries, preventing tight coupling to provider-specific names:
```text
utilities:
  select(
    domain = deployment
    effects <= update
  )
```

### 22.5 Graph-Native Relationships
The gluless IR is structurally graph-compatible. The semantic core is a typed relationship graph relating Goals, Observations, Utilities, Limits, and Evidence:
$$\text{Goal} \xrightarrow{\text{requires}} \text{Observation}$$
$$\text{Limit} \xrightarrow{\text{governs}} \text{Utility}$$
$$\text{Evidence} \xrightarrow{\text{substantiates}} \text{Claim}$$

---

## 23. Runtime Authoring & Execution Loops

### 23.1 Ephemeral Context & Data Custody
By default, planner context is ephemeral, persisting only for the duration of run execution.
*   **Ephemerality**: $\text{CONTEXT} \neq \text{PERSISTENCE}$.
*   **Reference-Based Evidence**: Runtimes store digests (hashes, commit SHAs) rather than full data payloads, minimizing data custody and duplication.

### 23.2 Next-Valid-Action Reasoning
GluLess does not require agents to pre-calculate complete execution plans. The core execution loop runs iteratively:
```
[Observe State] -> [Propose Next Valid Action] -> [Typecheck/Authorize] -> [Execute] -> [Observe] -> [Evaluate Goal]
```
Execution halts as soon as the Goal evaluates to satisfied.

### 23.3 Conformance Test
To verify that a feature conforms to the agent-native architecture, it must satisfy the following validation questions:
*   Can an agent construct it directly?
*   Can it be validated deterministically?
*   Can it be composed and reused by reference without copying?
*   Can its execution binding change without changing contract semantics?
*   Does it avoid assuming custody of external application state?
*   Does it produce verifiable evidence?
*   Can it survive changes of implementation language, transport, or executor?

---

## 24. Reference Examples

### Example: Release Train Convergence

```text
gluless ReleaseConvergence {

    goal {
        MergeRequest("ReleaseGate").merged == true
    }

    limits {
        invariant: MergeRequest("ReleaseGate").predecessors.all(mr => mr.state == "merged")
        invariant: CI.pipeline("release/v0.1.x").status == "success"

        allow GitLab.MergeRequest.inspect
        allow GitLab.Pipeline.inspect
        
        allow GitLab.MergeRequest.merge 
            when MergeRequest.target == "main"
            
        require approval
            for GitLab.MergeRequest.merge 
            when MergeRequest.has\_conflicts == true
    }

    observe {
        GitLab.MergeRequest
        GitLab.Pipeline
    }

    utilities {
        GitLab.MergeRequest.inspect
        GitLab.MergeRequest.merge
        GitLab.Pipeline.inspect
    }

    success {
        MergeRequest("ReleaseGate").merged == true

        evidence {
            git.commit\_exists(MergeRequest.merge\_commit\_sha)
            pipeline.passed(MergeRequest.merge\_commit\_sha)
        }
    }
}
