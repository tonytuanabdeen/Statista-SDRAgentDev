# Migration Checklist

## Build Order (recommended sequence)

### Phase 1: Follow-up Outreach (lowest complexity, validates pattern)

- [ ] Create Prompt Template: `LNA_Nova_Follow_Up_Nudge`
- [ ] Create Flow: `LNA_Nova_Follow_Up_Outreach`
- [ ] Wire Flow as topic action in planner bundle
- [ ] Replace 6 topic instructions with 2 slim instructions
- [ ] Test: standard nudge (isFinalMessage = false)
- [ ] Test: final message (isFinalMessage = true)
- [ ] Test: UK lead → en-GB spelling
- [ ] Test: US lead → en-US spelling

### Phase 2: Manage Opt-Out (validates JSON classification + Flow branching)

- [ ] Create Prompt Template: `LNA_Nova_Opt_Out_Response`
- [ ] Create Flow: `LNA_Nova_Manage_Opt_Out`
- [ ] Implement JSON parsing (Apex Action or Formula)
- [ ] Wire Flow as topic action in planner bundle
- [ ] Replace 6 topic instructions with 2 slim instructions
- [ ] Remove `LNA_Nova_Update_Lead_Record` action from topic
- [ ] Test: SPAM classification → Status=Unqualified, Reason=Spam
- [ ] Test: NOT_INTERESTED → Status=Unqualified, Reason=Customer Not Interested
- [ ] Test: OPT_OUT → Status=Unqualified, Reason=Opt-out, HasOptedOutOfEmail=true
- [ ] Test: UK/US locale variations

### Phase 3: Meeting Response (validates seller resolution in Flow)

- [ ] Create Prompt Template: `LNA_Nova_Meeting_Response_Email`
- [ ] Create Flow: `LNA_Nova_Meeting_Response`
- [ ] Wire Flow as topic action in planner bundle
- [ ] Replace 7 topic instructions with 2 slim instructions
- [ ] Remove `GetRecordDetails` action from topic
- [ ] Remove `LNA_Nova_Update_Lead_Record` action from topic
- [ ] Test: positive reply → email with seller name + meeting link
- [ ] Test: concern reply → validation + reframe toward call
- [ ] Test: Rating updated to "Warm" (deterministic)
- [ ] Test: UK/US locale variations

### Phase 4: Regression & Cleanup

- [ ] Verify Sales Cadence orchestration still routes correctly (Intro/Nudge/Reply)
- [ ] Verify topic routing rules unchanged (ruleExpressions still match)
- [ ] Remove unused `GetRecordDetails` local actions from planner bundle
- [ ] Confirm `AnswerQuestionsWithKnowledge` global action unaffected
- [ ] End-to-end test: full cadence lifecycle (Intro → Nudge → Reply → Opt-Out)
- [ ] Monitor Flex Credit consumption delta

---

## Actions Removed from Planner Bundle (post-migration)

| Topic | Action Removed | Reason |
|-------|---------------|--------|
| Follow-up Outreach | `GetRecordDetails` | Lead data now retrieved inside Flow |
| Meeting Response | `GetRecordDetails` | Lead + Owner data retrieved inside Flow |
| Meeting Response | `LNA_Nova_Update_Lead_Record` | Rating update now deterministic in Flow |
| Manage Opt-Out | `LNA_Nova_Update_Lead_Record` | Unqualify logic now deterministic in Flow |

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| PT JSON parsing failure (Opt-Out) | Add fault path in Flow → create Task for Lead Owner |
| Flex Credit increase | Monitor via Einstein Usage dashboard; offset by reduced planner token usage |
| Locale detection edge cases | Default to en-GB for unknown countries; add countries incrementally |
| Regression in cadence routing | ruleExpressions are unchanged; test with existing OrchestrationStage values |
