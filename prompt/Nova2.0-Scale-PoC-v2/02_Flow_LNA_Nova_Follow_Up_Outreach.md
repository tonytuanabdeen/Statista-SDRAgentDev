# Flow: LNA Nova - Follow-Up Outreach

**API Name:** `LNA_Nova_Follow_Up_Outreach`  
**Type:** AutoLaunchedFlow  
**Description:** Orchestrates follow-up nudge email generation with locale resolution

---

## Input Variables

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `InputLeadId` | String | Yes | The Lead record ID |
| `emailBody` | String | Yes | The previous outreach email body |
| `isFinalMessage` | Boolean | Yes | Whether this is the last nudge in the cadence |

## Output Variables

| Variable | Type | Description |
|----------|------|-------------|
| `varEmailOutput` | String | Generated nudge email (subject + body) |

## Internal Variables

| Variable | Type | Description |
|----------|------|-------------|
| `varLocale` | String | Resolved locale (en-GB or en-US) |

---

## Flow Steps

### 1. Get Lead Record

```
Record Lookup: Get_Lead_Record
Object: Lead
Filter: Id = {InputLeadId}
Fields: Id, FirstName, Title, Country, Name
Get First Record Only: true
```

### 2. Resolve Locale

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

### 3. Generate Nudge Email (Prompt Template)

```
Action Call: Generate_Nudge_Email
Action: generatePromptResponse
Template: LNA_Nova_Follow_Up_Nudge

Inputs:
  - Input:Lead → {Get_Lead_Record}
  - Input:EmailBody → {emailBody}
  - Input:IsFinalMessage → {isFinalMessage}
  - Input:Locale → {varLocale}

Output:
  - promptResponse → {varEmailOutput}
```

### 4. Return

Flow ends. `varEmailOutput` is returned to the agent.

---

## Flow Diagram

```
Start
  │
  ▼
Get Lead Record (Id, FirstName, Title, Country)
  │
  ▼
Resolve Locale ──┬── US → varLocale = "en-US"
                 └── Default → varLocale = "en-GB"
  │
  ▼
Generate Nudge Email (PT: LNA_Nova_Follow_Up_Nudge)
  │
  ▼
End (return varEmailOutput)
```

---

## Design Notes

- No record updates needed — follow-up nudges don't change lead status
- The PT handles both standard nudge and final message logic via `IsFinalMessage` param
- Meeting link for final messages is embedded in the PT content (not a Flow variable) because it's static and only used in one code path
