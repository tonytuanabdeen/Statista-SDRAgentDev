# Decision Log: Meeting Response V3

Architectural decisions specific to the V3 Meeting Response refactoring.

---

## D1: Dynamic meeting link via `OwnerMeetingLink__c` formula field

**Decision:** Replace the hardcoded Outlook booking URL with a formula field that resolves `Owner:User.MeetingLink__c` at query time.

**Rationale:**
- V1 embeds `https://outlook.office365.com/book/sales@statista.com/` directly in topic Instruction 3. This is a single shared link for all sellers.
- V2 moved it to a Flow variable (still hardcoded, but in one place).
- V3 resolves it dynamically from the Lead Owner's User record. Each seller maintains their own link — Outlook, Calendly, or any other tool.
- Link changes require only a User record update (admin action), not a deployment.
- Works automatically when leads are reassigned to different owners.

**Trade-off:** Requires all Lead Owners to have `MeetingLink__c` populated. Mitigated by the fault gate (Step 3 in Flow: if blank → Task + stop).

---

## D2: Explicit fault gate for missing meeting link

**Decision:** If `OwnerMeetingLink__c` is blank, the Flow creates a Task and stops — no email is generated.

**Rationale:**
- An email offering "connect with [Seller Name]" but with no meeting link is broken CTA.
- Better to route to a human than to send an incomplete email.
- The Task alerts the Lead Owner that their `MeetingLink__c` needs configuration.
- V1 had no equivalent safeguard — the hardcoded URL always existed.

**Alternative considered:** Fall back to a shared/default booking URL. Rejected — this defeats the purpose of per-seller links and could route meetings to the wrong person.

---

## D3: Locale resolution at Flow level (not PT level)

**Decision:** The Flow resolves Country → locale code and passes it to the PT as a string input.

**Rationale:**
- PT shouldn't make data-model decisions (what country maps to what locale).
- Flow Decision nodes are deterministic, testable, and auditable.
- Adding a new locale = one new Decision rule + one PT locale block. No prompt redesign.
- The PT receives a simple string and applies it — separation of concerns.

**Alternative considered:** Pass Country directly to the PT and let it decide the locale. Rejected — this pushes a deterministic decision into a probabilistic layer (LLM might misclassify "DE" as German-locale when we want English with en-GB default).

---

## D4: Seller name from `Owner.Name` (not GetRecordDetails)

**Decision:** Retrieve seller name via the standard `Owner.Name` relationship in the Lead query.

**Rationale:**
- V1 calls `GetRecordDetails` (a standard invocable action) to get a text blob, then the planner extracts the Owner name from unstructured text. This costs tokens and introduces extraction risk.
- A direct relationship query (`Get_Lead_Record.Owner.Name`) is deterministic and free.
- Eliminates one planner action entirely.

**Trade-off:** None. Strictly better.

---

## D5: Keep Reply vs Opt-Out disambiguation in the planner

**Decision:** The planner still routes between Meeting Response and Manage Opt-Out based on topic `scope` descriptions when OrchestrationStage = "Reply".

**Rationale:**
- Intent classification (is this reply positive or negative?) is a natural-language task — the planner's strength.
- Moving this into a Flow would require a classification PT call before routing, adding latency and Flex cost for a task the planner already does well.
- V1 uses this pattern successfully. No evidence of misrouting.

**Alternative considered:** Single "Reply Handler" topic that classifies internally and branches. Rejected — combines two very different response patterns into one complex Flow, loses topic-level observability.

---

## D6: PT generates conversation summary (not a separate step)

**Decision:** The Meeting Response PT returns both `reply` and `summary` in a single JSON response.

**Rationale:**
- The PT already reads and comprehends the lead's email to generate the reply. Producing a 1-2 bullet summary is marginal additional work (no extra context needed).
- Separating summarization into a second PT call would double Flex cost for this topic.
- The summary is constrained to what the lead actually said — grounded in the same input the PT already processes.

**Trade-off:** PT output is JSON (2 fields) rather than plain text. Requires Apex parsing. Acceptable — the parser is simple, tested, and reusable.

---

## D7: 5-bullet cap on LeadDescription__c with LIFO ordering

**Decision:** New bullets prepend (newest at top). When count exceeds 5, oldest bullets are dropped.

**Rationale:**
- Sales teams care most about recent interactions. Oldest context is least actionable.
- A cap prevents the field from growing unbounded (rich text field limits, CRM readability).
- 5 bullets ≈ the last 5 meaningful interactions — enough context for a seller to prepare for a call.
- LIFO ordering means the most relevant context is always at the top of the field.

**Alternative considered:** No cap (append indefinitely). Rejected — field bloat, poor UX in the CRM.

---

## D8: V3 scoped to Meeting Response only (not all 4 topics)

**Decision:** This PoC refactors Meeting Response in isolation. Other topics follow the same pattern but are separate efforts.

**Rationale:**
- Meeting Response is the highest-complexity V1 topic (7 instructions, 2 actions, meeting link injection, seller resolution, record updates).
- It validates the full V3 pattern: dynamic data resolution, locale, PT generation, Apex parsing, DML, conversation logging.
- Success here proves the pattern for Follow-Up Outreach and Manage Opt-Out with lower risk.
- Independent deployment means rollback doesn't affect other topics.

---

## D9: ISO date format in summary bullets (YYYY-MM-DD)

**Decision:** Summary bullets use `[YYYY-MM-DD]` regardless of locale.

**Rationale:**
- ISO 8601 is unambiguous (no DD/MM vs MM/DD confusion).
- CRM is read by internal teams across regions — a universal format avoids misinterpretation.
- The date in bullets is for internal logging, not customer-facing content.

**Alternative considered:** Locale-specific dates (DD/MM for UK, MM/DD for US). Rejected — internal-facing data should be unambiguous; locale only applies to customer-facing email content.
