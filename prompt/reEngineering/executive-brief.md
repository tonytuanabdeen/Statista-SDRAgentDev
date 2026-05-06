# LNA Nova: Prompt Builder Re-Engineering
## Executive Approval Brief

---

# Slide 1 — Why Re-Engineer Now

## The Problem

LNA Nova (Agentforce SDR) generates outreach emails across four topics: Initial Outreach, Follow-up Nudges, Meeting Responses, and Opt-Out handling. Today, only **1 of 4 topics** uses Salesforce Prompt Builder — the other three embed all email generation logic (~8,000 words) directly inside topic instructions, forcing the AI planner to simultaneously orchestrate actions AND compose emails.

## Business Impact of Current State

| Issue | Risk | Example |
|-------|------|---------|
| **Inconsistent output quality** | Planner-generated emails drift in tone, structure, and compliance across invocations | Nudge emails sometimes include sign-offs, vary in length, or miss the reframe requirement |
| **Spelling locked to UK English** | Cannot serve US market leads with US English conventions | Every email says "organisation" and "colour" regardless of lead's country |
| **Fragile record updates** | Planner must remember exact Salesforce picklist values (e.g., "Customer Not Interested" not "Not Interested") | Incorrect field values cause downstream automation failures |
| **High maintenance cost** | Changing email logic requires editing XML topic instructions, redeploying the entire agent bundle | No version control, no A/B testing, no prompt iteration workflow |
| **Cannot scale to new markets/regions** | Adding a new locale, industry, or cadence stage means rewriting topic instructions | No modular pattern to extend |

## The Ask

Approve the re-engineering effort to migrate all four topics to the **Prompt Builder framework** with **locale-aware spelling** (UK + US English), establishing a scalable pattern for future agent expansion.

---

# Slide 2 — Target Architecture

## Design: Topic → Flow → Prompt Template

Every topic follows one pattern. The AI planner's only job is to invoke a single Flow action. The Flow handles data retrieval, locale resolution, prompt template invocation, and record updates.

```
  ┌──────────────────┐     ┌────────────────────┐     ┌──────────────────────┐
  │   TOPIC          │     │   FLOW              │     │   PROMPT TEMPLATE    │
  │                  │     │                     │     │                      │
  │  2 instructions: │────▶│  1. Get Lead (+Country)  │  │  Full generation     │
  │  - What to do    │     │  2. Resolve Locale  │────▶│  logic with dynamic  │
  │  - Guardrails    │     │  3. Call PT          │     │  SpellingLocale      │
  │                  │     │  4. Update records  │     │  input               │
  │  Planner decides │     │  5. Return email    │     │                      │
  │  WHEN, not HOW   │     │     (deterministic) │     │  LLM decides HOW     │
  └──────────────────┘     └────────────────────┘     └──────────────────────┘
       Scope &                  Orchestration &             Generation &
       Guardrails               Record Updates              Personalisation
```

## Locale Resolution (New Capability)

```
Lead.Country ──▶ Flow Decision ──▶ SpellingLocale ("UK" or "US") ──▶ Prompt Template
                      │
                      ├── US, USA, United States, territories → "US"
                      └── Everything else (default)           → "UK"
```

- **Deterministic**: Flow-side decision, not LLM judgment
- **Extensible**: Add Australian English or other variants by adding one Decision branch
- **Safe default**: UK English (matches current production behaviour)

---

# Slide 3 — What Changes

## Component Inventory: Before vs After

| Component | Current State | Re-Engineered State |
|-----------|--------------|---------------------|
| **Topic Instructions** | 21 instructions across 4 topics (~8,000 words of prompt logic in XML) | 8 instructions (~800 words — scope + guardrails only) |
| **Prompt Builder Templates** | 2 (Persona Detection + Outreach Email) | 5 (+ Follow-Up Nudge, Meeting Response, Opt-Out Response) |
| **Orchestration Flows** | 2 (Initial Outreach + Update Lead Record) | 5 (+ Follow-Up Nudge, Meeting Response, Opt-Out Response) |
| **Record Update Logic** | Mixed — 2 in Flows, 2 rely on planner to set exact picklist values | 100% in Flows — all field values hardcoded declaratively |
| **Planner Reasoning per Topic** | 3-5 steps (action calls + email composition) | 1 step (invoke flow) |
| **Spelling Locales** | 1 (UK only, hardcoded) | 2 (UK + US, dynamic per Lead.Country) |
| **Country Queried in Flows** | 0 of 2 flows | 4 of 5 flows (all customer-facing) |

## New Deliverables

| # | Deliverable | Type | Effort |
|---|------------|------|--------|
| 1 | `LNA_Nova_Follow_Up_Nudge` | Prompt Template + Flow | Migrate 6 topic instructions → 1 PT |
| 2 | `LNA_Nova_Meeting_Response` | Prompt Template + Flow | Migrate 7 topic instructions → 1 PT |
| 3 | `LNA_Nova_Opt_Out_Response` | Prompt Template + Flow | Migrate 6 topic instructions → 1 PT + classification branching |
| 4 | Locale Resolution Layer | Flow Decision pattern (x4 flows) | Country → SpellingLocale mapping |
| 5 | `LNA_Nova_Outreach_Email` update | PT modification | Add SpellingLocale input, replace hardcoded UK constraint |
| 6 | `LNA_Nova_Initial_Outreach` update | Flow modification | Add Country to query, add locale resolve |
| 7 | All 4 topic updates | PlannerBundle modification | Reduce instructions, swap actions |
| 8 | US English test suite | Test data + references | Clone UK tests with Country = "United States" |

---

# Slide 4 — Delivery Plan & Estimates

## Phased Rollout (4 Phases + Foundation)

```
Phase 0 ─────── Phase 1 ─────── Phase 2 ─────── Phase 3 ─────── Phase 4
Locale          Follow-Up       Meeting         Opt-Out         Cleanup &
Foundation      Outreach        Response        Response        Deployment
                                                                
Update          Create PT       Create PT       Create PT       US test suite
existing        + Flow          + Flow          + Flow +        package.xml
flow + PT       Update topic    Update topic    branching       Full regression
                                                Update topic    Deploy
                                                                
~2 days         ~3 days         ~3 days         ~4 days         ~2 days
                                                                
LOW RISK        LOW RISK        MEDIUM RISK     HIGHEST RISK    ─────────
No new          No record       1 record        3 update        
components      updates         update          branches +      
                                                compliance      
```

## Effort Summary

| Phase | Scope | Estimate | Risk |
|-------|-------|----------|------|
| **Phase 0** — Locale Foundation | Update existing Initial Outreach flow + PT for locale support | **2 days** | Low — modifies existing working components with additive change |
| **Phase 1** — Follow-Up Outreach | New PT + Flow, update topic (no record updates) | **3 days** | Low — simplest topic, no data mutations |
| **Phase 2** — Meeting Response | New PT + Flow, update topic (Rating update moves to Flow) | **3 days** | Medium — includes lead owner resolution + record update |
| **Phase 3** — Manage Opt-Out | New PT + Flow, update topic (3-way classification branch + compliance fields) | **4 days** | Highest — branching update logic, exact picklist values, HasOptedOutOfEmail flag |
| **Phase 4** — Cleanup & Deploy | US test suite, package.xml, full regression, deploy | **2 days** | Low — testing and deployment only |
| | | **Total: ~14 days** | |

Each phase is independently deployable. If any phase encounters issues, previous phases remain stable in production.

## Key Dependencies

- Salesforce org access for scratch org testing
- Knowledge articles (persona profiles, ICP content) must remain published
- Country field values in the org must be validated against the locale mapping table

---

# Slide 5 — Return on Investment & Scale Readiness

## Immediate Returns

| Benefit | Metric | Impact |
|---------|--------|--------|
| **US market readiness** | Spelling locales: 1 → 2 | Enables US lead outreach without manual email editing |
| **Output consistency** | Planner reasoning steps: 3-5 → 1 | Emails follow the same structure every time — no planner drift |
| **Record update reliability** | LLM-dependent field values: 3 topics → 0 | Zero risk of incorrect picklist values breaking downstream automation |
| **Prompt iteration speed** | Edit Prompt Template in Prompt Builder UI → publish | No agent bundle redeployment needed for email content changes |
| **Maintenance reduction** | Topic instruction words: ~8,000 → ~800 | 90% less prompt logic to review, debug, and version |

## Future Scale: What This Pattern Enables

The re-engineered architecture creates a **repeatable pattern** for adding new capabilities:

| Future Scenario | What to Build | Pattern |
|-----------------|--------------|---------|
| **New locale** (e.g., Australian English, German-market English) | 1 Decision branch per Flow | Add country values to existing locale resolve — no new components |
| **New industry** (beyond Manufacturing + Telco & IT) | 1 ICP Knowledge article + Flow branch | Same as current Manufacturing/Telco pattern |
| **New cadence stage** (e.g., "Re-Engage" for dormant leads) | 1 Topic + 1 Flow + 1 PT | Follow the established Topic → Flow → PT pattern |
| **New agent** (e.g., Customer Success Rep) | Clone pattern, swap prompts | The architecture is agent-agnostic — the pattern transfers directly |
| **A/B testing email variants** | PT version management in Prompt Builder | Test new prompt versions without touching Flows or Topics |
| **Model swap** (e.g., Gemini → Claude) | Change `primaryModel` in PT metadata | Model selection is isolated in the PT layer — no Flow or Topic changes |

## Architecture Maturity Comparison

```
                    CURRENT                          RE-ENGINEERED
                    
    Topic ──────── Planner ──────── Action      Topic ──── Flow ──── PT
    (8K words)    (reasons +       (simple)     (800       (orchestr.  (generation
                   composes)                     words)     + locale)   + locale)
    
    Monolithic         ◄──────►                  Modular        ◄──────►
    Fragile            ◄──────►                  Deterministic  ◄──────►
    UK-only            ◄──────►                  Locale-aware   ◄──────►
    1 topic works      ◄──────►                  All 4 topics   ◄──────►
    right (Initial                               follow same
    Outreach)                                    pattern
```

## Recommendation

Approve the 14-day re-engineering effort across 5 phases. The investment pays for itself immediately through US market enablement and compounds over time as each new locale, industry, or agent reuses the established pattern without architectural rework.
