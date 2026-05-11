# Flow: LNA Nova - Meeting Response (V3)

**API Name:** `LNA_Nova_Meeting_Response`  
**Type:** AutoLaunchedFlow  
**Description:** Orchestrates meeting response email generation with dynamic seller/meeting-link resolution, locale-aware generation, deterministic Lead rating update, and conversation logging.

---

## Input Variables

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `InputLeadId` | String | Yes | The Lead record ID |
| `emailBody` | String | Yes | The lead's reply email body |

## Output Variables

| Variable | Type | Description |
|----------|------|-------------|
| `varEmailOutput` | String | Generated meeting response email (subject + body) |

## Internal Variables

| Variable | Type | Description |
|----------|------|-------------|
| `varLocale` | String | Resolved locale (en-GB or en-US) |
| `varSellerName` | String | Lead Owner's display name |
| `varMeetingLink` | String | Dynamic from `OwnerMeetingLink__c` |
| `varPTResponse` | String | Raw PT response (JSON) |
| `varReplyBody` | String | Extracted email body |
| `varSummary` | String | Extracted conversation summary |
| `varExistingDescription` | String | Current `LeadDescription__c` value |
| `varMergedDescription` | String | After Apex merge (prepend + cap) |

---

## Flow Steps

### 1. Get Lead Record (with Owner fields)

```
Record Lookup: Get_Lead_Record
Object: Lead
Filter: Id = {InputLeadId}
Fields:
  - Id
  - FirstName
  - Title
  - Country
  - OwnerId
  - Owner.Name
  - OwnerMeetingLink__c       ← formula: Owner:User.MeetingLink__c
  - LeadDescription__c
Get First Record Only: true
Store: Get_Lead_Record (SObject variable)
```

**Why `OwnerMeetingLink__c` instead of a related Owner lookup?**  
Formula fields resolve cross-object references at query time without requiring a subquery. The field is already deployed (SFBUILD-4919) and returns the Owner's `MeetingLink__c` User field directly on the Lead.

---

### 2. Assign Seller Name + Meeting Link

```
Assignment: Assign_Context
  varSellerName = {Get_Lead_Record.Owner.Name}
  varMeetingLink = {Get_Lead_Record.OwnerMeetingLink__c}
```

---

### 3. Validate Meeting Link (Fault Gate)

```
Decision: Validate_Meeting_Link

Rule: "Link_Available"
  Condition: {varMeetingLink} IS NOT NULL
             AND {varMeetingLink} != ""
  → Continue to Step 4

Default: "Link_Missing"
  → Create Task for Lead Owner:
      Subject: "Nova: Meeting link missing — cannot respond to lead reply"
      Description: "Lead {InputLeadId} replied but the Lead Owner has no MeetingLink__c configured."
      OwnerId: {Get_Lead_Record.OwnerId}
      WhatId: {InputLeadId}
  → End (no email returned)
```

**Why validate?** If the Lead Owner hasn't configured their booking link, sending an email without one is worse than creating a Task for human follow-up.

---

### 4. Resolve Locale

```
Decision: Resolve_Locale

Rule: "US_Locale"
  Condition: {Get_Lead_Record.Country} = "United States"
             OR {Get_Lead_Record.Country} = "US"
             OR {Get_Lead_Record.Country} = "USA"
  → Assignment: varLocale = "en-US"

Default: "Default_UK"
  → Assignment: varLocale = "en-GB"
```

**Extensibility:** Adding `en-AU` or other locales requires only a new Decision rule and a PT locale handler. No structural changes.

---

### 5. Generate Meeting Response Email (Prompt Template)

```
Action Call: Generate_Meeting_Response
Action Type: generatePromptResponse
Template: LNA_Nova_Meeting_Response_Email

Inputs:
  - Input:Lead       → {Get_Lead_Record}
  - Input:EmailBody  → {emailBody}
  - Input:SellerName → {varSellerName}
  - Input:MeetingLink → {varMeetingLink}
  - Input:Locale     → {varLocale}

Output:
  - promptResponse → varPTResponse (JSON string)
```

---

### 6. Parse PT Response (Apex Invocable)

```
Action Call: Parse_Meeting_Response
Action: LNA_Nova_ResponseParser.parseMeetingResponse

Input:
  - jsonResponse → {varPTResponse}

Output:
  - reply   → varReplyBody
  - summary → varSummary
```

**Fault check:**
```
Decision: Parse_Success
  Rule: varReplyBody IS NOT NULL AND varReplyBody != ""
    → Continue
  Default:
    → Create Task (malformed PT output)
    → End
```

---

### 7. Assign Email Output

```
Assignment: Assign_Output
  varEmailOutput = {varReplyBody}
```

---

### 8. Update Lead Rating (Deterministic)

```
Record Update: Update_Lead_Rating
Object: Lead
Filter: Id = {InputLeadId}
Field Updates:
  - Rating = "Warm"
```

No planner involvement. This is a business rule: any non-negative reply → Rating = Warm.

---

### 9. Merge + Update LeadDescription__c

```
Action Call: Merge_Description
Action: LNA_Nova_ResponseParser.mergeLeadDescription

Input:
  - existingDescription → {Get_Lead_Record.LeadDescription__c}
  - newSummary → {varSummary}

Output:
  - mergedDescription → varMergedDescription
```

```
Record Update: Update_Lead_Description
Object: Lead
Filter: Id = {InputLeadId}
Field Updates:
  - LeadDescription__c = {varMergedDescription}
```

---

### 10. End

Flow ends. `varEmailOutput` is returned to the agent for delivery.

---

## Flow Diagram

```
Start
  │
  ▼
Get Lead Record (Id, FirstName, Title, Country, Owner.Name,
                 OwnerMeetingLink__c, LeadDescription__c)
  │
  ▼
Assign: varSellerName + varMeetingLink
  │
  ▼
Decision: Meeting Link Available?
  ├── NO → Create Task ("Meeting link missing") → End
  │
  ▼ YES
Decision: Resolve Locale
  ├── US/USA → varLocale = "en-US"
  └── Default → varLocale = "en-GB"
  │
  ▼
Call PT: LNA_Nova_Meeting_Response_Email
  (Lead, EmailBody, SellerName, MeetingLink, Locale)
  │
  ▼
Apex: Parse JSON → varReplyBody + varSummary
  │
  ▼
Decision: Parse OK?
  ├── NO → Create Task ("Malformed PT output") → End
  │
  ▼ YES
Assign: varEmailOutput = varReplyBody
  │
  ▼
Record Update: Rating = "Warm"
  │
  ▼
Apex: Merge LeadDescription__c (prepend summary, cap at 5)
  │
  ▼
Record Update: LeadDescription__c = varMergedDescription
  │
  ▼
End (return varEmailOutput)
```

---

## Key Design Decisions (V3 vs V2)

| Decision | V2 | V3 | Rationale |
|----------|----|----|-----------|
| Meeting link source | Hardcoded Flow variable | `OwnerMeetingLink__c` formula field | Per-seller links; zero-maintenance on seller changes |
| Missing link handling | Not addressed | Explicit fault gate + Task creation | Prevents sending linkless emails |
| Parse validation | Implied | Explicit Decision node after Apex parse | Clearer fault path; debuggable |
| DML sequencing | Rating then Description in sequence | Same, but explicit step separation | Each update is independently auditable |

---

## Error Scenarios

| Scenario | Flow Behavior | User Experience |
|----------|--------------|-----------------|
| Lead not found | Flow fault → unhandled exception | Agent receives error, creates Task per guardrail |
| Owner has no MeetingLink__c | Task created for Owner | Lead receives no email; human follows up |
| PT returns empty/malformed JSON | Task created for Owner | Lead receives no email; human follows up |
| LeadDescription__c at 5 bullets | Apex drops oldest, prepends new | Seamless; no user impact |
| Country field blank | Defaults to en-GB | Email uses British English |
