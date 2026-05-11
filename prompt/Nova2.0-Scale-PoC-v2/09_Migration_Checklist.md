# Migration Checklist

## Build Order (recommended sequence)

### Phase 1: Apex JSON Parser (dependency for Phases 2 & 3)

- [ ] Create `LNA_Nova_ResponseParser` Apex class
- [ ] Implement `parseOptOutResponse` invocable method
- [ ] Implement `parseMeetingResponse` invocable method
- [ ] Implement `mergeLeadDescription` invocable method
- [ ] Write unit tests (all scenarios from `08_Apex_JSON_Parser.md`)
- [ ] Deploy to target org

### Phase 2: Follow-up Outreach (lowest complexity, validates Flow + PT pattern)

- [ ] Create Prompt Template: `LNA_Nova_Follow_Up_Nudge`
- [ ] Create Flow: `LNA_Nova_Follow_Up_Outreach`
- [ ] Wire Flow as topic action in planner bundle (replace `GetRecordDetails`)
- [ ] Replace 6 topic instructions with 2 slim instructions
- [ ] Test: standard nudge (isFinalMessage = false)
- [ ] Test: final message (isFinalMessage = true)
- [ ] Test: UK lead → en-GB spelling
- [ ] Test: US lead → en-US spelling

### Phase 3: Manage Opt-Out (validates JSON classification + Flow branching)

- [ ] Create Prompt Template: `LNA_Nova_Opt_Out_Response` (with `summary` field)
- [ ] Create Flow: `LNA_Nova_Manage_Opt_Out` (with Apex parser + LeadDescription update)
- [ ] Wire Flow as topic action in planner bundle
- [ ] Replace 7 topic instructions with 2 slim instructions
- [ ] Remove `LNA_Nova_Update_Lead_Record` action from Opt-Out topic
- [ ] Test: SPAM classification → Status=Unqualified, Reason=Spam
- [ ] Test: NOT_INTERESTED → Status=Unqualified, Reason=Customer Not Interested
- [ ] Test: OPT_OUT → Status=Unqualified, Reason=Opt-out, HasOptedOutOfEmail=true
- [ ] Test: LeadDescription__c updated with summary bullet
- [ ] Test: UK/US locale variations
- [ ] Test: Malformed PT output → fault path (Task created)

### Phase 4: Meeting Response (validates seller resolution + conversation logging)

- [ ] Create Prompt Template: `LNA_Nova_Meeting_Response_Email` (with `summary` field)
- [ ] Create Flow: `LNA_Nova_Meeting_Response` (with Apex parser + Rating + LeadDescription)
- [ ] Wire Flow as topic action in planner bundle
- [ ] Replace 7 topic instructions with 2 slim instructions
- [ ] Remove `GetRecordDetails` action from Meeting Response topic
- [ ] Remove `LNA_Nova_Update_Lead_Record` action from Meeting Response topic
- [ ] Test: positive reply → email with seller name + meeting link
- [ ] Test: concern reply → validation + reframe toward call
- [ ] Test: Rating updated to "Warm" (deterministic)
- [ ] Test: LeadDescription__c updated with summary bullets
- [ ] Test: UK/US locale variations
- [ ] Test: Malformed PT output → fault path

### Phase 5: Regression & Cleanup

- [ ] Verify Sales Cadence orchestration still routes correctly (Intro/Nudge/Reply)
- [ ] Verify topic routing rules unchanged (ruleExpressions still match)
- [ ] Remove unused `GetRecordDetails` local actions from planner bundle
- [ ] Confirm `AnswerQuestionsWithKnowledge` global action unaffected
- [ ] End-to-end test: full cadence lifecycle (Intro → Nudge × 3 → Reply → Opt-Out)
- [ ] Monitor Flex Credit consumption delta
- [ ] Retire `LNA_Nova_Update_Lead_Record` Flow (no longer needed by any topic)

---

## Actions Removed from Planner Bundle (post-migration)

| Topic | Action Removed | Reason |
|-------|---------------|--------|
| Follow-up Outreach | `GetRecordDetails` | Lead data now retrieved inside Flow |
| Meeting Response | `GetRecordDetails` | Lead + Owner data retrieved inside Flow |
| Meeting Response | `LNA_Nova_Update_Lead_Record` | Rating + LeadDescription now deterministic in Flow |
| Manage Opt-Out | `LNA_Nova_Update_Lead_Record` | Unqualify + LeadDescription now deterministic in Flow |

---

## Planner Bundle Changes

### Topic instruction updates (all 4 topics → 2 instructions each)

| Topic | Action | Details |
|-------|--------|---------|
| Follow-up Outreach | Replace instructions | 6 → 2 (see `01_Topic_Instructions.md`) |
| Meeting Response | Replace instructions | 7 → 2 |
| Manage Opt-Out | Replace instructions | 7 → 2 |
| Initial Outreach | No change | Already at 2 instructions |

### Local action updates

| Topic | Add | Remove |
|-------|-----|--------|
| Follow-up Outreach | `LNA_Nova_Follow_Up_Outreach` (flow) | `GetRecordDetails` |
| Meeting Response | `LNA_Nova_Meeting_Response` (flow) | `GetRecordDetails`, `LNA_Nova_Update_Lead_Record` |
| Manage Opt-Out | `LNA_Nova_Manage_Opt_Out` (flow) | `LNA_Nova_Update_Lead_Record` |

### Rule expressions (unchanged)

- `Intro` → Initial Outreach topic
- `Nudge` → Follow-up Outreach topic  
- `Reply` → Meeting Response + Manage Opt-Out topics

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| PT JSON parsing failure | Apex parser returns null → Flow fault path → Task for Lead Owner |
| Flex Credit increase (more PT calls) | Monitor via Einstein Usage dashboard; offset by ~90% reduction in planner tokens |
| Locale detection edge cases | Default to en-GB for unknown countries; add countries incrementally |
| Regression in cadence routing | ruleExpressions unchanged; test with existing OrchestrationStage values |
| LeadDescription__c merge errors | Apex unit tests cover all edge cases; V1 planner logic was more error-prone |
| Seller name blank (no Lead Owner) | Flow fault path: if Owner.Name is blank, create Task and stop |

---

## Rollback Plan

Each phase is independently deployable. If a phase fails:

1. Revert the planner bundle to the previous topic instructions
2. Re-add the removed local actions
3. Deactivate the new Flow (set status to Draft)
4. The new PT can remain deployed (inactive/unused without the Flow calling it)

No data migration is needed — the LeadDescription__c format is backwards-compatible.
