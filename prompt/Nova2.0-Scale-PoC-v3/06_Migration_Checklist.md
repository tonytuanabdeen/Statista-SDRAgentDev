# Migration Checklist: Meeting Response (V3)

## Prerequisites

- [ ] `OwnerMeetingLink__c` formula field deployed to target org (confirmed in repo)
- [ ] Lead Owners have `MeetingLink__c` populated on their User records
- [ ] `LNA_Nova_ResponseParser` Apex class deployed (shared dependency)

---

## Build Order

### Phase 1: Apex Parser (if not already deployed from Opt-Out migration)

- [ ] Create `LNA_Nova_ResponseParser` Apex class
- [ ] Implement `parseMeetingResponse` invocable method
- [ ] Implement `mergeLeadDescription` invocable method
- [ ] Write unit tests (all scenarios from `04_Apex_Response_Parser.md`)
- [ ] Deploy to target org
- [ ] Verify invocable methods appear in Flow Builder

### Phase 2: Prompt Template

- [ ] Create `LNA_Nova_Meeting_Response_Email` prompt template
- [ ] Set model to `sfdc_ai__DefaultVertexAIGemini25Flash001`
- [ ] Configure 5 input parameters (Lead, EmailBody, SellerName, MeetingLink, Locale)
- [ ] Paste prompt content from `03_PT_LNA_Nova_Meeting_Response_Email.md`
- [ ] Test with en-GB locale (UK lead)
- [ ] Test with en-US locale (US lead)
- [ ] Verify JSON output structure (`reply` + `summary` fields)
- [ ] Verify no sign-off appended
- [ ] Verify meeting link appears on its own line
- [ ] Verify seller name referenced correctly
- [ ] Verify prompt injection resistance (embed directive in EmailBody)

### Phase 3: Flow Orchestration

- [ ] Create `LNA_Nova_Meeting_Response` autolaunched Flow
- [ ] Add input variables: `InputLeadId` (String), `emailBody` (String)
- [ ] Add output variable: `varEmailOutput` (String)
- [ ] Step 1: Record Lookup — Get Lead (Id, FirstName, Title, Country, Owner.Name, OwnerMeetingLink__c, LeadDescription__c)
- [ ] Step 2: Assignment — varSellerName, varMeetingLink
- [ ] Step 3: Decision — Validate Meeting Link (if blank → Task + End)
- [ ] Step 4: Decision — Resolve Locale (US → en-US, Default → en-GB)
- [ ] Step 5: Action — Call PT (LNA_Nova_Meeting_Response_Email)
- [ ] Step 6: Action — Apex parseMeetingResponse
- [ ] Step 7: Decision — Validate parse (if null → Task + End)
- [ ] Step 8: Assignment — varEmailOutput = varReplyBody
- [ ] Step 9: Record Update — Rating = "Warm"
- [ ] Step 10: Action — Apex mergeLeadDescription
- [ ] Step 11: Record Update — LeadDescription__c = varMergedDescription
- [ ] Activate Flow
- [ ] Test: end-to-end with UK lead
- [ ] Test: end-to-end with US lead
- [ ] Test: Lead Owner with blank MeetingLink__c (expect Task created)
- [ ] Test: Malformed PT response (expect Task created)

### Phase 4: Planner Bundle Update

- [ ] Wire `LNA_Nova_Meeting_Response` Flow as new topic action
- [ ] Replace 7 topic instructions with 2 (from `01_Topic_Instructions.md`)
- [ ] Update topic `scope` description (V3 version from `01_Topic_Instructions.md`)
- [ ] Remove `GetRecordDetails_179bY000001jeX4` local action
- [ ] Remove `LNA_Nova_Update_Lead_Record_179bY000001jeX4` local action
- [ ] Deploy planner bundle
- [ ] Test: agent routing (Reply stage → Meeting Response topic)
- [ ] Test: full cycle (lead reply → email generated → Rating updated → Description logged)

### Phase 5: Regression & Cleanup

- [ ] Verify `ruleExpressions` still route correctly (Intro/Nudge/Reply)
- [ ] Verify Manage Opt-Out topic still receives negative replies
- [ ] Verify Initial Outreach and Follow-Up Outreach topics unaffected
- [ ] Verify `AnswerQuestionsWithKnowledge` global action unaffected
- [ ] End-to-end cadence test: Intro → Nudge × 3 → Positive Reply → Meeting Response
- [ ] End-to-end cadence test: Intro → Nudge × 3 → Negative Reply → Opt-Out (not Meeting Response)
- [ ] Monitor Flex Credit consumption (expect net reduction from token savings)
- [ ] Consider retiring `LNA_Nova_Update_Lead_Record` Flow (if Opt-Out also migrated)

---

## Rollback Plan

Each phase is independently deployable. If Phase 4 (planner bundle) fails:

1. Revert planner bundle to V1 instructions (7 instructions)
2. Re-add `GetRecordDetails` and `LNA_Nova_Update_Lead_Record` local actions
3. Deactivate the new Flow (Draft status)
4. PT remains deployed but unused (no impact)
5. Apex class remains deployed (no impact, invocable methods are inactive without Flow)

No data migration needed — `LeadDescription__c` format is backwards-compatible.

---

## Validation Criteria

| Criterion | How to Verify |
|-----------|---------------|
| Email references specific content from lead's reply | Manual review of 5+ test replies |
| Seller name matches Lead Owner | Compare email output vs. Lead Owner record |
| Meeting link matches Owner's `MeetingLink__c` | Compare email output vs. User record |
| Rating = "Warm" after response | Query Lead record post-execution |
| LeadDescription__c has new bullet | Read field value, verify YYYY-MM-DD format |
| Bullet cap at 5 | Test with Lead that already has 5 bullets |
| en-GB spelling for UK leads | Check for "organisation", "colour" patterns |
| en-US spelling for US leads | Check for "organization", "color" patterns |
| No sign-off in email | Verify email ends with meeting link line |
| Fault path: missing meeting link | Verify Task created, no email sent |
| Fault path: malformed PT JSON | Verify Task created, no email sent |
