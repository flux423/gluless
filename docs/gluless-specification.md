# gluless Specification (v0.1.0)

## 1. Philosophy
gluless is a typed, declarative contract system for describing desired state, authority, capabilities, constraints, and evidence, from which intelligent runtimes derive and execute permitted plans.

Unlike traditional agent frameworks that focus on orchestrating prompt flows or tool calls, gluless separates **intent and boundaries** from **execution logic**. It defines the boundaries of a solution space. Agents may reason freely inside that space, but every consequential action must resolve to a typed, authorized, observable operation.

The runtime discovers implementations, the planner derives candidate execution graphs, and the policy engine validates security boundaries deterministically.

---

## 2. Computational Model

The lifecycle of a gluless contract execution follows a strict pipeline:

```
[Declaration (gluless)]
          │
          ▼
      [Resolver]          ← (Discovers available agent/resource capabilities)
          │
          ▼
  [Capability Graph]
          │
          ▼
      [Planner]          ← (Derives candidate execution graphs)
          │
          ▼
   [Policy Engine]       ← (Eliminates forbidden graphs deterministically)
          │
          ▼
   [Execution Graph]
          │
          ▼
      [Executor]          ← (Performs typed operations)
          │
          ▼
    [Event Ledger]        ← (Records state changes & evidence)
```

---

## 3. Core Primitives

The core language model of gluless is built upon the following distinct primitives:

*   **gluless**: The top-level declarative contract containing goals, invariants, and authority definitions.
*   **entity**: A typed domain object within the system (e.g., `City`, `Repository`, `DoltDatabase`).
*   **state**: The current attribute values of an entity.
*   **goal**: A desired condition that the system must bring about.
*   **invariant**: A condition that must never be violated during execution.
*   **capability**: An interface exposing a group of resources or potential actions.
*   **operation**: A specific, typed, executable method on a capability.
*   **authority**: The permission layer defining what operations are allowed, denied, or require approval.
*   **policy**: Governance rules restricting capability execution.
*   **constraint**: Hard limits on performance, cost, or resource utilization.
*   **event**: An immutable record of a state transition or system occurrence.
*   **evidence**: Verifiable proof that a state transition or goal has been achieved.
*   **artifact**: A generated output or document resulting from an operation.
*   **approval**: A human or system gate authorizing a specific plan or execution step.
*   **result**: The verified outcome of the contract execution.

---

## 4. Type System

All entities, capabilities, operations, and evidence in gluless are strictly typed. This prevents runtime interpretation errors and ensures static validation is mathematically provable.

Types include:
*   Primitive types (`string`, `boolean`, `integer`, `float`, `datetime`).
*   Domain types (defined by schemas representing platform resources).
*   State types (representing finite state machine statuses).

---

## 5. Identity Model

All actors—including human operators, planner runtimes, and fanned-out specialist agents—must execute under a clear, verifiable identity. Identities are bound to specific cryptographic keys or platform principals and carry semantic names (e.g., `GITLAB_OPERATOR_IDENTITY`).

---

## 6. Capability Model

A capability is a discoverable interface. It describes *what* resource is available, whereas an operation defines *how* to interact with it. 

Example:
*   **Capability:** `GitLab.MergeRequest`
*   **Operation:** `GitLab.MergeRequest.merge`

Protocol adapters (e.g., MCP, A2A, CLI, REST) implement capabilities.

---

## 7. Authority Model

Authority is declarative and evaluated prior to execution. The planner proposes actions, but a separate, deterministic policy engine approves or denies them.

*   `allow <operation>`: Permits the operation within the solution space.
*   `allow <operation> when <condition>`: Conditional authorization.
*   `require approval for <operation>`: Inserts a human-in-the-loop gate.
*   `deny <operation>`: Explicitly forbids the operation under any planning tree.

---

## 8. State Model

The system operates as a state transition machine. Every operation takes the system from state $S_n$ to $S_{n+1}$. Transitions are valid only if they conform to the authority model and do not violate any declared invariants.

---

## 9. Policy Model

Policies define global constraints across projects, runtimes, and teams. They are enforced at the organization or platform level, ensuring that even if a local gluless file permits an action, a global policy can override and block it (e.g., forbidding plaintext secrets in command-line arguments).

---

## 10. Goal and Invariant Semantics

*   **Goal**: Evaluates to `true` when the desired state is reached. Runtimes plan backward from goals.
*   **Invariant**: Must evaluate to `true` at every step of the execution graph. If any candidate plan violates an invariant at step $i$, that path is eliminated.

---

## 11. Event Model

The runtime emits structured, typed events for every transition, plan evaluation, and execution step. Events are written to an immutable stream, providing traceability.

---

## 12. Evidence Model

Success is not declared by the executor; it is verified independently via evidence. Evidence consists of cryptographic signatures, API query results, or check hashes demonstrating that the goal state has actually been achieved.

---

## 13. Planner Contract

The planner takes the gluless declaration, current state, capability graph, and policies, and solves for a valid execution path.

```
Current State + Goal + Capabilities + Invariants = Execution Plan
```

If the specification is unsatisfiable (e.g., a required capability is missing or blocked by policy), compilation fails statically.

---

## 14. Execution Graph

The Execution Graph is the concrete plan derived by the planner for a specific state of the world. While the gluless contract is declarative and long-lived, the execution graph is imperative, detailed, and ephemeral.

---

## 15. Runtime Contract

The runtime executes the execution graph step-by-step. If a step fails, the runtime halts, updates the current state, and invokes the planner to derive a recovery execution path, ensuring no invariants are violated during recovery.

---

## 16. Protocol Adapters

Protocol adapters (e.g., MCP servers, A2A messaging, HTTP clients, SQL interfaces) connect capabilities to real-world software. They are pluggable and independent of the core gluless language.

---

## 17. Human Approval Semantics

When an operation requires approval, the execution graph pauses, serializes its current state and proposed step, and exposes a human-interface gate. The human review is supported by the generated evidence and execution path.

---

## 18. Failure Semantics

Failure is typed. If an operation fails, the system classifies the failure (e.g., `AUTHORIZATION_DENIED`, `RESOURCE_NOT_FOUND`, `NETWORK_TIMEOUT`) and triggers fallback paths defined in the authority or policy engine.

---

## 19. Versioning

Contracts carry semantic versions (e.g., `v0.1.0`). If a capability interface updates, the contract must be recompiled to verify that dependencies and operations remain valid against the new capability signature.

---

## 20. Sovereignty Model

gluless enforces a multi-dimensional Sovereignty Model to protect state, data, and execution independence:

*   **Contract Sovereignty**: The gluless contract remains portable and independent of a particular executor.
*   **Data Sovereignty**: Data stays under the authority, location, retention, and access rules of its actual owner.
*   **Runtime Sovereignty**: A gluless runtime can operate independently; no canonical centralized gluless service is required.
*   **Implementation Sovereignty**: Utilities and runtimes may use any implementation language, protocol, platform, model, or infrastructure as long as they satisfy the canonical contract.

---

## 21. Non-Negotiable Invariants

All gluless implementations and runtimes must enforce these invariants at all times, organized by category:

### AUTHORITY
*   **CAPABILITY != AUTHORITY**: The discovery or availability of a capability (such as an MCP tool or OpenAPI endpoint) does not grant permission to invoke it.
*   **UTILITY_AVAILABLE != UTILITY_PERMITTED**: Capability availability is separate from authority constraints.
*   **DELEGATION != AUTHORITY_AMPLIFICATION**: Delegated agents or fanned-out task execution receive no more authority than the parent contract allows.
*   **AVAILABLE_CREDENTIAL != AUTHORIZED_ACTION**: The runtime resolves the minimum authority required for the exact permitted invocation.
*   **AMBIENT_CAPABILITY != CONTRACT_CAPABILITY**: Ambient capabilities are separate from contract capabilities.

### SEMANTICS
*   **PLAN != CONTRACT**: A proposed execution plan is an ephemeral implementation detail. Only the contract defines the authoritative goal and boundaries.
*   **MODEL_OUTPUT != POLICY_DECISION**: AI-driven planners suggest candidate steps; authorization and policy boundaries are decided deterministically by the runtime.
*   **SURFACE_SYNTAX != CANONICAL_SEMANTICS**: The canonical language is the Intermediate Representation (IR). All text formats (like `.glu`) are non-normative projections.
*   **SERIALIZATION != LANGUAGE**: The semantic model is the typed relationship graph; serialization formats (JSON, CBOR, etc.) are projections.
*   **DERIVED_SUBGOAL != CONTRACT_GOAL**: Planner-derived intermediate subgoals are distinct from contract-level goals.
*   **PLAN_IDENTITY != CONTRACT_IDENTITY**: Plans are disposable runtime products and carry separate identities.

### EVIDENCE
*   **EVENT != EVIDENCE**: An event ledger captures telemetry of what was attempted; only evidence provides independent verification of the actual outcome.
*   **OBSERVATION != POSSESSION**: An agent can observe something without gluless copying it into permanent store.
*   **ACCESS != OWNERSHIP**: The agent having access to data does not mean the runtime acquires ownership of it.
*   **EXECUTION_LOG != COMPLETION_PROOF**: An execution log captures actions; it does not prove goal satisfaction.

### STATE
*   **WORLD_STATE != EXECUTION_STATE**: The gluless runtime holds transient execution state (references, observations, history) but does not duplicate or assume ownership of the world's authoritative domain state (which remains with CRM, Git, Kubernetes, etc.).
*   **CONTEXT != PERSISTENCE**: An agent can reason over information in its context window without gluless assuming permanent custody of that information.
*   **EXECUTOR != OWNER**: gluless governs the invocation and evaluates results; it does not have to own or run the executor.

### PORTABILITY
*   **IMPLEMENTATION_LANGUAGE != GLULESS_LANGUAGE**: Runtimes and adapters may use Python, Rust, Go, etc., but the gluless language remains independent of host language types or systems.
*   **HOST_TYPE_SYSTEM != GLULESS_TYPE_SYSTEM**: Host-language types (Python classes, Rust structs) are generated projections of gluless types, not the defining authority.
*   **PROTOCOL != SEMANTICS**: OpenAPI, MCP, A2A, gRPC are capability sources or transport protocols; they do not define gluless semantics.
*   **TRANSPORT != CONTRACT**: The transport is replaceable; the contract remains immutable.
*   **UTILITY_BINDING != DATA_CUSTODY**: Binding a capability does not imply custody of its processed data.
*   **DATA_LOCATION != RUNTIME_LOCATION**: Execution location is decoupled from data residency/jurisdiction.
*   **CAPABILITY_IDENTITY != TRANSPORT_IDENTITY**: Capability identification is distinct from the transport method used to reach it.
*   **UTILITY != BINDING**: The utility defines capability semantics; the binding defines environment-specific transport details.

### EXECUTION
*   **PLAN_FAILURE != CONTRACT_FAILURE**: A failed plan does not imply a failed contract; the runtime may resolve alternative paths.
*   **CONCURRENCY != CONTRACT_SEMANTICS**: Runtimes infer concurrency from dependency independence; scheduling is decoupled from contract declaration.
*   **SCHEDULING != CONTRACT_SEMANTICS**: The scheduling sequence is derived, not declared (unless timing is part of the Goal or Limits).

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

### 22.4 Semantic Capability Selection
Runtimes support selecting capabilities via semantic queries, preventing tight coupling to provider-specific names:
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

    invariant {
        MergeRequest("ReleaseGate").predecessors.all(mr => mr.state == "merged")
        CI.pipeline("release/v0.1.x").status == "success"
    }

    observe {
        GitLab.MergeRequest
        GitLab.Pipeline
    }

    capabilities {
        GitLab.MergeRequest.inspect
        GitLab.MergeRequest.merge
        GitLab.Pipeline.inspect
    }

    authority {
        allow GitLab.MergeRequest.inspect
        allow GitLab.Pipeline.inspect
        
        allow GitLab.MergeRequest.merge 
            when MergeRequest.target == "main"
            
        require approval
            for GitLab.MergeRequest.merge 
            when MergeRequest.has_conflicts == true
    }

    success {
        MergeRequest("ReleaseGate").merged == true

        evidence {
            git.commit_exists(MergeRequest.merge_commit_sha)
            pipeline.passed(MergeRequest.merge_commit_sha)
        }
    }
}

---

## 25. Persistent Utility Registry & Ephemeral Context Resolver

### 25.1 Philosophy & Separation of Concerns
To allow runtimes and planners to discover capabilities dynamically without overwhelming context windows, gluless decouples durable knowledge representation from ephemeral reasoning:
*   **UtilityRegistry**: A persistent, canonical repository of normalized capability interfaces. Cached from OpenAPI specs, GraphQL schemas, or MCP servers.
*   **ExperienceIndex**: A persistent database tracking empirical telemetry (success rates, latencies, observed side effects) collected across runtimes.
*   **ContextResolver**: Ephemerally constructs a bounded `ContextProjection` containing only the relevant, ranked utilities, goals, and limits for the planner.

### 25.2 Core Invariants
1.  `KNOWLEDGE != CONTEXT`: Durable registry metadata persists across runs; agent prompt context remains ephemeral and minimal.
2.  `CONTEXT != SOURCE_OF_TRUTH`: Projected context is discardable and run-scoped.
3.  `DECLARED_SEMANTICS != OBSERVED_BEHAVIOR`: Declare schemas and contracts statically; record observed execution anomalies dynamically.
4.  `PAST_SUCCESS != CURRENT_AUTHORITY`: Experience metrics optimize capability choice; they never expand permissions.
5.  `UTILITY != BINDING`: A utility represents a logical capability; a binding maps to its target HTTP, gRPC, or MCP endpoint.
6.  `STATELESS_RUNTIME != NO_PERSISTENCE`: The runtime remains stateless and reconstructable; discovery catalogs and experience indexes may be persistent.
