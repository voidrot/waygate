# Structured Consensus Plan

This document is the design anchor for Epic `#8` issue `#40`: prototype structured-consensus compilation across multiple review paths.

## Purpose

WayGate's compiler currently uses a single draft path and a single review path with a bounded revise-and-retry loop. This plan defines how the compiler could evolve toward structured consensus without replacing the current LangGraph-based workflow or implying that multi-model compilation already exists.

## Current Compiler Baseline

Implemented today:

- The graph entrypoint is `draft`.
- `draft` produces one candidate draft from the current raw document set.
- `review` evaluates that single draft against the raw source material.
- Approved drafts route to `publish`.
- Rejected drafts loop back to `draft` until the revision limit is hit.
- Three failed review cycles escalate to `human_review`.
- Middleware hooks already wrap nodes for auditing and tracing.

This means the structured-consensus roadmap should extend the existing graph and state model rather than inventing a separate compiler system.

## Non-Negotiable Constraints

1. Consensus remains grounded in the same raw source material used by the current compiler.
2. The existing Draft -> Review -> Publish path must remain a valid fallback.
3. Any consensus design must preserve auditability, trace correlation, and publish provenance.
4. Human review remains the terminal safety valve for unresolved disagreement.
5. Consensus work must stay prototype-oriented and avoid implying provider procurement or production cost commitments.

## What Structured Consensus Means For WayGate

For this system, structured consensus means generating multiple independent judgments about the same synthesis task, then combining them through an explicit policy rather than trusting a single draft-review pass.

Recommended consensus dimensions:

- multiple draft candidates from different models or prompt variants
- multiple review passes over one draft
- cross-critique where reviewers compare competing drafts
- explicit disagreement capture rather than silent averaging

## Candidate Consensus Modes

### Mode 1: Multi-review on a single draft

- Keep one `draft` node.
- Run two or more review passes over the same draft.
- Aggregate reviewer outcomes into one approval decision.

Benefits:

- smallest graph change
- easiest to layer onto the current state model
- lowest additional token cost among consensus options

Tradeoffs:

- draft quality still depends on a single writer path
- consensus is limited to critique diversity, not synthesis diversity

### Mode 2: Multi-draft with comparative review

- Generate two or more candidate drafts.
- Run one or more comparative reviews that score or critique the candidates.
- Select, merge, or request revision based on comparative outcomes.

Benefits:

- stronger protection against one bad drafting pass
- makes disagreement visible at the content level

Tradeoffs:

- materially higher cost and latency
- requires richer state handling and aggregation logic

### Mode 3: Hybrid consensus

- Generate multiple drafts.
- Run multiple independent reviews.
- Add an aggregation or adjudication step that resolves disagreements.

Benefits:

- strongest confidence model
- clearest foundation for future provenance of uncertainty

Tradeoffs:

- most expensive and operationally complex
- least deterministic unless tightly bounded

## Recommended Prototype Direction

The first prototype after this planning slice should prefer multi-review on a single draft.

Why:

- it fits the current compiler graph with the least disruption
- it reuses the current `draft` prompt and node shape
- it gives immediate signal on disagreement handling without multiplying synthesis cost

## Suggested Graph Evolution

Recommended future graph roles:

- `draft`: produce the candidate draft as it does today
- `review_primary`: current review-style grounded QA
- `review_secondary`: independent critique pass using a separate model, prompt variant, or policy overlay
- `consensus_gate`: aggregate reviewer outcomes and decide `publish`, `revise`, or `human_review`
- `publish`: unchanged final publish step

This preserves the current graph structure while inserting a narrow consensus decision point before publish.

## Suggested State Evolution

The current `GraphState` is optimized for one draft and one reviewer. A future consensus prototype likely needs additional state, for example:

- `draft_candidates`: list of candidate drafts when multi-draft mode is enabled
- `review_outcomes`: list of structured reviewer results
- `consensus_decision`: final aggregated approval state
- `consensus_strategy`: active mode such as `single_review`, `multi_review`, or `multi_draft`
- `consensus_notes`: explanation of disagreement or merge rationale

The existing fields should remain meaningful:

- `current_draft` remains the publish candidate or selected winner
- `qa_feedback` remains the human-readable revision guidance
- `revision_count` still bounds retry loops
- `status` still drives routing

## Middleware And Hook Strategy

The current middleware wrapper is already the right seam for consensus instrumentation.

Future hook responsibilities could include:

- recording which model or prompt variant produced each draft or review outcome
- attaching consensus metadata to audit events
- capturing disagreement counts and adjudication outcomes in spans
- enforcing experimental flags for consensus-enabled runs

This keeps consensus observability aligned with the existing tracing and audit model.

## Decision Policy

Recommended initial aggregation rules:

- unanimous approval -> publish
- any severe grounding failure -> revise
- repeated reviewer disagreement after bounded retries -> human_review

The first prototype should avoid opaque weighted scoring. Explicit rules are easier to reason about, test, and audit.

## Determinism, Cost, And Latency Tradeoffs

- Determinism decreases as the number of models and adjudication steps grows.
- Cost increases roughly linearly with each extra draft or review pass.
- Latency increases with every additional serial step unless some reviewer passes are parallelized.

For those reasons, the first prototype should keep the consensus surface small and bounded.

## Relationship To Missing Context And Retrieval

Structured consensus is adjacent to, but separate from, the retrieval roadmap.

- Missing-context handling should distinguish missing knowledge from reviewer disagreement.
- Consensus retries should not be used to mask true corpus gaps.
- If reviewers disagree because source material is insufficient, the future missing-context loop should become the next step instead of infinite draft retries.

The later provenance-evaluation roadmap is documented in
`docs/cryptographic_provenance_plan.md` because consensus confidence and
cryptographic attestation solve different problems.

## Human Review Boundary

Human review should remain the final boundary for unresolved consensus failures.

- repeated disagreement
- high-severity grounding violations
- conflict between reviewers that cannot be resolved by the policy gate

This preserves the current safety posture while making consensus failure explicit.

## Prototype Recommendation

For the first implementation-oriented prototype after this planning slice:

1. Add a second review path only.
2. Keep a single draft candidate.
3. Add a small `consensus_gate` node that aggregates structured review outcomes.
4. Preserve the current `publish` and `human_review` endpoints.

This validates the graph and state changes with the lowest operational risk.

## Follow-On Issue Split

Reasonable implementation splits after this plan:

- graph/state refactor for multiple review outcomes
- second review node with independent prompt or model configuration
- consensus gate and routing rules
- observability and audit expansion for reviewer disagreement

## Acceptance Mapping For Issue #40

- Concrete prototype plan: this document defines consensus modes, the recommended first prototype, and graph changes.
- Grounded in the current compiler: it builds directly on the existing Draft -> Review -> Publish flow, GraphState, and middleware.
- Clear follow-on work: graph/state, reviewer expansion, and consensus-gate tasks are separable.

## Explicitly Deferred

- Full production rollout of multi-model compilation.
- Provider procurement or cost governance.
- Automatic consensus across arbitrary numbers of models.
- Replacing the current single-path compiler outright.
