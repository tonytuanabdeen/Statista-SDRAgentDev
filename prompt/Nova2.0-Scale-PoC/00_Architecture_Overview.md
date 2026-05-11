# LNA Nova 2.0: Scalable Architecture PoC

## Current State

| Topic | Instructions | Pattern | Spelling | Record Updates |
|-------|-------------|---------|----------|----------------|
| Initial Outreach | 2 | Flow + 2 PTs | UK hardcoded in PT | Flow DML |
| Follow-up Outreach | 6 | Instruction-based | None | None |
| Meeting Response | 7 | Instruction-based | None | Planner guesses Rating |
| Manage Opt-Out | 6 | Instruction-based | None | Planner recalls picklist values |

## Target Pattern (all 4 topics)

```
Topic (2 instructions: scope + guardrails)
  └── Flow Action (deterministic orchestration)
        ├── Get Lead Record (incl. Country)
        ├── Resolve Locale (Country → en-GB / en-US)
        ├── Call Prompt Template (with locale param)
        ├── Deterministic Record Updates (exact values, no planner involvement)
        └── Return email content to agent
```

## Locale Resolution (reusable pattern)

```
Decision: Resolve_Locale
  Rule: "US Locale"
    Condition: Lead.Country IN ("United States", "US", "USA")
    → varLocale = "en-US"
  Default:
    → varLocale = "en-GB"
```

## Net-New Deliverables

| Component | API Name | Purpose |
|-----------|----------|---------|
| Flow | `LNA_Nova_Follow_Up_Outreach` | Orchestrates nudge generation + locale |
| Flow | `LNA_Nova_Meeting_Response` | Orchestrates reply + seller resolution + Rating update |
| Flow | `LNA_Nova_Manage_Opt_Out` | Orchestrates classification + branching + unqualify DML |
| Prompt Template | `LNA_Nova_Follow_Up_Nudge` | Generates follow-up nudge emails |
| Prompt Template | `LNA_Nova_Meeting_Response_Email` | Generates meeting response emails |
| Prompt Template | `LNA_Nova_Opt_Out_Response` | Classifies reply + generates opt-out response |

## Slim Topic Instructions (post-refactor)

Each topic retains exactly 2 instructions:

1. **Purpose** — tells the planner what Flow to invoke and what input to pass
2. **Guardrails** — hard constraints the planner must never violate

## Impact

| Metric | V1 | V2 |
|--------|----|----|
| Topic instructions | 21 (~8,000 words) | 8 (~800 words) |
| Prompt Templates | 2 | 5 |
| Orchestration Flows | 2 | 5 |
| Record updates via planner | 2 topics | 0 |
| Locale support | 1 (UK only) | 2+ (dynamic) |
| Picklist prediction risk | High | Zero |
