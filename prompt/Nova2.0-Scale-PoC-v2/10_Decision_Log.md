# Decision Log

Architectural decisions made during the V2 refactoring and rationale.

---

## D1: Move all record updates into Flows

**Decision:** Zero planner-side DML. All record updates are deterministic Flow steps.

**Rationale:**
- V1 requires the planner to recall exact picklist values (e.g., "Customer Not Interested" not "Not Interested"). One typo silently breaks downstream automations.
- V1 requires the planner to call the Update action in the correct order (Status before UnqualifyReason). If sequencing is wrong, the Salesforce validation rule rejects the update.
- Flow Decision elements guarantee exact field values every time.

**Trade-off:** Slightly more complex Flows, but eliminates an entire class of runtime failures.

---

## D2: Add `summary` field to PT JSON output

**Decision:** PTs for Meeting Response and Opt-Out now return a `summary` field alongside `reply`.

**Rationale:**
- V1 has the planner generate LeadDescription__c bullets and call the Update action itself. This requires the planner to: (a) read existing description, (b) parse HTML, (c) prepend, (d) enforce cap, (e) format with `<br>`. LLMs frequently miscounted, dropped old bullets, or reformatted.
- By having the PT return a pre-formatted summary bullet and letting Apex handle the merge, we get reliable logging with zero planner context cost.

**Trade-off:** PT output is slightly more complex (JSON with 2-3 fields vs. plain text). Acceptable because the Apex parser handles this reliably.

---

## D3: Single Apex parser class, multiple invocable methods

**Decision:** One `LNA_Nova_ResponseParser` class with separate `@InvocableMethod` for each PT response type.

**Rationale:**
- Keeps deployment simple (one class, one test class)
- Methods are independently callable from different Flows
- Shared `mergeLeadDescription` logic avoids duplication

**Alternative considered:** Separate classes per PT. Rejected — too much boilerplate for what amounts to JSON field extraction.

---

## D4: Locale as Flow variable, not PT constant

**Decision:** Locale is resolved in the Flow (Country → en-GB/en-US) and passed to the PT as an input parameter.

**Rationale:**
- V1 hardcodes "UK spelling" in the PT content. Adding US support would require duplicating the entire PT or adding complex conditional logic inside the prompt.
- The Flow pattern is extensible: adding en-AU, de-DE, or fr-FR later requires only a new Decision rule — no PT changes.

**Trade-off:** One extra variable per Flow. Negligible cost.

---

## D5: Meeting link as Flow variable (not embedded in topic instructions)

**Decision:** The meeting link is assigned in the Flow and passed to the PT as `{!$Input:MeetingLink}`.

**Rationale:**
- V1 embeds the full Outlook booking URL in multiple topic instructions (Follow-up Instruction 4, Meeting Response Instruction 3). If the link changes, it must be updated in 2+ places.
- Flow variable: one assignment, one source of truth.
- For Follow-up final messages: the link is still embedded in the PT because it's part of a static template pattern and only used in one code path. If it changes frequently, it could be moved to a Flow variable in future.

---

## D6: Keep Follow-up Nudge PT as plain text output (no JSON)

**Decision:** The Follow-up Nudge PT returns plain text (the email), not JSON.

**Rationale:**
- No record updates needed for follow-up nudges
- No conversation logging needed (the nudge is outbound, not a reply)
- Plain text is simpler to consume in the Flow (no Apex parser needed)
- Reduces Flex Credit cost (shorter PT, faster response)

**Contrast with:** Meeting Response and Opt-Out PTs which return JSON because they need structured fields for downstream Flow logic.

---

## D7: Topic scope handles Meeting Response vs. Opt-Out disambiguation

**Decision:** Both topics share the `Reply` orchestration stage. The planner routes to the correct topic based on the `scope` description.

**Rationale:**
- The planner is good at intent classification (positive vs. negative reply) — this is its natural strength.
- V1 already uses this pattern successfully. No reason to change it.
- Alternative (single "Reply" topic that classifies internally) would combine two very different response patterns into one complex Flow.

**Trade-off:** Relies on planner for one classification decision. Acceptable because this is routing (planner's strength), not data manipulation (planner's weakness).

---

## D8: Fault paths create Tasks rather than retrying

**Decision:** If a PT returns malformed JSON or an Apex parse fails, the Flow creates a Task for the Lead Owner and stops. No email is sent.

**Rationale:**
- Retrying the same PT call is unlikely to produce different results
- Sending a malformed or empty email to the lead is worse than sending nothing
- The Task ensures a human reviews the failure
- This matches the existing guardrail pattern ("If error, create Task and stop")
