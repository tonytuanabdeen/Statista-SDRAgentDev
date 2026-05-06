# LNA Nova Re-Engineering Plan: Topic Instructions to Prompt Builder Framework

## 1. Executive Summary

The LNA Nova agent (Agentforce Sales Development Rep) currently has four topics, but only **Initial Outreach** follows the Prompt Builder pattern — delegating email generation to GenAiPromptTemplates orchestrated via Flow. The remaining three topics (**Follow-up Outreach**, **Meeting Response**, **Manage Opt-Out**) embed all prompt logic directly in topic instructions, forcing the ReAct planner to simultaneously reason about action orchestration AND perform complex email generation.

This plan re-engineers those three topics to match the Initial Outreach pattern: extract email generation into dedicated Prompt Builder templates, orchestrate data retrieval and record updates via Flows, and reduce topic instructions to minimal scope + invocation + guardrails.

---

## 2. Current Architecture Analysis

### 2.1 What Exists Today

| Component | Type | Status |
|-----------|------|--------|
| `Agentforce_Sales_Development_Rep.genAiPlannerBundle` | GenAiPlannerBundle | 4 topics, 1 global action, 3 rule expressions |
| `LNA_Nova_Lead_Persona_Detection.genAiPromptTemplate` | GenAiPromptTemplate | Published (GPT-4o Mini) |
| `LNA_Nova_Outreach_Email.genAiPromptTemplate` | GenAiPromptTemplate | Published (Gemini 2.5 Flash) |
| `LNA_Nova_Initial_Outreach.flow` | AutoLaunchedFlow | Active — orchestrates persona detection + email gen |
| `LNA_Nova_Update_Lead_Record.flow` | AutoLaunchedFlow | Active — generic lead update |
| `v1.botVersion` | BotVersion | 7 conversation variables, ReAct planner |

### 2.2 Orchestration Model

The agent is invoked by a Sales Cadence. The `OrchestrationStage` conversation variable routes to topics via rule expressions:

```
OrchestrationStage = "Intro"  → Initial Outreach topic
OrchestrationStage = "Nudge"  → Follow-up Outreach topic
OrchestrationStage = "Reply"  → Meeting Response topic + Manage Opt-Out topic (both eligible; planner selects based on reply content)
```

Context variables passed per invocation: `currentRecordId`, `emailBody`, `isFinalMessage`, `actionCadenceStepTrackerId`.

### 2.3 Topic-by-Topic Audit

#### Initial Outreach (REFERENCE PATTERN)
- **Instructions**: 2 (Purpose + Guardrails) — minimal
- **Actions**: 1 flow (`LNA_Nova_Initial_Outreach`)
- **Prompt Builder**: YES — flow calls `LNA_Nova_Lead_Persona_Detection` then `LNA_Nova_Outreach_Email`
- **Record Updates**: Flow updates Lead Status to "Outreach"
- **Assessment**: This is the target pattern. Topic tells agent what to do; flow + templates handle how.

#### Follow-up Outreach (NEEDS RE-ENGINEERING)
- **Instructions**: 6 (role-aware reframing, output format, reframe strategy, final message override, tone rules, guardrails)
- **Actions**: 1 (`Get Record Details`)
- **Prompt Builder**: NO — all generation logic lives in topic XML instructions
- **Record Updates**: None
- **Issues**:
  - ~2,500 words of prompt logic embedded in topic instructions
  - Planner must call Get Record Details, parse Job Title, read emailBody, determine if isFinalMessage, then compose a role-aware reframed nudge — all within the ReAct reasoning loop
  - Final message (breakaway) logic is a conditional override of 3 other instructions, adding branching complexity to the planner
  - Meeting link is hardcoded in instructions for final messages only

#### Meeting Response (NEEDS RE-ENGINEERING)
- **Instructions**: 7 (read reply + get details, acknowledge + seller connect, meeting link formatting, output format, tone rules, mandatory update action, guardrails)
- **Actions**: 2 (`Get Record Details`, `LNA Nova - Update Lead Record`)
- **Prompt Builder**: NO — all generation logic lives in topic XML instructions
- **Record Updates**: Agent must call Update Lead Record (Rating = Warm) after generating email
- **Issues**:
  - ~1,800 words of prompt logic in topic instructions
  - Planner must: (1) call Get Record Details, (2) extract lead owner name, (3) compose a reply that references specific content from the lead's email, (4) include meeting link, (5) then call Update Lead Record — five-step reasoning chain
  - Lead owner extraction is fragile — depends on planner correctly parsing Get Record Details output

#### Manage Opt-Out (NEEDS RE-ENGINEERING)
- **Instructions**: 6 (classify reply, response templates per class, output format, tone rules, mandatory update with exact field values, guardrails)
- **Actions**: 1 (`LNA Nova - Update Lead Record`)
- **Prompt Builder**: NO — all generation logic lives in topic XML instructions
- **Record Updates**: Agent must set Status="Unqualified" + UnqualifyReason__c + conditionally HasOptedOutOfEmail
- **Issues**:
  - ~2,000 words of prompt logic in topic instructions
  - Classification logic (SPAM/NOT INTERESTED/OPT-OUT) + email generation + field-value mapping are all interleaved
  - Exact picklist values are specified in instructions ("Customer Not Interested" not "Not Interested") — error-prone when planner must remember exact strings
  - Three different update payloads depending on classification — branching logic that belongs in a Flow, not planner reasoning

---

## 3. Target Architecture

### 3.1 Design Principles

1. **Separation of Concerns**: Topic instructions define *what* and *when*. Prompt Templates define *how to generate*. Flows define *how to orchestrate*.
2. **Planner Simplicity**: Reduce each topic to: understand the task → invoke one flow action → return the result. The planner should never compose emails directly.
3. **Deterministic Record Updates**: Move all field update logic (exact picklist values, conditional fields) into Flows where they are declarative and testable, not dependent on LLM output parsing.
4. **Consistent Pattern**: Every topic follows: `Topic (scope + guardrails) → Flow (orchestration + data + updates) → Prompt Template(s) (generation)`.

### 3.2 Architecture Diagram

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
     ┌──────────┼──────┐          │        ┌───────────┐ ┌───────────┐
     ▼                 ▼          ▼        │ Flow:     │ │ Flow:     │
┌─────────┐   ┌──────────┐ ┌──────────┐   │ LNA_Nova_ │ │ LNA_Nova_ │
│ PT:     │   │ PT:      │ │ PT:      │   │ Meeting_  │ │ Opt_Out_  │
│ Persona │   │ Outreach │ │ Follow   │   │ Response  │ │ Response  │
│ Detect  │   │ Email    │ │ Up Nudge │   └─────┬─────┘ └─────┬─────┘
└─────────┘   └──────────┘ └──────────┘         │             │
                                                ▼             ▼
                                          ┌──────────┐  ┌──────────┐
                                          │ PT:      │  │ PT:      │
                                          │ Meeting  │  │ Opt-Out  │
                                          │ Response │  │ Response │
                                          └──────────┘  └──────────┘
```

**Legend**: PT = GenAiPromptTemplate | Flow = AutoLaunchedFlow | Topic = GenAiPlugin (in PlannerBundle)

---

## 4. Deliverables

### 4.1 New GenAiPromptTemplates (3)

| # | Template Name | Model | Inputs | Output | Migrated From |
|---|--------------|-------|--------|--------|---------------|
| 1 | `LNA_Nova_Follow_Up_Nudge` | Gemini 2.5 Flash | Lead (SObject), PreviousEmailBody (String), IsFinalMessage (String), LeadJobTitle (String) | JSON: `{ subject, body }` | Follow-up Outreach Instructions 1-5 |
| 2 | `LNA_Nova_Meeting_Response` | Gemini 2.5 Flash | Lead (SObject), LeadReply (String), LeadOwnerName (String), PreviousSubject (String) | JSON: `{ subject, body }` | Meeting Response Instructions 1-5 |
| 3 | `LNA_Nova_Opt_Out_Response` | Gemini 2.5 Flash | LeadReply (String), PreviousSubject (String) | JSON: `{ classification, subject, body }` | Manage Opt-Out Instructions 1-4 |

### 4.2 New Flows (3)

| # | Flow Name | Type | Purpose |
|---|-----------|------|---------|
| 1 | `LNA_Nova_Follow_Up_Nudge` | AutoLaunchedFlow | Get Lead Record → Extract Job Title → Call PT → Return email body |
| 2 | `LNA_Nova_Meeting_Response` | AutoLaunchedFlow | Get Lead + Owner → Call PT → Update Lead (Rating=Warm) → Return email body |
| 3 | `LNA_Nova_Opt_Out_Response` | AutoLaunchedFlow | Call PT → Parse classification → Branch: set Status/UnqualifyReason__c/HasOptedOutOfEmail per classification → Update Lead → Return email body |

### 4.3 Modified Components

| # | Component | Change |
|---|-----------|--------|
| 1 | Follow-up Outreach topic | Reduce from 6 instructions to 2 (Purpose + Guardrails). Remove Get Record Details action. Add new flow action. |
| 2 | Meeting Response topic | Reduce from 7 instructions to 2 (Purpose + Guardrails). Remove Get Record Details + Update Lead Record actions. Add new flow action. |
| 3 | Manage Opt-Out topic | Reduce from 6 instructions to 2 (Purpose + Guardrails). Remove Update Lead Record action. Add new flow action. |
| 4 | `package.xml` manifest | Add 3 new GenAiPromptTemplates + 3 new Flows |

### 4.4 No-Change Components

| Component | Reason |
|-----------|--------|
| Initial Outreach topic + flow + templates | Already follows target pattern |
| `LNA_Nova_Update_Lead_Record` flow | Still used by new flows for record updates |
| Bot version + conversation variables | No changes to orchestration variables |
| Rule expressions | Routing logic unchanged |
| `AnswerQuestionsWithKnowledge` global action | Unchanged |

---

## 5. Detailed Implementation Phases

### Phase 1: Follow-up Outreach Re-engineering

#### 5.1.1 Create Prompt Template: `LNA_Nova_Follow_Up_Nudge`

**File**: `force-app/main/default/genAiPromptTemplates/LNA_Nova_Follow_Up_Nudge.genAiPromptTemplate-meta.xml`

**Type**: `einstein_gpt__flex`
**Model**: `sfdc_ai__DefaultVertexAIGemini25Flash001`
**Related Entity**: `Lead`

**Inputs**:
| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `Recipient` | `SOBJECT://Lead` | Yes | Lead record with FirstName, Title |
| `PreviousEmailBody` | `primitive://String` | Yes | Full previous email (subject + body) from emailBody context var |
| `IsFinalMessage` | `primitive://String` | Yes | "true" or "false" from isFinalMessage context var |

**Prompt Content** (migrate from Instructions 1-5 of current topic):

The template prompt must contain these sections, consolidated from the current 6 instructions:

1. **Role & Context**: You write follow-up nudge emails for leads who haven't responded to a previous outreach from Nova.
2. **Lead Data**: Merge fields for `{!$Input:Recipient.FirstName}`, `{!$Input:Recipient.Title}`.
3. **Previous Email**: `{!$Input:PreviousEmailBody}` — read to identify the original angle, pain point, and value proposition.
4. **Branching Logic**: If `{!$Input:IsFinalMessage}` is "true", generate a breakaway check-in (current Instruction 4 logic). Otherwise, generate a role-aware reframe (current Instructions 1+3 logic).
5. **Output Format**: JSON `{ "subject": "...", "body": "..." }` — subject reuses previous subject, body follows the defined structure.
6. **Tone & Language Rules**: Migrated from current Instruction 5.
7. **Constraints/Guardrails**: Subset of current Instruction 6 that applies to generation (not action invocation).

**Key Decisions**:
- The meeting link for final messages is embedded in the template prompt (static value), same as current Instruction 4.
- The "Get Record Details" action is replaced by direct Lead SObject merge fields in the template — the Flow passes the full Lead record.
- Word count guidance (40-60 words for nudges, under 40 for check-ins) moves into the template.

#### 5.1.2 Create Flow: `LNA_Nova_Follow_Up_Nudge`

**File**: `force-app/main/default/flows/LNA_Nova_Follow_Up_Nudge.flow-meta.xml`

**Type**: AutoLaunchedFlow
**API Version**: 66.0

**Input Variables**:
| Variable | Type | Description |
|----------|------|-------------|
| `InputLeadId` | String | Lead record ID (from currentRecordId) |
| `InputEmailBody` | String | Previous email content (from emailBody) |
| `InputIsFinalMessage` | String | Final message flag (from isFinalMessage) |

**Output Variables**:
| Variable | Type | Description |
|----------|------|-------------|
| `varEmailBody` | String | Generated nudge email (PT response) |

**Flow Steps**:
1. **Get Lead Record** — Query Lead by InputLeadId. Retrieve: Id, FirstName, Title.
2. **Generate Follow-Up Nudge** — Call `LNA_Nova_Follow_Up_Nudge` Prompt Template:
   - `Input:Recipient` = Get_Lead_Record
   - `Input:PreviousEmailBody` = InputEmailBody
   - `Input:IsFinalMessage` = InputIsFinalMessage
3. **Assign Output** — Store `promptResponse` into `varEmailBody`.

**Error Handling**: If Get Lead Record returns null, set varEmailBody to an error marker. The topic guardrail instruction handles this by telling the agent to create a Task and stop.

#### 5.1.3 Update Follow-up Outreach Topic

**Reduce to 2 instructions**:

**Instruction 1 (Purpose)**:
> Invoke the LNA Nova - Follow-Up Nudge flow action. Pass the Lead's record ID as InputLeadId, the previous email content as InputEmailBody, and the final message flag as InputIsFinalMessage. The flow handles all data retrieval, email generation, and formatting. Do not modify the returned email content. Do not call any other actions.

**Instruction 2 (Guardrails)**:
> - Never share product prices or offer specific products, services, or tiers
> - Never recommend specific days or times for a meeting
> - Never offer to share examples or sample reports
> - Never fabricate company-specific data or statistics
> - Never reference the lead's browsing activity or imply tracking
> - Never include a sign-off, closing, or signature line
> - Never mention the lead owner, seller, or any other person by name
> - If the flow action returns an error or empty result, do not attempt to generate an email yourself. Create a Task for the Lead Owner and stop.
> - Always write in English using UK spelling and conventions.

**Action Changes**:
- Remove: `GetRecordDetails_179c1000000KABJ`
- Add: `LNA_Nova_Follow_Up_Nudge` (new flow action)

---

### Phase 2: Meeting Response Re-engineering

#### 5.2.1 Create Prompt Template: `LNA_Nova_Meeting_Response`

**File**: `force-app/main/default/genAiPromptTemplates/LNA_Nova_Meeting_Response.genAiPromptTemplate-meta.xml`

**Type**: `einstein_gpt__flex`
**Model**: `sfdc_ai__DefaultVertexAIGemini25Flash001`
**Related Entity**: `Lead`

**Inputs**:
| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `Recipient` | `SOBJECT://Lead` | Yes | Lead record with FirstName |
| `LeadReply` | `primitive://String` | Yes | The lead's reply email from emailBody |
| `LeadOwnerName` | `primitive://String` | Yes | Lead owner's full name (seller name) |
| `PreviousSubject` | `primitive://String` | Yes | Subject line from previous email thread |

**Prompt Content** (migrate from Instructions 1-5 of current topic):

1. **Role & Context**: You respond to leads who have replied to a previous outreach or nudge email from Nova. Your job is to acknowledge their reply and connect them with the seller.
2. **Lead Data**: `{!$Input:Recipient.FirstName}` for greeting.
3. **Lead's Reply**: `{!$Input:LeadReply}` — read carefully; your opening sentence must reference something specific they said.
4. **Seller Details**: The lead owner is `{!$Input:LeadOwnerName}` — this is the seller. Use this name when connecting the lead. Never use "Nova" as the seller name.
5. **Meeting Link Logic**: Always include the meeting link. Frame naturally. Static link embedded in prompt.
6. **Response Strategy**: Migrated from current Instructions 1-2 (acknowledge reply, connect with seller, handle concerns).
7. **Output Format**: JSON `{ "subject": "Re: {!$Input:PreviousSubject}", "body": "..." }`.
8. **Tone Rules**: Migrated from current Instruction 5.
9. **Constraints**: No prices, no specific days/times, no fabricated data, no sign-off, max one prep question.

**Key Decisions**:
- Lead owner name is resolved in the Flow (via relationship query on Lead.Owner.Name), not by the planner parsing Get Record Details output. This eliminates the fragile extraction step.
- The `PreviousSubject` input lets the template construct the "Re:" subject deterministically.
- Meeting link remains a static string in the prompt (same URL as current).

#### 5.2.2 Create Flow: `LNA_Nova_Meeting_Response`

**File**: `force-app/main/default/flows/LNA_Nova_Meeting_Response.flow-meta.xml`

**Type**: AutoLaunchedFlow
**API Version**: 66.0

**Input Variables**:
| Variable | Type | Description |
|----------|------|-------------|
| `InputLeadId` | String | Lead record ID (from currentRecordId) |
| `InputEmailBody` | String | Lead's reply content (from emailBody) |

**Output Variables**:
| Variable | Type | Description |
|----------|------|-------------|
| `varEmailBody` | String | Generated response email (PT response) |

**Flow Steps**:
1. **Get Lead Record** — Query Lead by InputLeadId. Retrieve: Id, FirstName, Owner.Name (relationship field).
2. **Extract Previous Subject** — Use a Formula or Assignment to parse the subject line from InputEmailBody (content after "Subject:" prefix up to first newline).
3. **Generate Meeting Response** — Call `LNA_Nova_Meeting_Response` Prompt Template:
   - `Input:Recipient` = Get_Lead_Record
   - `Input:LeadReply` = InputEmailBody
   - `Input:LeadOwnerName` = Get_Lead_Record.Owner.Name
   - `Input:PreviousSubject` = extracted subject formula
4. **Update Lead Rating** — Update Lead record: set Rating = "Warm".
5. **Assign Output** — Store `promptResponse` into `varEmailBody`.

**Key Advantage**: The record update (Rating = Warm) is now deterministic in the Flow — no longer depends on the planner remembering to call a separate action after generating the email.

#### 5.2.3 Update Meeting Response Topic

**Reduce to 2 instructions**:

**Instruction 1 (Purpose)**:
> Invoke the LNA Nova - Meeting Response flow action. Pass the Lead's record ID as InputLeadId and the lead's reply email as InputEmailBody. The flow handles all data retrieval (including the lead owner/seller name), email generation, meeting link inclusion, and Lead record update (Rating = Warm). Do not modify the returned email content. Do not call any other actions.

**Instruction 2 (Guardrails)**:
> - Never share product prices or offer specific products, services, or tiers
> - Never recommend specific days or times
> - Never fabricate company-specific data or statistics
> - Never include a sign-off, closing, or signature
> - Never ask more than one question
> - If the flow action returns an error or empty result, do not attempt to generate an email yourself. Create a Task for the Lead Owner and stop.

**Action Changes**:
- Remove: `GetRecordDetails_179c1000000KABK`, `LNA_Nova_Update_Lead_Record_179c1000000KABK`
- Add: `LNA_Nova_Meeting_Response` (new flow action)

---

### Phase 3: Manage Opt-Out Re-engineering

#### 5.3.1 Create Prompt Template: `LNA_Nova_Opt_Out_Response`

**File**: `force-app/main/default/genAiPromptTemplates/LNA_Nova_Opt_Out_Response.genAiPromptTemplate-meta.xml`

**Type**: `einstein_gpt__flex`
**Model**: `sfdc_ai__DefaultVertexAIGemini25Flash001`

**Inputs**:
| Input | Type | Required | Description |
|-------|------|----------|-------------|
| `LeadReply` | `primitive://String` | Yes | The lead's reply email from emailBody |
| `PreviousSubject` | `primitive://String` | Yes | Subject line from previous email thread |

**Prompt Content** (migrate from Instructions 1-4 of current topic):

1. **Role & Context**: You classify and respond to leads who have replied negatively, irrelevantly, or asked to opt out.
2. **Lead's Reply**: `{!$Input:LeadReply}` — read carefully and classify.
3. **Classification Logic**: Migrated from current Instruction 1 (SPAM / NOT INTERESTED / OPT-OUT definitions and examples).
4. **Response Templates**: Migrated from current Instruction 2 (per-classification response guidance).
5. **Output Format**: JSON `{ "classification": "SPAM|NOT_INTERESTED|OPT_OUT", "subject": "Re: {!$Input:PreviousSubject}", "body": "..." }`.
6. **Tone Rules**: Migrated from current Instruction 4.

**Key Decision**:
- The template outputs a `classification` field that the Flow uses for deterministic branching — the Flow maps classification to exact picklist values, not the LLM.
- No Lead SObject input needed — the opt-out response doesn't require lead name or personalisation (current responses use "Hi," not "Hi [Name]").

#### 5.3.2 Create Flow: `LNA_Nova_Opt_Out_Response`

**File**: `force-app/main/default/flows/LNA_Nova_Opt_Out_Response.flow-meta.xml`

**Type**: AutoLaunchedFlow
**API Version**: 66.0

**Input Variables**:
| Variable | Type | Description |
|----------|------|-------------|
| `InputLeadId` | String | Lead record ID (from currentRecordId) |
| `InputEmailBody` | String | Lead's reply content (from emailBody) |

**Output Variables**:
| Variable | Type | Description |
|----------|------|-------------|
| `varEmailBody` | String | Generated response email (PT response) |

**Flow Steps**:
1. **Extract Previous Subject** — Parse subject from InputEmailBody.
2. **Generate Opt-Out Response** — Call `LNA_Nova_Opt_Out_Response` Prompt Template:
   - `Input:LeadReply` = InputEmailBody
   - `Input:PreviousSubject` = extracted subject formula
3. **Parse Classification** — Extract `classification` value from JSON response.
4. **Decision: Classification Branch**:
   - **SPAM** → Update Lead: Status = "Unqualified", UnqualifyReason__c = "Spam"
   - **NOT_INTERESTED** → Update Lead: Status = "Unqualified", UnqualifyReason__c = "Customer Not Interested"
   - **OPT_OUT** → Update Lead: Status = "Unqualified", UnqualifyReason__c = "Opt-out", HasOptedOutOfEmail = true
5. **Assign Output** — Store email body from PT response into `varEmailBody`.

**Key Advantage**: The exact picklist values ("Customer Not Interested", not "Not Interested") are hardcoded in Flow update elements — zero chance of the LLM using a wrong value. The conditional HasOptedOutOfEmail flag is a declarative branch, not an LLM instruction.

#### 5.3.3 Update Manage Opt-Out Topic

**Reduce to 2 instructions**:

**Instruction 1 (Purpose)**:
> Invoke the LNA Nova - Opt-Out Response flow action. Pass the Lead's record ID as InputLeadId and the lead's reply email as InputEmailBody. The flow handles reply classification (SPAM, NOT INTERESTED, OPT-OUT), response email generation, and all Lead record updates (Status, UnqualifyReason__c, HasOptedOutOfEmail). Do not modify the returned email content. Do not call any other actions.

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

## 6. Topic Scope Updates

When reducing topic instructions, the **scope** field must also be updated to reflect the simplified delegation pattern. The scope tells the planner when to select this topic — it should describe the topic's responsibility, not how it works internally.

| Topic | Current Scope (Summary) | Updated Scope |
|-------|------------------------|---------------|
| Follow-up Outreach | "You write short follow-up emails... Read the previous email via emailBody and reframe its angle..." | "You handle follow-up nudges for leads who have not responded to a previous outreach from Nova. You invoke the LNA Nova - Follow-Up Nudge flow action, which handles data retrieval, email generation, and formatting. You do not handle initial outreach, responses, meeting booking, or opt-out processing." |
| Meeting Response | "You respond to leads who have replied... Read their reply carefully and respond..." | "You handle replies from leads who engage with the outreach topic. You invoke the LNA Nova - Meeting Response flow action, which handles data retrieval, email generation, seller connection, meeting link inclusion, and Lead record update. You handle all replies except opt-out requests — those are handled by the Manage Opt-Out topic. You do not handle initial outreach or follow-up nudges." |
| Manage Opt-Out | "You respond to leads who have replied... with a negative, irrelevant, or spam response... Read their reply carefully, classify..." | "You handle negative, irrelevant, or spam replies from leads. You invoke the LNA Nova - Opt-Out Response flow action, which handles reply classification (SPAM, NOT INTERESTED, OPT-OUT), response email generation, and Lead record updates. Only replies that engage with the outreach topic are handled by the Meeting Response topic. You do not handle initial outreach or follow-up nudges." |

---

## 7. Migration Checklist (per Phase)

Each phase follows the same steps:

- [ ] **7.1** Draft Prompt Template content by migrating instructions from current topic XML
- [ ] **7.2** Create GenAiPromptTemplate metadata XML file with inputs, model, and versioning
- [ ] **7.3** Design and build the orchestration Flow in Flow Builder (or metadata XML)
- [ ] **7.4** Test Flow in isolation: verify data retrieval, PT invocation, record updates
- [ ] **7.5** Update the GenAiPlannerBundle:
  - Replace topic instructions (reduce to 2)
  - Update topic scope
  - Remove old localActions
  - Add new flow localAction
  - Update localActionLinks
- [ ] **7.6** Update `package.xml` manifest to include new components
- [ ] **7.7** Deploy to scratch org and run agent conversation tests
- [ ] **7.8** Run existing test suite from `prompt/testing-agent/` against re-engineered topics
- [ ] **7.9** Compare outputs with previous test results in `testing/output/` for quality regression check

---

## 8. Testing Strategy

### 8.1 Unit Testing (per Prompt Template)

For each new Prompt Template, run isolated tests using the existing test harness pattern:

| Template | Test Data | Assertions |
|----------|-----------|------------|
| `LNA_Nova_Follow_Up_Nudge` | Existing nudge test leads + emailBody samples | Subject reuses previous subject; body 40-60 words (non-final) / under 40 words (final); no sign-off; final messages include meeting link; non-final messages exclude meeting link |
| `LNA_Nova_Meeting_Response` | Existing positive-response test leads | Subject starts with "Re:"; body references lead's reply content; seller name present; meeting link present; no sign-off |
| `LNA_Nova_Opt_Out_Response` | Opt-out test leads with SPAM/NOT INTERESTED/OPT-OUT replies | Classification matches expected category; response under 3 sentences; no re-engagement; JSON output parseable |

### 8.2 Flow Integration Testing

| Flow | Test | Expected Outcome |
|------|------|-----------------|
| `LNA_Nova_Follow_Up_Nudge` | Pass valid Lead ID + emailBody | varEmailBody populated with valid email |
| `LNA_Nova_Follow_Up_Nudge` | Pass invalid Lead ID | varEmailBody contains error marker |
| `LNA_Nova_Meeting_Response` | Pass valid Lead ID + reply | varEmailBody populated; Lead.Rating = "Warm" |
| `LNA_Nova_Opt_Out_Response` | Pass Lead ID + "unsubscribe me" | varEmailBody populated; Lead.Status = "Unqualified"; UnqualifyReason__c = "Opt-out"; HasOptedOutOfEmail = true |
| `LNA_Nova_Opt_Out_Response` | Pass Lead ID + "not interested" | Lead.UnqualifyReason__c = "Customer Not Interested"; HasOptedOutOfEmail unchanged |
| `LNA_Nova_Opt_Out_Response` | Pass Lead ID + spam text | Lead.UnqualifyReason__c = "Spam"; HasOptedOutOfEmail unchanged |

### 8.3 End-to-End Agent Testing

Re-run the full test suite using test references in `prompt/testing-agent/uk-test-references/`:
- `nudges.md` → Tests Follow-up Outreach topic via agent conversation API
- `positive-response.md` → Tests Meeting Response topic
- `opt-out.md` → Tests Manage Opt-Out topic

Compare results against baseline outputs in `testing/output/` to verify no quality regression.

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| JSON parsing in Flows (extracting classification, subject from PT output) | Flow fails if PT returns malformed JSON | Use Formula resources with error-safe parsing; add Fault path in Flow to handle parse failures gracefully |
| Prompt Template quality divergence from current topic instructions | Email quality changes after migration | Run side-by-side comparison tests before and after; iterate on PT prompt content |
| Lead Owner relationship query unavailable in Flow | Meeting Response Flow can't resolve seller name | Fall back to separate Get Record query on User object using Lead.OwnerId; test in scratch org |
| Subject line extraction from emailBody | emailBody format may vary (with/without "Subject:" prefix) | Implement defensive parsing in Flow formula; handle both formats |
| Planner still tries to compose emails despite simplified instructions | Old behaviour leaks through | Ensure topic scope explicitly states "do not generate email content"; test with adversarial inputs |

---

## 10. Implementation Order & Dependencies

```
Phase 1: Follow-up Outreach (lowest risk — no record updates)
    ├── 1a. Create PT: LNA_Nova_Follow_Up_Nudge
    ├── 1b. Create Flow: LNA_Nova_Follow_Up_Nudge
    ├── 1c. Update topic in PlannerBundle
    └── 1d. Test + validate

Phase 2: Meeting Response (medium risk — one record update)
    ├── 2a. Create PT: LNA_Nova_Meeting_Response
    ├── 2b. Create Flow: LNA_Nova_Meeting_Response
    ├── 2c. Update topic in PlannerBundle
    └── 2d. Test + validate

Phase 3: Manage Opt-Out (highest risk — branching updates, compliance implications)
    ├── 3a. Create PT: LNA_Nova_Opt_Out_Response
    ├── 3b. Create Flow: LNA_Nova_Opt_Out_Response
    ├── 3c. Update topic in PlannerBundle
    └── 3d. Test + validate (with extra focus on field value accuracy)

Phase 4: Cleanup & Deployment
    ├── 4a. Update package.xml
    ├── 4b. Full regression test
    └── 4c. Deploy to target org
```

---

## 11. Summary of Changes

| Metric | Before | After |
|--------|--------|-------|
| Topic instructions (total across 4 topics) | 21 instructions (~8,000 words) | 8 instructions (~800 words) |
| Prompt Builder templates | 2 | 5 |
| Orchestration flows | 2 | 5 |
| Record update logic | Mixed (2 in Flow, 2 in planner) | All in Flows (5 of 5) |
| Planner reasoning steps per topic | 3-5 (action calls + composition) | 1 (invoke flow) |
| LLM-dependent field value accuracy | 3 topics rely on planner for exact picklist values | 0 topics — all values hardcoded in Flows |
