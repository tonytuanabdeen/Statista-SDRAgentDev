# LNA Nova Re-Engineering Plan v2: Prompt Builder Framework + Locale-Aware Spelling

## 1. Executive Summary

This plan extends [plan.md](plan.md) with a cross-cutting concern: **locale-aware spelling**. Today all emails are hardcoded to UK English (`colour`, `organisation`, `programme`). The re-engineered architecture must support both **UK English** and **US English** (`color`, `organization`, `program`), selected dynamically based on the lead's `Country` field.

The core re-engineering strategy from plan.md remains unchanged: extract topic instructions into Prompt Builder templates orchestrated by Flows. This plan adds a **Locale Resolution Layer** that runs in every Flow, resolves the lead's country to a spelling standard, and passes it as an input to every Prompt Template. The LLM receives an explicit spelling directive per invocation rather than a static "use UK spelling" constraint.

**This plan supersedes plan.md.** All sections from plan.md are included here with locale modifications highlighted.

---

## 2. Locale Design: Country-to-Spelling Resolution

### 2.1 The Problem

- The `LNA_Nova_Outreach_Email` prompt template has `- Language: English (UK spelling and conventions)` hardcoded in its Constraints section (line 157 / line 378 across both versions).
- The Initial Outreach topic guardrail says: `Always write in English using UK spelling and conventions`.
- The Follow-up Outreach, Meeting Response, and Manage Opt-Out topic instructions contain no spelling directive at all (the planner defaults to whatever it prefers).
- Country is a merge field in the Outreach Email PT (`{!$Input:Recipient.Country}`) but is not used for spelling — it's listed as Lead Data for personalisation context only.
- The `LNA_Nova_Initial_Outreach` flow doesn't even query the Country field from the Lead record.

### 2.2 Design Decision: Flow-Side Resolution, Not LLM-Side

**Option A (rejected):** Pass Country to the Prompt Template and let the LLM decide which spelling standard to use based on the country name.

Problem: LLMs are unreliable at consistently applying spelling rules, especially for subtle differences (`analyse` vs `analyze`, `licence` vs `license`). They also hallucinate country-to-locale mappings (is "Ireland" UK or US spelling?). Country values in Salesforce can be free-text, abbreviated, or non-standard.

**Option B (selected):** Resolve Country to a `SpellingLocale` string (`UK` or `US`) deterministically in the Flow using a Decision element, then pass the resolved locale as a dedicated Prompt Template input. The PT receives an unambiguous directive: `Write in UK English` or `Write in US English`.

Advantages:
- Deterministic: the mapping is a declarative lookup, not an LLM judgment call.
- Testable: you can unit-test the Flow's country-to-locale decision independently.
- Extensible: adding a third locale (e.g., Australian English) means adding one Decision branch, not rewriting every prompt.
- Consistent: every email for a given country always gets the same spelling — no drift between invocations.

### 2.3 Country-to-Locale Mapping

The Flow Decision element maps `Lead.Country` to one of two locales. The mapping follows this logic:

**US English** applies when the lead's country is in the United States or a US territory where American English is the dominant business convention:

| Country Value (case-insensitive) | Locale |
|----------------------------------|--------|
| `United States` | US |
| `United States of America` | US |
| `US` | US |
| `USA` | US |
| `U.S.` | US |
| `U.S.A.` | US |
| `Puerto Rico` | US |
| `Guam` | US |
| `US Virgin Islands` | US |
| `American Samoa` | US |

**UK English** applies for all other countries (default). This is the safe default because:
- The current production agent already uses UK English exclusively.
- Statista's UK sales team initiated this agent — the existing email tone, examples, and test baselines are all UK English.
- UK English is standard business English in most non-US anglophone markets (UK, Ireland, Australia, New Zealand, South Africa, India, Hong Kong, Singapore, EU countries receiving English-language outreach).

**Implementation in Flow**: A single Decision element with one rule:
- **Rule: "US Locale"** — `Lead.Country` matches any value in the US list (use OR conditions or a Collection Contains check).
- **Default Outcome: "UK Locale"** — everything else, including blank/null Country values.

The resolved locale is stored in a `varSpellingLocale` text variable with value `US` or `UK`.

### 2.4 Prompt Template Spelling Directive

Every Prompt Template that generates customer-facing text receives a new input:

| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `SpellingLocale` | `primitive://String` | Yes | `UK` or `US` — resolved by the Flow |

Each template's Constraints section replaces the static spelling rule with a dynamic directive:

**Before** (current, hardcoded):
```
- Language: English (UK spelling and conventions)
```

**After** (dynamic):
```
## Spelling & Language

Locale: {!$Input:SpellingLocale}

If Locale is "UK": Write in British English. Use UK spelling and conventions throughout 
(e.g., colour, organisation, programme, centre, analyse, behaviour, travelled, licence [noun]).

If Locale is "US": Write in American English. Use US spelling and conventions throughout 
(e.g., color, organization, program, center, analyze, behavior, traveled, license).

This applies to every word in the email — subject line, body, and CTA. Do not mix 
conventions. If unsure about a specific word, default to the locale specified above.
```

This directive is explicit, provides concrete examples for the most commonly confused words, and tells the LLM not to mix conventions within a single email.

### 2.5 Spelling Differences Reference

For prompt engineering clarity, here are the key differences the LLM must handle:

| Category | UK English | US English |
|----------|-----------|------------|
| **-our / -or** | colour, behaviour, favour, honour | color, behavior, favor, honor |
| **-ise / -ize** | organise, analyse, recognise, specialise | organize, analyze, recognize, specialize |
| **-re / -er** | centre, metre, fibre | center, meter, fiber |
| **-mme / -m** | programme | program |
| **-ce / -se (nouns)** | licence, practice (noun) | license, practice |
| **-lled / -led** | travelled, cancelled, modelled | traveled, canceled, modeled |
| **-ogue / -og** | catalogue, dialogue | catalog, dialog |
| **Vocabulary** | whilst, amongst, towards | while, among, toward |

These examples should be embedded in a shared Knowledge article or included in each PT's spelling section for LLM reference.

---

## 3. Current Architecture Analysis

*(Carried forward from plan.md with locale annotations)*

### 3.1 What Exists Today

| Component | Type | Status | Locale Handling |
|-----------|------|--------|-----------------|
| `Agentforce_Sales_Development_Rep.genAiPlannerBundle` | GenAiPlannerBundle | 4 topics, 1 global action, 3 rule expressions | No spelling directives in Follow-up/Meeting/Opt-Out topics |
| `LNA_Nova_Lead_Persona_Detection.genAiPromptTemplate` | GenAiPromptTemplate | Published (GPT-4o Mini) | N/A — outputs a persona label, not customer-facing text |
| `LNA_Nova_Outreach_Email.genAiPromptTemplate` | GenAiPromptTemplate | Published (Gemini 2.5 Flash) | Hardcoded: `Language: English (UK spelling and conventions)` |
| `LNA_Nova_Initial_Outreach.flow` | AutoLaunchedFlow | Active | Does not query Lead.Country |
| `LNA_Nova_Update_Lead_Record.flow` | AutoLaunchedFlow | Active | N/A — no text generation |
| `v1.botVersion` | BotVersion | 7 conversation variables | No locale variable |

### 3.2 Locale Gaps in Current Architecture

1. **Outreach Email PT** has Country as a merge field (`{!$Input:Recipient.Country}`) but only uses it for personalisation context — the spelling constraint is hardcoded to UK.
2. **Initial Outreach Flow** queries Id, Title, LeadRole__c, Company, Industry, Name, Email — **Country is not in the queriedFields list**, so even though the PT references `Recipient.Country`, the value is always null when the Lead SObject is passed via the Flow query.
3. **Topic instructions** for Follow-up, Meeting Response, and Opt-Out contain no spelling guidance at all. The planner defaults to whatever the model produces (typically US English for most LLMs).
4. **Initial Outreach topic guardrail** says "Always write in English using UK spelling and conventions" — but this is a topic instruction, not a PT constraint, so it competes with the PT's own constraint when the agent passes through the planner.

---

## 4. Target Architecture

### 4.1 Design Principles

1. **Separation of Concerns**: Topic instructions define *what* and *when*. Prompt Templates define *how to generate*. Flows define *how to orchestrate*.
2. **Planner Simplicity**: Reduce each topic to: understand the task → invoke one flow action → return the result.
3. **Deterministic Record Updates**: All field update logic in Flows, not planner reasoning.
4. **Consistent Pattern**: `Topic → Flow → Prompt Template(s)` for every topic.
5. **Locale as a First-Class Input**: Every Flow resolves `Lead.Country` → `SpellingLocale`. Every customer-facing PT accepts `SpellingLocale` as a required input. No hardcoded spelling directives anywhere.

### 4.2 Architecture Diagram

```
                        ┌─────────────────────────────────┐
                        │   Sales Cadence Orchestrator     │
                        │  (sets OrchestrationStage var)   │
                        └──────────────┬──────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                   │
              Stage=Intro        Stage=Nudge         Stage=Reply
                    │                  │                   │
                    ▼                  ▼                   ▼
        ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐
        │ Initial       │  │ Follow-up     │  │ Reply Router      │
        │ Outreach      │  │ Outreach      │  │ (planner selects) │
        │ Topic         │  │ Topic         │  └────────┬──────────┘
        │ (2 instr.)    │  │ (2 instr.)    │      ┌────┴────┐
        └───────┬───────┘  └───────┬───────┘      │         │
                │                  │               ▼         ▼
                ▼                  ▼         ┌──────────┐ ┌─────────┐
        ┌───────────────┐  ┌───────────────┐ │ Meeting  │ │ Manage  │
        │ Flow:         │  │ Flow:         │ │ Response │ │ Opt-Out │
        │ LNA_Nova_     │  │ LNA_Nova_     │ │ Topic    │ │ Topic   │
        │ Initial_      │  │ Follow_Up_    │ │(2 instr.)│ │(2 instr)│
        │ Outreach      │  │ Nudge         │ └────┬─────┘ └────┬────┘
        └───────┬───────┘  └───────┬───────┘      │            │
                │                  │               ▼            ▼
                │                  │         ┌───────────┐ ┌───────────┐
                │                  │         │ Flow:     │ │ Flow:     │
                │                  │         │ LNA_Nova_ │ │ LNA_Nova_ │
                │                  │         │ Meeting_  │ │ Opt_Out_  │
                │                  │         │ Response  │ │ Response  │
                │                  │         └─────┬─────┘ └─────┬─────┘
                │                  │               │             │
       ┌────────┼────────┐        │               │             │
       │        │        │        │               │             │
       ▼        ▼        ▼        ▼               ▼             ▼
   ┌───────┐┌───────┐┌───────┐┌───────┐    ┌───────────┐ ┌───────────┐
   │ PT:   ││ PT:   ││ Locale││ Locale│    │ PT:       │ │ PT:       │
   │Persona││Outrea-││Resolve││Resolve│    │ Meeting   │ │ Opt-Out   │
   │Detect ││ch     ││  (in  ││  (in  │    │ Response  │ │ Response  │
   │       ││Email  ││ flow) ││ flow) │    └───────────┘ └───────────┘
   └───────┘└───────┘└───────┘└───────┘           │             │
                │                  │          ┌────┴────┐   ┌────┴────┐
                │                  │          │ Locale  │   │ Locale  │
                │                  │          │ Resolve │   │ Resolve │
                │                  │          │(in flow)│   │(in flow)│
                │                  │          └─────────┘   └─────────┘
                │                  │
        ┌───────┴───────┐         │
        │  SpellingLocale│        │
        │  passed to PT  │        │
        │  as input      │        │
        └────────────────┘        │
                            ┌─────┴──────┐
                            │SpellingLoc.│
                            │passed to PT│
                            └────────────┘
```

**Key Change**: Every Flow now includes a **Locale Resolve** step between Get Lead Record and the PT invocation. The resolved `SpellingLocale` (UK or US) is passed as a dedicated input to each customer-facing Prompt Template.

### 4.3 Simplified Locale Flow Pattern

Every Flow that generates customer-facing email follows this sub-pattern:

```
Get Lead Record (with Country field)
        │
        ▼
Decision: Resolve Locale
        ├── Country IN (US values) → Assign varSpellingLocale = "US"
        └── Default              → Assign varSpellingLocale = "UK"
        │
        ▼
Call Prompt Template (SpellingLocale = varSpellingLocale)
```

This is implemented once per Flow as a reusable 3-element pattern (Decision + 2 Assignments). It adds minimal complexity and keeps locale resolution deterministic.

---

## 5. Deliverables

### 5.1 New GenAiPromptTemplates (3)

| # | Template Name | Model | Inputs | Output | Migrated From |
|---|--------------|-------|--------|--------|---------------|
| 1 | `LNA_Nova_Follow_Up_Nudge` | Gemini 2.5 Flash | Lead (SObject), PreviousEmailBody (String), IsFinalMessage (String), **SpellingLocale (String)** | JSON: `{ subject, body }` | Follow-up Outreach Instructions 1-5 |
| 2 | `LNA_Nova_Meeting_Response` | Gemini 2.5 Flash | Lead (SObject), LeadReply (String), LeadOwnerName (String), PreviousSubject (String), **SpellingLocale (String)** | JSON: `{ subject, body }` | Meeting Response Instructions 1-5 |
| 3 | `LNA_Nova_Opt_Out_Response` | Gemini 2.5 Flash | LeadReply (String), PreviousSubject (String), **SpellingLocale (String)** | JSON: `{ classification, subject, body }` | Manage Opt-Out Instructions 1-4 |

### 5.2 Modified GenAiPromptTemplate (1)

| # | Template Name | Change |
|---|--------------|--------|
| 1 | `LNA_Nova_Outreach_Email` | Add `SpellingLocale` input. Replace hardcoded `Language: English (UK spelling and conventions)` with dynamic spelling directive using `{!$Input:SpellingLocale}`. |

### 5.3 New Flows (3)

| # | Flow Name | Type | Purpose |
|---|-----------|------|---------|
| 1 | `LNA_Nova_Follow_Up_Nudge` | AutoLaunchedFlow | Get Lead (with Country) → Resolve Locale → Call PT → Return email |
| 2 | `LNA_Nova_Meeting_Response` | AutoLaunchedFlow | Get Lead + Owner (with Country) → Resolve Locale → Call PT → Update Lead (Rating=Warm) → Return email |
| 3 | `LNA_Nova_Opt_Out_Response` | AutoLaunchedFlow | Get Lead (Country only) → Resolve Locale → Call PT → Parse classification → Branch updates → Return email |

### 5.4 Modified Flows (1)

| # | Flow Name | Change |
|---|-----------|--------|
| 1 | `LNA_Nova_Initial_Outreach` | Add `Country` to queriedFields on Get Lead Record. Add Locale Resolve decision. Pass `SpellingLocale` to `LNA_Nova_Outreach_Email` PT invocation. |

### 5.5 Modified Topics (4)

| # | Topic | Change |
|---|-------|--------|
| 1 | Initial Outreach | Remove "Always write in English using UK spelling and conventions" from guardrails (now handled by PT + Flow). |
| 2 | Follow-up Outreach | Reduce from 6 → 2 instructions. Remove Get Record Details action. Add new flow action. |
| 3 | Meeting Response | Reduce from 7 → 2 instructions. Remove both actions. Add new flow action. |
| 4 | Manage Opt-Out | Reduce from 6 → 2 instructions. Remove Update Lead Record action. Add new flow action. |

### 5.6 No-Change Components

| Component | Reason |
|-----------|--------|
| `LNA_Nova_Lead_Persona_Detection` PT | Outputs a persona label — not customer-facing text, no spelling needed |
| `LNA_Nova_Update_Lead_Record` flow | Generic record update, no text generation |
| Bot version + conversation variables | No new conversation variables needed — locale is resolved in Flows |
| Rule expressions | Routing logic unchanged |

---

## 6. Detailed Implementation Phases

### Phase 0: Locale Foundation (Cross-Cutting — Do First)

This phase creates the locale infrastructure that all subsequent phases depend on.

#### 6.0.1 Update Existing Flow: `LNA_Nova_Initial_Outreach`

**Changes to** `force-app/main/default/flows/LNA_Nova_Initial_Outreach.flow-meta.xml`:

**Step 1 — Add Country to Lead query**:

Add `Country` to the `Get_Lead_Record` element's `queriedFields`:
```xml
<queriedFields>Id</queriedFields>
<queriedFields>Title</queriedFields>
<queriedFields>LeadRole__c</queriedFields>
<queriedFields>Company</queriedFields>
<queriedFields>Industry</queriedFields>
<queriedFields>Name</queriedFields>
<queriedFields>Email</queriedFields>
<queriedFields>Country</queriedFields>   <!-- NEW -->
```

**Step 2 — Add Locale Resolution Decision**:

Insert after `Get_Lead_Record` and before the existing `Lead_Title_Provided` decision:

```
Decision: Resolve_Spelling_Locale
├── Rule: US_Locale
│   Conditions (OR logic):
│     - Get_Lead_Record.Country EqualTo "United States"
│     - Get_Lead_Record.Country EqualTo "United States of America"
│     - Get_Lead_Record.Country EqualTo "US"
│     - Get_Lead_Record.Country EqualTo "USA"
│     - Get_Lead_Record.Country EqualTo "U.S."
│     - Get_Lead_Record.Country EqualTo "U.S.A."
│     - Get_Lead_Record.Country EqualTo "Puerto Rico"
│     - Get_Lead_Record.Country EqualTo "Guam"
│     - Get_Lead_Record.Country EqualTo "US Virgin Islands"
│     - Get_Lead_Record.Country EqualTo "American Samoa"
│   → Assignment: varSpellingLocale = "US"
│   → Connector: Lead_Title_Provided
│
└── Default: UK_Locale
    → Assignment: varSpellingLocale = "UK"
    → Connector: Lead_Title_Provided
```

**Step 3 — Add variable**:

```xml
<variables>
    <name>varSpellingLocale</name>
    <dataType>String</dataType>
    <isCollection>false</isCollection>
    <isInput>false</isInput>
    <isOutput>false</isOutput>
</variables>
```

**Step 4 — Pass locale to PT invocation**:

In the `Generate_Outreach_Email` action call, add:
```xml
<inputParameters>
    <name>Input:SpellingLocale</name>
    <value>
        <elementReference>varSpellingLocale</elementReference>
    </value>
</inputParameters>
```

#### 6.0.2 Update Existing PT: `LNA_Nova_Outreach_Email`

**Changes to** `force-app/main/default/genAiPromptTemplates/LNA_Nova_Outreach_Email.genAiPromptTemplate-meta.xml`:

**Step 1 — Add SpellingLocale input** (in both template versions):

```xml
<inputs>
    <apiName>SpellingLocale</apiName>
    <definition>primitive://String</definition>
    <masterLabel>SpellingLocale</masterLabel>
    <referenceName>Input:SpellingLocale</referenceName>
    <required>true</required>
</inputs>
```

**Step 2 — Replace static spelling constraint** (in both template versions):

**Find**:
```
- Language: English (UK spelling and conventions)
```

**Replace with**:
```
## Spelling & Language

Locale: {!$Input:SpellingLocale}

If Locale is "UK": Write in British English using UK spelling and conventions throughout 
(e.g., colour, organisation, programme, centre, analyse, behaviour, travelled, licence [noun], 
whilst, amongst, towards).

If Locale is "US": Write in American English using US spelling and conventions throughout 
(e.g., color, organization, program, center, analyze, behavior, traveled, license, 
while, among, toward).

Apply the specified locale to every word in the email — subject line, body, and CTA. 
Do not mix conventions within a single email.
```

#### 6.0.3 Update Initial Outreach Topic Guardrail

**Find** in topic Instruction 2:
```
- Always write in English using UK spelling and conventions (e.g., colour, organisation, 
programme, centre, travelled). Do NOT use US spelling.
```

**Replace with**:
```
- The flow determines the correct spelling locale (UK or US English) based on the lead's 
country. Do not override the spelling in the returned email.
```

#### 6.0.4 Testing Phase 0

| Test | Input | Expected Outcome |
|------|-------|-----------------|
| UK lead | Lead.Country = "United Kingdom" | Email uses UK spelling (colour, organisation, programme) |
| US lead | Lead.Country = "United States" | Email uses US spelling (color, organization, program) |
| US abbreviation | Lead.Country = "USA" | Email uses US spelling |
| EU lead | Lead.Country = "Germany" | Email uses UK spelling (default) |
| Blank country | Lead.Country = null | Email uses UK spelling (default) |
| US territory | Lead.Country = "Puerto Rico" | Email uses US spelling |

**Regression**: Re-run existing UK test suite from `testing/output/` to confirm no change for UK leads.

---

### Phase 1: Follow-up Outreach Re-engineering

#### 6.1.1 Create Prompt Template: `LNA_Nova_Follow_Up_Nudge`

**File**: `force-app/main/default/genAiPromptTemplates/LNA_Nova_Follow_Up_Nudge.genAiPromptTemplate-meta.xml`

**Type**: `einstein_gpt__flex`
**Model**: `sfdc_ai__DefaultVertexAIGemini25Flash001`
**Related Entity**: `Lead`

**Inputs**:
| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `Recipient` | `SOBJECT://Lead` | Yes | Lead record with FirstName, Title |
| `PreviousEmailBody` | `primitive://String` | Yes | Full previous email (subject + body) |
| `IsFinalMessage` | `primitive://String` | Yes | "true" or "false" |
| `SpellingLocale` | `primitive://String` | Yes | "UK" or "US" — resolved by Flow |

**Prompt Content** — sections consolidated from current 6 instructions:

1. **Role & Context**: You write follow-up nudge emails for leads who haven't responded to a previous outreach from Nova.
2. **Lead Data**: Merge fields for `{!$Input:Recipient.FirstName}`, `{!$Input:Recipient.Title}`.
3. **Previous Email**: `{!$Input:PreviousEmailBody}` — read to identify the original angle.
4. **Branching Logic**: If `{!$Input:IsFinalMessage}` is "true" → breakaway check-in. Otherwise → role-aware reframe.
5. **Output Format**: JSON `{ "subject": "...", "body": "..." }`.
6. **Spelling & Language**: Dynamic directive using `{!$Input:SpellingLocale}` (see Section 2.4 template).
7. **Tone Rules**: Migrated from current Instruction 5.
8. **Constraints**: Migrated from current Instruction 6.

#### 6.1.2 Create Flow: `LNA_Nova_Follow_Up_Nudge`

**File**: `force-app/main/default/flows/LNA_Nova_Follow_Up_Nudge.flow-meta.xml`

**Input Variables**:
| Variable | Type | Description |
|----------|------|-------------|
| `InputLeadId` | String | Lead record ID |
| `InputEmailBody` | String | Previous email content |
| `InputIsFinalMessage` | String | Final message flag |

**Output Variables**:
| Variable | Type | Description |
|----------|------|-------------|
| `varEmailBody` | String | Generated nudge email |

**Flow Steps**:
1. **Get Lead Record** — Query Lead by InputLeadId. Retrieve: Id, FirstName, Title, **Country**.
2. **Resolve Locale** — Decision element (same pattern as Phase 0 Section 6.0.1).
3. **Generate Follow-Up Nudge** — Call `LNA_Nova_Follow_Up_Nudge` PT:
   - `Input:Recipient` = Get_Lead_Record
   - `Input:PreviousEmailBody` = InputEmailBody
   - `Input:IsFinalMessage` = InputIsFinalMessage
   - `Input:SpellingLocale` = varSpellingLocale
4. **Assign Output** — Store `promptResponse` into `varEmailBody`.

#### 6.1.3 Update Follow-up Outreach Topic

**Reduce to 2 instructions**:

**Instruction 1 (Purpose)**:
> Invoke the LNA Nova - Follow-Up Nudge flow action. Pass the Lead's record ID as InputLeadId, the previous email content as InputEmailBody, and the final message flag as InputIsFinalMessage. The flow handles all data retrieval, locale resolution, email generation, and formatting. Do not modify the returned email content. Do not call any other actions.

**Instruction 2 (Guardrails)**:
> - Never share product prices or offer specific products, services, or tiers
> - Never recommend specific days or times for a meeting
> - Never offer to share examples or sample reports
> - Never fabricate company-specific data or statistics
> - Never reference the lead's browsing activity or imply tracking
> - Never include a sign-off, closing, or signature line
> - Never mention the lead owner, seller, or any other person by name
> - The flow determines the correct spelling locale (UK or US English) based on the lead's country. Do not override the spelling in the returned email.
> - If the flow action returns an error or empty result, do not attempt to generate an email yourself. Create a Task for the Lead Owner and stop.

**Action Changes**:
- Remove: `GetRecordDetails_179c1000000KABJ`
- Add: `LNA_Nova_Follow_Up_Nudge` (new flow action)

---

### Phase 2: Meeting Response Re-engineering

#### 6.2.1 Create Prompt Template: `LNA_Nova_Meeting_Response`

**File**: `force-app/main/default/genAiPromptTemplates/LNA_Nova_Meeting_Response.genAiPromptTemplate-meta.xml`

**Type**: `einstein_gpt__flex`
**Model**: `sfdc_ai__DefaultVertexAIGemini25Flash001`
**Related Entity**: `Lead`

**Inputs**:
| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `Recipient` | `SOBJECT://Lead` | Yes | Lead record with FirstName |
| `LeadReply` | `primitive://String` | Yes | The lead's reply email |
| `LeadOwnerName` | `primitive://String` | Yes | Lead owner's full name (seller) |
| `PreviousSubject` | `primitive://String` | Yes | Subject line from previous thread |
| `SpellingLocale` | `primitive://String` | Yes | "UK" or "US" — resolved by Flow |

**Prompt Content** — sections migrated from current 7 instructions:

1. **Role & Context**: Respond to leads who replied to outreach. Acknowledge and connect with seller.
2. **Lead Data**: `{!$Input:Recipient.FirstName}` for greeting.
3. **Lead's Reply**: `{!$Input:LeadReply}` — opening must reference specifics.
4. **Seller Details**: `{!$Input:LeadOwnerName}` — always use this name, never "Nova".
5. **Meeting Link**: Static link embedded. Frame naturally.
6. **Output Format**: JSON `{ "subject": "...", "body": "..." }`.
7. **Spelling & Language**: Dynamic directive using `{!$Input:SpellingLocale}`.
8. **Tone Rules**: Warm, conversational, reference what they said.
9. **Constraints**: No prices, no fabrication, no sign-off, max one prep question.

#### 6.2.2 Create Flow: `LNA_Nova_Meeting_Response`

**File**: `force-app/main/default/flows/LNA_Nova_Meeting_Response.flow-meta.xml`

**Input Variables**:
| Variable | Type | Description |
|----------|------|-------------|
| `InputLeadId` | String | Lead record ID |
| `InputEmailBody` | String | Lead's reply content |

**Output Variables**:
| Variable | Type | Description |
|----------|------|-------------|
| `varEmailBody` | String | Generated response email |

**Flow Steps**:
1. **Get Lead Record** — Query Lead by InputLeadId. Retrieve: Id, FirstName, Owner.Name, **Country**.
2. **Resolve Locale** — Decision element (same pattern).
3. **Extract Previous Subject** — Formula to parse subject from InputEmailBody.
4. **Generate Meeting Response** — Call `LNA_Nova_Meeting_Response` PT:
   - `Input:Recipient` = Get_Lead_Record
   - `Input:LeadReply` = InputEmailBody
   - `Input:LeadOwnerName` = Get_Lead_Record.Owner.Name
   - `Input:PreviousSubject` = extracted subject
   - `Input:SpellingLocale` = varSpellingLocale
5. **Update Lead Rating** — Set Rating = "Warm".
6. **Assign Output** — Store `promptResponse` into `varEmailBody`.

#### 6.2.3 Update Meeting Response Topic

**Reduce to 2 instructions**:

**Instruction 1 (Purpose)**:
> Invoke the LNA Nova - Meeting Response flow action. Pass the Lead's record ID as InputLeadId and the lead's reply email as InputEmailBody. The flow handles all data retrieval (including the lead owner/seller name), locale resolution, email generation, meeting link inclusion, and Lead record update (Rating = Warm). Do not modify the returned email content. Do not call any other actions.

**Instruction 2 (Guardrails)**:
> - Never share product prices or offer specific products, services, or tiers
> - Never recommend specific days or times
> - Never fabricate company-specific data or statistics
> - Never include a sign-off, closing, or signature
> - Never ask more than one question
> - The flow determines the correct spelling locale (UK or US English) based on the lead's country. Do not override the spelling in the returned email.
> - If the flow action returns an error or empty result, do not attempt to generate an email yourself. Create a Task for the Lead Owner and stop.

**Action Changes**:
- Remove: `GetRecordDetails_179c1000000KABK`, `LNA_Nova_Update_Lead_Record_179c1000000KABK`
- Add: `LNA_Nova_Meeting_Response` (new flow action)

---

### Phase 3: Manage Opt-Out Re-engineering

#### 6.3.1 Create Prompt Template: `LNA_Nova_Opt_Out_Response`

**File**: `force-app/main/default/genAiPromptTemplates/LNA_Nova_Opt_Out_Response.genAiPromptTemplate-meta.xml`

**Type**: `einstein_gpt__flex`
**Model**: `sfdc_ai__DefaultVertexAIGemini25Flash001`

**Inputs**:
| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `LeadReply` | `primitive://String` | Yes | The lead's reply email |
| `PreviousSubject` | `primitive://String` | Yes | Subject line from previous thread |
| `SpellingLocale` | `primitive://String` | Yes | "UK" or "US" — resolved by Flow |

**Prompt Content** — sections migrated from current 6 instructions:

1. **Role & Context**: Classify and respond to negative/irrelevant/opt-out replies.
2. **Lead's Reply**: `{!$Input:LeadReply}` — classify into SPAM / NOT_INTERESTED / OPT_OUT.
3. **Classification Logic**: Migrated from current Instruction 1.
4. **Response Templates**: Per-classification response guidance.
5. **Output Format**: JSON `{ "classification": "...", "subject": "...", "body": "..." }`.
6. **Spelling & Language**: Dynamic directive using `{!$Input:SpellingLocale}`.
7. **Tone Rules**: Respectful, professional, brief.

#### 6.3.2 Create Flow: `LNA_Nova_Opt_Out_Response`

**File**: `force-app/main/default/flows/LNA_Nova_Opt_Out_Response.flow-meta.xml`

**Input Variables**:
| Variable | Type | Description |
|----------|------|-------------|
| `InputLeadId` | String | Lead record ID |
| `InputEmailBody` | String | Lead's reply content |

**Output Variables**:
| Variable | Type | Description |
|----------|------|-------------|
| `varEmailBody` | String | Generated response email |

**Flow Steps**:
1. **Get Lead Record** — Query Lead by InputLeadId. Retrieve: Id, **Country** (minimal — opt-out responses don't use lead name).
2. **Resolve Locale** — Decision element (same pattern).
3. **Extract Previous Subject** — Formula to parse subject from InputEmailBody.
4. **Generate Opt-Out Response** — Call `LNA_Nova_Opt_Out_Response` PT:
   - `Input:LeadReply` = InputEmailBody
   - `Input:PreviousSubject` = extracted subject
   - `Input:SpellingLocale` = varSpellingLocale
5. **Parse Classification** — Extract `classification` from JSON response.
6. **Decision: Classification Branch**:
   - **SPAM** → Update Lead: Status = "Unqualified", UnqualifyReason__c = "Spam"
   - **NOT_INTERESTED** → Update Lead: Status = "Unqualified", UnqualifyReason__c = "Customer Not Interested"
   - **OPT_OUT** → Update Lead: Status = "Unqualified", UnqualifyReason__c = "Opt-out", HasOptedOutOfEmail = true
7. **Assign Output** — Store email body from PT response into `varEmailBody`.

#### 6.3.3 Update Manage Opt-Out Topic

**Reduce to 2 instructions**:

**Instruction 1 (Purpose)**:
> Invoke the LNA Nova - Opt-Out Response flow action. Pass the Lead's record ID as InputLeadId and the lead's reply email as InputEmailBody. The flow handles reply classification (SPAM, NOT INTERESTED, OPT-OUT), locale resolution, response email generation, and all Lead record updates (Status, UnqualifyReason__c, HasOptedOutOfEmail). Do not modify the returned email content. Do not call any other actions.

**Instruction 2 (Guardrails)**:
> - Never try to re-engage or change the lead's mind
> - Never offer a meeting, suggest "reaching out later", or propose alternatives
> - Never include a sign-off, closing, or signature
> - Never share product prices, services, or company details
> - If the flow action returns an error or empty result, do not retry. Stop and do not send a reply.

**Action Changes**:
- Remove: `LNA_Nova_Update_Lead_Record_179c1000000KABM`
- Add: `LNA_Nova_Opt_Out_Response` (new flow action)

---

## 7. Topic Scope Updates

| Topic | Updated Scope |
|-------|---------------|
| Initial Outreach | *(no change to scope text — only guardrail instruction updated for locale)* |
| Follow-up Outreach | "You handle follow-up nudges for leads who have not responded to a previous outreach from Nova. You invoke the LNA Nova - Follow-Up Nudge flow action, which handles data retrieval, locale-aware email generation, and formatting. You do not handle initial outreach, responses, meeting booking, or opt-out processing." |
| Meeting Response | "You handle replies from leads who engage with the outreach topic. You invoke the LNA Nova - Meeting Response flow action, which handles data retrieval, locale-aware email generation, seller connection, meeting link inclusion, and Lead record update. You handle all replies except opt-out requests — those are handled by the Manage Opt-Out topic. You do not handle initial outreach or follow-up nudges." |
| Manage Opt-Out | "You handle negative, irrelevant, or spam replies from leads. You invoke the LNA Nova - Opt-Out Response flow action, which handles reply classification (SPAM, NOT INTERESTED, OPT-OUT), locale-aware response email generation, and Lead record updates. Only replies that engage with the outreach topic are handled by the Meeting Response topic. You do not handle initial outreach or follow-up nudges." |

---

## 8. Migration Checklist (per Phase)

### Phase 0 (Locale Foundation):
- [ ] **8.0.1** Add `Country` to queriedFields in `LNA_Nova_Initial_Outreach` flow
- [ ] **8.0.2** Add Locale Resolve decision + assignments to `LNA_Nova_Initial_Outreach` flow
- [ ] **8.0.3** Add `SpellingLocale` input to `LNA_Nova_Outreach_Email` PT (both versions)
- [ ] **8.0.4** Replace hardcoded UK spelling constraint with dynamic directive in PT (both versions)
- [ ] **8.0.5** Pass `varSpellingLocale` to PT invocation in flow
- [ ] **8.0.6** Update Initial Outreach topic guardrail (remove hardcoded UK spelling line)
- [ ] **8.0.7** Test: UK lead → UK spelling; US lead → US spelling; blank → UK default
- [ ] **8.0.8** Regression: re-run full UK test suite to confirm no change for existing leads

### Phases 1-3 (per topic, same as plan.md + locale):
- [ ] **8.x.1** Draft PT content with dynamic `SpellingLocale` directive
- [ ] **8.x.2** Create GenAiPromptTemplate metadata XML with `SpellingLocale` input
- [ ] **8.x.3** Build Flow with Locale Resolve step + Country in queriedFields
- [ ] **8.x.4** Test Flow: verify locale resolution + PT invocation + record updates
- [ ] **8.x.5** Update PlannerBundle topic (2 instructions, locale-aware guardrail)
- [ ] **8.x.6** Update `package.xml` manifest
- [ ] **8.x.7** Deploy and run agent conversation tests (both UK and US leads)
- [ ] **8.x.8** Compare outputs with baselines; verify spelling matches country

### Phase 4 (Cleanup & Deployment):
- [ ] **8.4.1** Final `package.xml` update with all new components
- [ ] **8.4.2** Full regression test (UK + US leads across all 4 topics)
- [ ] **8.4.3** Deploy to target org

---

## 9. Testing Strategy

### 9.1 Locale-Specific Test Matrix

Every template must be tested with both locale values. The following words are **spelling canaries** — if the LLM gets these right, the locale directive is working:

| Canary Word | UK Expected | US Expected |
|-------------|-------------|-------------|
| organisation/organization | organisation | organization |
| colour/color | colour | color |
| analyse/analyze | analyse | analyze |
| behaviour/behavior | behaviour | behavior |
| programme/program | programme | program |
| centre/center | centre | center |

**Test approach**: For each PT, run 2 test leads (one UK, one US) with identical fields except Country. Diff the outputs — the only differences should be spelling variants, not content or structure.

### 9.2 Unit Testing (per Prompt Template)

| Template | Test Data | Locale Assertions |
|----------|-----------|-------------------|
| `LNA_Nova_Outreach_Email` | Existing UK test leads + cloned US test leads | UK leads: UK canary words. US leads: US canary words. No mixed spelling within a single email. |
| `LNA_Nova_Follow_Up_Nudge` | Nudge test leads (UK + US) | Same canary word check. Final vs non-final logic unchanged by locale. |
| `LNA_Nova_Meeting_Response` | Positive-response test leads (UK + US) | Same canary word check. Seller name and meeting link unaffected by locale. |
| `LNA_Nova_Opt_Out_Response` | Opt-out test leads (UK + US) | Same canary word check. Classification logic unaffected by locale. |

### 9.3 Flow Integration Testing

All tests from plan.md Section 8.2, plus:

| Flow | Test | Expected Outcome |
|------|------|-----------------|
| `LNA_Nova_Initial_Outreach` | Lead.Country = "United States" | varSpellingLocale = "US"; email body uses US spelling |
| `LNA_Nova_Initial_Outreach` | Lead.Country = "UK" | varSpellingLocale = "UK"; email body uses UK spelling |
| `LNA_Nova_Initial_Outreach` | Lead.Country = null | varSpellingLocale = "UK" (default) |
| `LNA_Nova_Follow_Up_Nudge` | Lead.Country = "USA" | US spelling in nudge |
| `LNA_Nova_Meeting_Response` | Lead.Country = "US" | US spelling in response |
| `LNA_Nova_Opt_Out_Response` | Lead.Country = "American Samoa" | US spelling in opt-out reply |

### 9.4 End-to-End Agent Testing

Expand the existing test suite:
- **UK test set** (existing in `prompt/testing-agent/uk-test-references/`): Re-run as-is. Expected: identical results to current baseline.
- **US test set** (new — create in `prompt/testing-agent/us-test-references/`): Clone UK test references, change Lead.Country to "United States". Expected: same email structure and quality, US spelling throughout.

### 9.5 Edge Case Testing

| Scenario | Lead.Country | Expected Locale | Rationale |
|----------|-------------|-----------------|-----------|
| Standard UK | "United Kingdom" | UK | Direct match |
| Standard US | "United States" | US | Direct match |
| US abbreviation | "US" | US | Common CRM shorthand |
| US with periods | "U.S.A." | US | Formal abbreviation |
| Canada | "Canada" | UK | Commonwealth; UK spelling is standard in Canadian business English |
| Australia | "Australia" | UK | Commonwealth default |
| Ireland | "Ireland" | UK | UK spelling dominant in Irish business |
| Germany (EU) | "Germany" | UK | English outreach to non-anglophone countries uses UK default |
| India | "India" | UK | Commonwealth default |
| Blank/null | null | UK | Safe default (current production behaviour) |
| Unexpected value | "Narnia" | UK | Default path handles unknown values |

---

## 10. Risks & Mitigations

All risks from plan.md, plus:

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM ignores SpellingLocale directive and falls back to its trained default (typically US) | UK leads receive US-spelled emails | Include explicit word-level examples in the directive; test with canary words; add a post-generation assertion in the test harness that checks for UK/US canary words |
| LLM mixes conventions within a single email (e.g., "organisation" + "analyze") | Looks unprofessional | Directive explicitly says "Do not mix conventions within a single email"; test for mixed spelling in QA |
| Country field contains non-standard values (e.g., "U.S. of A.", "Vereinigte Staaten") | Flow defaults to UK when it should be US | Start with the known US values listed in Section 2.3; monitor misclassifications; expand the Decision conditions over time. Non-English country names default to UK, which is acceptable for non-US leads. |
| Locale resolution adds latency to every Flow | Slower email generation | Decision + Assignment is negligible overhead (milliseconds) vs. PT invocation (seconds). No measurable impact. |
| Existing UK test baselines invalidated | False regression failures | Phase 0 testing explicitly confirms UK leads produce identical output. Only expand test baselines after confirming Phase 0 parity. |
| Salesforce org uses Country picklist with standardised ISO values | Decision conditions don't match ISO codes | Check the org's Country picklist configuration during implementation. If using ISO codes, add "US" and "USA" mappings (already included). If using Salesforce State/Country picklists feature, values are standardised — adapt conditions accordingly. |

---

## 11. Implementation Order & Dependencies

```
Phase 0: Locale Foundation (PREREQUISITE — do first)
    ├── 0a. Update LNA_Nova_Initial_Outreach flow (add Country query + locale resolve)
    ├── 0b. Update LNA_Nova_Outreach_Email PT (add SpellingLocale input + dynamic directive)
    ├── 0c. Update Initial Outreach topic guardrail
    ├── 0d. Test UK parity (regression) + US locale (new)
    └── 0e. Deploy Phase 0

Phase 1: Follow-up Outreach (lowest risk — no record updates)
    ├── 1a. Create PT: LNA_Nova_Follow_Up_Nudge (with SpellingLocale input)
    ├── 1b. Create Flow: LNA_Nova_Follow_Up_Nudge (with locale resolve)
    ├── 1c. Update topic in PlannerBundle
    └── 1d. Test UK + US leads

Phase 2: Meeting Response (medium risk — one record update)
    ├── 2a. Create PT: LNA_Nova_Meeting_Response (with SpellingLocale input)
    ├── 2b. Create Flow: LNA_Nova_Meeting_Response (with locale resolve)
    ├── 2c. Update topic in PlannerBundle
    └── 2d. Test UK + US leads

Phase 3: Manage Opt-Out (highest risk — branching updates)
    ├── 3a. Create PT: LNA_Nova_Opt_Out_Response (with SpellingLocale input)
    ├── 3b. Create Flow: LNA_Nova_Opt_Out_Response (with locale resolve)
    ├── 3c. Update topic in PlannerBundle
    └── 3d. Test UK + US leads

Phase 4: Cleanup & Deployment
    ├── 4a. Create US test references (prompt/testing-agent/us-test-references/)
    ├── 4b. Update package.xml
    ├── 4c. Full regression test (UK + US across all 4 topics)
    └── 4d. Deploy to target org
```

---

## 12. Summary of Changes

| Metric | Before | After (plan.md) | After (plan2.md — this plan) |
|--------|--------|-----------------|------------------------------|
| Topic instructions (total) | 21 (~8,000 words) | 8 (~800 words) | 8 (~800 words) |
| Prompt Builder templates | 2 | 5 | 5 (1 modified + 3 new + 1 unchanged) |
| Orchestration flows | 2 | 5 | 5 (1 modified + 3 new + 1 unchanged) |
| Record update logic | Mixed (2 Flow, 2 planner) | All in Flows | All in Flows |
| Planner reasoning steps per topic | 3-5 | 1 | 1 |
| LLM-dependent field values | 3 topics | 0 topics | 0 topics |
| Spelling locales supported | 1 (UK only, hardcoded) | 1 (UK only, hardcoded) | **2 (UK + US, dynamic per lead)** |
| Locale resolution | None | None | **Flow-side, deterministic** |
| SpellingLocale as PT input | 0 templates | 0 templates | **4 templates (all customer-facing)** |
| Country queried in flows | 0 flows | 0 flows | **4 flows** |
| Test coverage (locale) | UK only | UK only | **UK + US for every topic** |
