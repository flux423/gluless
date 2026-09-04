# Implementation Plan — Semantic Normalization & Architectural Restructuring of GluLess Docs

This plan details the steps required to align the GluLess specification and whitepapers with the three-plane model, clean up obsolete runtime graphs, re-order and correct subsection numbering, and normalize terminology (Capability, Utility, Binding, Limits).

---

## Proposed Changes

### 1. Update the Specification (`docs/gluless-specification.md`)
*   **Ontology Realignment**: Frame the core primitives around:
    *   **Primary Contract Semantics**: Goal, Limits, Utilities.
    *   **Supporting Runtime Semantics**: Observation, Evidence, Event, Result, Artifact, Binding, Approval, Identity.
    *   **Limit Subtypes**: Authority, Policy, Constraint, Invariant, Budget, ApprovalRequirement, EvidenceRequirement.
*   **Diagram Replacement**: Replace the obsolete runtime diagram at the beginning of the spec with the new Three-Plane Architecture Diagram and the detailed execution model flow.
*   **Invariant Families**: Group invariants under explicit families (`AUTHORITY`, `SEMANTICS`, `KNOWLEDGE`, `CONTEXT`, `EVIDENCE`, `STATE`, `PORTABILITY`, `EXECUTION`) rather than enforcing a fixed count.
*   **Terminology Pass**: Replace outdated terminology (`Capability Graph`, `capability interface`, etc.) with `Utility`, `Binding`, `ContextProjection`, `LimitEvaluator` definitions.

### 2. Update the Whitepaper (`docs/whitepapers/gluless_whitepaper_draft.md`)
*   **Renumber Subsections**: Programmatically renumber all subsections (e.g. `### 14.1` under `## 3.` becomes `### 3.1`, etc.).
*   **Three Planes Division**: Explicitly introduce the Contract plane, Knowledge plane, and Execution plane division early in the draft.
*   **Resolver Filtering Sequence**: Tighten the resolution rules in the Resolver/Registry section to detail:
    1.  **Filter** (deterministic compatibility: Type → Capability → Limits → Environment → Version)
    2.  **Rank** (semantic relevance → goal contribution → reliability → latency → cost → evidence quality)
    3.  **Invariants**: `COMPATIBILITY BEFORE OPTIMIZATION` and `AUTHORITY BEFORE EXPERIENCE`.

---

## Verification Plan

*   Run the Python subsection renumbering script.
*   Verify that `pytest` continues to pass with 0 failures to ensure the documentation edits do not conflict with runtime definitions.
