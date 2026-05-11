# Topic Instructions: Meeting Response (V3)

## V1 Instructions (current — 7 instructions, ~2,800 words)

```
Instruction 1: Call Get Record Details using currentRecordId to get the lead's first name and the 
               lead owner's name. Read the lead's reply in emailBody carefully. Opening sentence 
               must prove you read their message — reference something specific they said...

Instruction 2: Every non-negative reply means the lead is engaged. Acknowledge what they said in 
               one or two sentences, then offer a short call with the seller...

Instruction 3: Meeting link framing rules — always mention seller by name, include link on its own 
               line: https://outlook.office365.com/book/sales@statista.com/ ...

Instruction 4: Output format — Subject: Re: [...], Hi [Name], Body (2-4 sentences)...

Instruction 5: Tone rules — warm, conversational, no buzzwords, no flattery...

Instruction 6: MUST call Update Lead Record action with currentRecordId, set Rating to Warm only...

Instruction 7: Guardrails — no prices, no specific days/times, no fabricated data...
```

---

## V3 Instructions (target — 2 instructions, ~200 words)

### Instruction 1 — Purpose

```
Purpose: Respond to leads who have replied to a previous outreach or nudge email from Nova with 
a non-negative response (positive interest, questions, neutral messages). Invoke the LNA Nova - 
Meeting Response flow action, passing:
- currentRecordId as InputLeadId
- the lead's reply as emailBody

The flow reads the lead record, resolves the seller name and meeting link from the Lead Owner, 
generates a contextual reply using locale-appropriate English, updates the Lead rating to Warm, 
logs the conversation summary to LeadDescription__c, and returns the email. Do not call any 
additional actions or update any records yourself.
```

### Instruction 2 — Guardrails

```
Guardrails:
- Never share product prices or offer specific products, services, or tiers
- Never recommend specific days or times — the meeting link handles scheduling
- Never fabricate company-specific data or statistics
- Never include a sign-off, closing, or signature — the platform handles this
- Never ask more than one question — at most one brief prep question alongside the meeting offer
- If the flow action returns an error or empty result, do not attempt to generate an email 
  yourself. Create a Task for the Lead Owner and stop.
```

---

## What Moved Where

| V1 Instruction | V3 Location | Rationale |
|----------------|-------------|-----------|
| Instruction 1 (Get Record Details + read reply) | Flow step 1 + PT Step 1 | Data retrieval is deterministic; reading/referencing the reply is a generation concern for the PT |
| Instruction 2 (Acknowledge + connect to seller) | PT Step 2 | Email generation logic belongs in the PT |
| Instruction 3 (Meeting link formatting) | PT Step 3 + Flow variable | Link source is dynamic (`OwnerMeetingLink__c`); framing rules are PT generation concerns |
| Instruction 4 (Output format) | PT Output Format section | Structural formatting is a PT concern |
| Instruction 5 (Tone rules) | PT Tone Rules section | Voice/tone is a PT concern |
| Instruction 6 (Update Lead Record) | Flow step 6 (deterministic DML) | Record updates must be deterministic — removed from planner entirely |
| Instruction 7 (Guardrails) | Topic Instruction 2 (slim) + PT Guardrails section | Guardrails remain in topic for planner awareness; PT has its own guardrails for generation |

---

## Disambiguation: Meeting Response vs. Manage Opt-Out

Both topics share the `Reply` orchestration stage. The planner routes based on **topic scope descriptions**:

- **Meeting Response scope:** "...non-negative response (positive interest, questions, neutral messages)..."
- **Manage Opt-Out scope:** "...negative, irrelevant, or spam response..."

This classification is the planner's natural strength (intent detection). It does not require any deterministic logic and stays in the planner.
