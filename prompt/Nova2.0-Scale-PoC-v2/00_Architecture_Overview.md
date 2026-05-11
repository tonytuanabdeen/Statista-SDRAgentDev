# LNA Nova 2.0 v2: Scalable Architecture

## Problem Statement

The V1 agent uses 21 topic instructions (~8,000 words) across 4 topics. Three of the four topics rely on the planner to:
1. Predict exact picklist values (e.g., "Customer Not Interested" vs "Not Interested")
2. Orchestrate multi-step record updates in the correct order
3. Manage locale/spelling variations inline
4. Handle meeting link injection and seller name resolution

This creates fragility at scale: picklist prediction errors, token bloat in the planner context, and no locale flexibility beyond hardcoded UK English.

## V2 Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Planner = Router** | Topic instructions tell the planner WHAT to invoke, not HOW to execute |
| **Flow = Orchestrator** | Deterministic logic (locale, record updates, seller resolution) lives in Flows |
| **PT = Generator** | Email generation with locale-aware content lives in Prompt Templates |
| **Zero planner-side DML** | All record updates are Flow DML steps — the planner never touches field values |
| **Locale as input** | Every PT accepts a `Locale` param; the Flow resolves Country → locale before calling the PT |

## Current State (V1)

| Topic | Instructions | Pattern | Spelling | Record Updates |
|-------|-------------|---------|----------|----------------|
| Initial Outreach | 2 | Flow + 2 PTs | UK hardcoded in PT | Flow DML |
| Follow-up Outreach | 6 | Instruction-based | None | None |
| Meeting Response | 7 | Instruction-based | None | Planner guesses Rating |
| Manage Opt-Out | 7 | Instruction-based | None | Planner recalls picklist values |

## Target State (V2)

| Topic | Instructions | Pattern | Spelling | Record Updates |
|-------|-------------|---------|----------|----------------|
| Initial Outreach | 2 | Flow + 2 PTs | Flow resolves locale → PT param | Flow DML |
| Follow-up Outreach | 2 | Flow + PT | Flow resolves locale → PT param | None (no updates needed) |
| Meeting Response | 2 | Flow + PT | Flow resolves locale → PT param | Flow DML (Rating = Warm) |
| Manage Opt-Out | 2 | Flow + PT | Flow resolves locale → PT param | Flow DML (Unqualify + branching) |

## Unified Flow Pattern

```
Topic (2 instructions: purpose + guardrails)
  └── Flow Action (deterministic orchestration)
        ├── Get Lead Record (incl. Country + context fields)
        ├── Resolve Locale (Country → en-GB / en-US)
        ├── [Optional] Resolve contextual data (seller name, meeting link, etc.)
        ├── Call Prompt Template (with locale + context params)
        ├── [Optional] Deterministic Record Updates (exact values, no planner involvement)
        └── Return email content to agent
```

## Locale Resolution (shared pattern across all Flows)

```
Decision: Resolve_Locale
  Rule: "US_Locale"
    Condition: Lead.Country IN ("United States", "US", "USA")
    → Assignment: varLocale = "en-US"
  Default: "Default_UK"
    → Assignment: varLocale = "en-GB"
```

## Component Inventory

### Prompt Templates (5 total)

| API Name | Type | Model | Purpose |
|----------|------|-------|---------|
| `LNA_Nova_Lead_Persona_Detection` | flex | GPT-4o-mini | Classify lead persona (existing) |
| `LNA_Nova_Outreach_Email` | einsteinSdrEmail | Gemini 2.5 Flash | Generate initial outreach (existing) |
| `LNA_Nova_Follow_Up_Nudge` | flex | Gemini 2.5 Flash | Generate follow-up nudge emails |
| `LNA_Nova_Meeting_Response_Email` | flex | Gemini 2.5 Flash | Generate meeting response emails |
| `LNA_Nova_Opt_Out_Response` | flex | Gemini 2.5 Flash | Classify reply + generate opt-out response |

### Orchestration Flows (4 total)

| API Name | Inputs | DML | Purpose |
|----------|--------|-----|---------|
| `LNA_Nova_Initial_Outreach` | LeadId | Status → Outreach | Persona detection + email gen (existing) |
| `LNA_Nova_Follow_Up_Outreach` | LeadId, emailBody, isFinalMessage | None | Locale → nudge generation |
| `LNA_Nova_Meeting_Response` | LeadId, emailBody | Rating → Warm | Seller resolution + reply gen |
| `LNA_Nova_Manage_Opt_Out` | LeadId, emailBody | Status/Reason/OptOut (branched) | Classification + unqualify |

### Retired Components (post-migration)

| Component | Reason |
|-----------|--------|
| `GetRecordDetails` (Follow-up topic) | Data retrieved inside Flow |
| `GetRecordDetails` (Meeting Response topic) | Lead + Owner data retrieved inside Flow |
| `LNA_Nova_Update_Lead_Record` (Meeting Response topic) | Rating update now in Flow DML |
| `LNA_Nova_Update_Lead_Record` (Opt-Out topic) | Unqualify logic now in Flow DML |

## Impact Summary

| Metric | V1 | V2 |
|--------|----|----|
| Topic instructions | 21 (~8,000 words) | 8 (~800 words) |
| Prompt Templates | 2 | 5 |
| Orchestration Flows | 2 | 4 |
| Record updates via planner | 2 topics | 0 |
| Locale support | 1 (UK only) | 2+ (dynamic, extensible) |
| Picklist prediction risk | High | Zero |
| Planner token budget | ~8,000 words per turn | ~800 words per turn |
| Meeting link hardcoded in instructions | Yes (2 topics) | No (Flow variable) |

## LeadDescription__c (Conversation Log)

In V1, the planner manages the `LeadDescription__c` rich-text field directly — reading existing bullets, prepending new ones, and enforcing a 5-bullet cap. This is error-prone (LLMs miscounting, dropping old bullets, reformatting HTML).

**V2 approach:** Move conversation logging to the orchestration Flows for Meeting Response and Manage Opt-Out. The PT returns a structured `summary` field in its JSON output; the Flow appends it to `LeadDescription__c` using an Assignment + Record Update. This eliminates planner-side string manipulation entirely.

## Orchestration Stage Routing (unchanged)

The `ruleExpressions` in the planner bundle remain the same:
- `OrchestrationStage = Intro` → Initial Outreach topic
- `OrchestrationStage = Nudge` → Follow-up Outreach topic
- `OrchestrationStage = Reply` → Meeting Response OR Manage Opt-Out topic

Topic scope descriptions handle the disambiguation between Meeting Response and Manage Opt-Out (positive vs. negative replies).
