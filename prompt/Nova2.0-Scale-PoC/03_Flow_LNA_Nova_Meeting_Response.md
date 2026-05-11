# Flow: LNA Nova - Meeting Response

**API Name:** `LNA_Nova_Meeting_Response`  
**Type:** AutoLaunchedFlow  
**Description:** Orchestrates meeting response email generation, seller resolution, and Lead rating update

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

---

## Flow Steps

### 1. Get Lead Record (with Owner)

```
Record Lookup: Get_Lead_Record
Object: Lead
Filter: Id = {InputLeadId}
Fields: Id, FirstName, Title, Country, OwnerId, Owner.Name
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
  - promptResponse → {varEmailOutput}
```

### 6. Update Lead Rating (Deterministic)

```
Record Update: Update_Lead_Rating
Object: Lead
Filter: Id = {InputLeadId}
Field Updates:
  - Rating = "Warm"
```

### 7. Return

Flow ends. `varEmailOutput` is returned to the agent.

---

## Flow Diagram

```
Start
  │
  ▼
Get Lead Record (incl. Owner.Name)
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
Update Lead: Rating = "Warm" (deterministic DML)
  │
  ▼
End (return varEmailOutput)
```

---

## Key Design Decision

The `Rating = "Warm"` update is now a Flow DML step, not a planner action. This eliminates the risk of the planner forgetting to call the update action or passing wrong field values.
