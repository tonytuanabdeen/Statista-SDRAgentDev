# Flow: LNA Nova - Meeting Response

**API Name:** `LNA_Nova_Meeting_Response`  
**Type:** AutoLaunchedFlow  
**Description:** Orchestrates meeting response email generation, seller resolution, Lead rating update, and conversation logging

---

## Input Variables

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `InputLeadId` | String | Yes | The Lead record ID |
| `emailBody` | String | Yes | The lead's reply email body |

## Output Variables

| Variable | Type | Description |
|----------|------|-------------|
| `varEmailOutput` | String | Generated meeting response email |

## Internal Variables

| Variable | Type | Description |
|----------|------|-------------|
| `varLocale` | String | Resolved locale (en-GB or en-US) |
| `varSellerName` | String | Lead Owner's display name |
| `varMeetingLink` | String | Hardcoded booking link |
| `varPTResponse` | String | Raw PT response (JSON) |
| `varReplyBody` | String | Extracted email body from PT response |
| `varSummary` | String | Extracted conversation summary from PT response |
| `varExistingDescription` | String | Current LeadDescription__c value |

---

## Flow Steps

### 1. Get Lead Record (with Owner)

```
Record Lookup: Get_Lead_Record
Object: Lead
Filter: Id = {InputLeadId}
Fields: Id, FirstName, Title, Country, OwnerId, Owner.Name, LeadDescription__c
Get First Record Only: true
```

### 2. Assign Seller Name

```
Assignment: Assign_Seller_Name
  varSellerName = {Get_Lead_Record.Owner.Name}
```

### 3. Assign Meeting Link

```
Assignment: Assign_Meeting_Link
  varMeetingLink = "https://outlook.office.com/bookwithme/user/41949760dc4146dc81a9dabaa442f9f0@statista.com/meetingtype/kI1Wg4drn0OO3DteX6_24w2?bookingcode=9f3ce907-60d0-493f-aa05-88ce9e265f54&anonymous&ismsaljsauthenabled&ep=mCardFromTile"
```

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

### 5. Generate Meeting Response Email (Prompt Template)

```
Action Call: Generate_Meeting_Response
Action: generatePromptResponse
Template: LNA_Nova_Meeting_Response_Email

Inputs:
  - Input:Lead → {Get_Lead_Record}
  - Input:EmailBody → {emailBody}
  - Input:SellerName → {varSellerName}
  - Input:MeetingLink → {varMeetingLink}
  - Input:Locale → {varLocale}

Output:
  - promptResponse → varPTResponse (JSON string)
```

### 6. Parse PT Response

The PT returns a JSON object:
```json
{
  "reply": "the generated email text",
  "summary": "1-2 bullet summary of the lead's reply"
}
```

```
Assignment: Parse_Response
  varReplyBody = Extract "reply" from varPTResponse
  varSummary = Extract "summary" from varPTResponse
  varEmailOutput = varReplyBody
```

> **Implementation note:** Use an Apex Action to parse the JSON. See `09_Apex_JSON_Parser.md` for the invocable class design.

### 7. Update Lead Rating (Deterministic)

```
Record Update: Update_Lead_Rating
Object: Lead
Filter: Id = {InputLeadId}
Field Updates:
  - Rating = "Warm"
```

### 8. Update LeadDescription__c (Conversation Log)

```
Assignment: Build_Description
  varExistingDescription = {Get_Lead_Record.LeadDescription__c}
  
  // Prepend new summary bullets to existing description
  // Format: "Nova's Update<br>" + new bullets + existing bullets (cap at 5)
  
Record Update: Update_Lead_Description
Object: Lead
Filter: Id = {InputLeadId}
Field Updates:
  - LeadDescription__c = {varNewDescription}
```

> **Implementation note:** The Apex JSON parser action can also handle the LeadDescription__c merge logic (prepend new bullets, enforce 5-bullet cap, preserve existing bullets verbatim). This keeps the Flow simple and avoids complex formula string manipulation.

### 9. Return

Flow ends. `varEmailOutput` is returned to the agent.

---

## Flow Diagram

```
Start
  │
  ▼
Get Lead Record (incl. Owner.Name, LeadDescription__c)
  │
  ▼
Assign Seller Name + Meeting Link
  │
  ▼
Resolve Locale ──┬── US → varLocale = "en-US"
                 └── Default → varLocale = "en-GB"
  │
  ▼
Generate Meeting Response (PT: LNA_Nova_Meeting_Response_Email)
  │
  ▼
Parse JSON → varReplyBody + varSummary
  │
  ▼
Update Lead: Rating = "Warm" (deterministic DML)
  │
  ▼
Update Lead: LeadDescription__c (prepend summary)
  │
  ▼
End (return varEmailOutput)
```

---

## Key Design Decisions

1. **Rating = "Warm" is deterministic** — every positive reply warrants this. No planner judgment needed.
2. **Seller name from Owner.Name** — eliminates `GetRecordDetails` action from the planner bundle.
3. **Meeting link as Flow variable** — if it changes, update one place instead of multiple topic instructions.
4. **Conversation log via Apex parser** — avoids planner-side string manipulation that was error-prone in V1.
