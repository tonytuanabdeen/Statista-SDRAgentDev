# LNA Nova 2.0 v3: Meeting Response — Scalable Architecture

## Scope

This document covers the **Meeting Response** topic only. It refactors the V1 instruction-heavy planner design into a Flow Orchestration + Prompt Template architecture, incorporating learnings from V2 and new platform capabilities (`OwnerMeetingLink__c` formula field).

---

## Problem Statement (V1)

The Meeting Response topic currently uses **7 topic instructions (~2,800 words)** plus 2 planner actions (`GetRecordDetails`, `LNA_Nova_Update_Lead_Record`). This creates:

| Problem | Impact |
|---------|--------|
| Planner must recall meeting link URL | Hardcoded in instructions; breaks if URL changes |
| Planner must determine field values (`Rating = "Warm"`) | Picklist prediction risk |
| Planner must sequence actions (generate → update) | Ordering errors skip record updates |
| No locale support | UK English only; no path to US/APAC expansion |
| Planner resolves seller name via `GetRecordDetails` | Unnecessary token cost per invocation |
| Meeting link is static (one shared booking URL) | Cannot scale to per-owner booking links |

---

## V3 Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Planner = Router** | 2 instructions: purpose + guardrails |
| **Flow = Orchestrator** | Deterministic record lookups, locale resolution, seller/meeting-link resolution, DML, conversation logging |
| **PT = Generator** | Email generation with locale-aware spelling and tone |
| **Zero planner-side DML** | `Rating = "Warm"` + `LeadDescription__c` merge happen in Flow |
| **Dynamic meeting link** | `OwnerMeetingLink__c` formula (→ `Owner:User.MeetingLink__c`) replaces hardcoded URL |
| **Locale as input** | Flow resolves Country → locale; PT generates in correct dialect |

---

## V1 → V3 Comparison

| Aspect | V1 (Current) | V3 (Target) |
|--------|--------------|-------------|
| Topic instructions | 7 (~2,800 words) | 2 (~200 words) |
| Planner actions | 2 (`GetRecordDetails` + `Update Lead Record`) | 1 (Flow action) |
| Record updates | Planner-side (error-prone) | Flow DML (deterministic) |
| Locale | None (UK only) | Dynamic (en-GB default, en-US, extensible) |
| Meeting link source | Hardcoded URL in Instruction 3 | `Lead.OwnerMeetingLink__c` formula field |
| Seller name source | `GetRecordDetails` snapshot | `Lead.Owner.Name` (direct lookup) |
| Conversation logging | None | PT `summary` field → Apex merge → `LeadDescription__c` |
| Token budget per turn | ~2,800 words + GetRecordDetails response | ~200 words |

---

## Component Architecture

```
Agent Topic: Meeting Response (2 instructions)
  │
  └── Flow Action: LNA_Nova_Meeting_Response
        │
        ├── 1. Get Lead Record
        │     Fields: Id, FirstName, Title, Country, OwnerId, 
        │             Owner.Name, OwnerMeetingLink__c, LeadDescription__c
        │
        ├── 2. Resolve Locale
        │     Decision: Country → en-US | en-GB (default)
        │
        ├── 3. Validate Meeting Link
        │     Decision: OwnerMeetingLink__c blank? → Fault path
        │
        ├── 4. Call Prompt Template: LNA_Nova_Meeting_Response_Email
        │     Inputs: Lead, EmailBody, SellerName, MeetingLink, Locale
        │     Output: JSON { reply, summary }
        │
        ├── 5. Parse Response (Apex Invocable)
        │     Extract: varReplyBody, varSummary
        │
        ├── 6. Update Lead: Rating = "Warm" (deterministic)
        │
        ├── 7. Merge + Update LeadDescription__c (Apex Invocable)
        │
        └── 8. Return varEmailOutput
```

---

## New: Dynamic Meeting Link via `OwnerMeetingLink__c`

V1 hardcodes `https://outlook.office365.com/book/sales@statista.com/` in topic instructions. V2 moved it to a Flow variable (still hardcoded, just in one place).

**V3** uses the new formula field:

```xml
<CustomField>
    <fullName>OwnerMeetingLink__c</fullName>
    <formula>Owner:User.MeetingLink__c</formula>
    <label>Owner Meeting Link</label>
    <type>Text</type>
</CustomField>
```

This resolves the meeting link dynamically from the Lead Owner's User record. Benefits:
- Each seller maintains their own booking link
- Changing a seller's link requires no agent/Flow/PT updates
- Works across reassigned leads automatically
- Fallback: if blank, Flow creates a Task rather than sending an email without a meeting link

---

## Retired Components (post-migration)

| Component | Reason |
|-----------|--------|
| `GetRecordDetails_179bY000001jeX4` | Lead + Owner data retrieved inside Flow |
| `LNA_Nova_Update_Lead_Record_179bY000001jeX4` | Rating update + LeadDescription merge now in Flow DML |
| Hardcoded meeting link in Instruction 3 | Replaced by `OwnerMeetingLink__c` formula |
| 7 topic instructions | Replaced by 2 (purpose + guardrails) |

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| PT returns malformed JSON | Apex parser returns null → Flow fault path → Task for Lead Owner |
| `OwnerMeetingLink__c` is blank (Owner has no link) | Flow Decision: if blank, create Task and stop |
| Locale detection edge cases | Default to en-GB for unknown/blank countries; Decision node is extensible |
| LeadDescription__c merge overflow | Apex enforces 5-bullet cap, oldest bullets dropped |
| Regression in cadence routing | `ruleExpressions` unchanged; `Reply` stage still routes to this topic |

---

## Flex Credit Impact

| Component | V1 Cost | V3 Cost | Delta |
|-----------|---------|---------|-------|
| Planner context (instructions) | ~2,800 tokens/turn | ~200 tokens/turn | -93% |
| GetRecordDetails action | 1 invocation | 0 | -100% |
| PT call (new) | 0 | 1 Flex call | +1 |
| Apex parser (new) | 0 | Negligible (in-transaction) | — |

Net: significant planner token reduction, one additional PT call. The token savings offset the PT cost for most volumes.
