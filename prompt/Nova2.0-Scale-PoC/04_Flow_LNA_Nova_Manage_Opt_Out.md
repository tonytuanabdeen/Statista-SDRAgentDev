# Flow: LNA Nova - Manage Opt-Out

**API Name:** `LNA_Nova_Manage_Opt_Out`  
**Type:** AutoLaunchedFlow  
**Description:** Orchestrates opt-out classification, response generation, and deterministic lead unqualification

---

## Input Variables

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `InputLeadId` | String | Yes | The Lead record ID |
| `emailBody` | String | Yes | The lead's reply email body |

## Output Variables

| Variable | Type | Description |
|----------|------|-------------|
| `varEmailOutput` | String | Generated opt-out response email |

## Internal Variables

| Variable | Type | Description |
|----------|------|-------------|
| `varLocale` | String | Resolved locale (en-GB or en-US) |
| `varClassification` | String | Classification result: SPAM, NOT_INTERESTED, or OPT_OUT |
| `varReplyBody` | String | Generated reply text from PT |

---

## Flow Steps

### 1. Get Lead Record

```
Record Lookup: Get_Lead_Record
Object: Lead
Filter: Id = {InputLeadId}
Fields: Id, FirstName, Country
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

### 3. Classify & Generate Response (Prompt Template)

```
Action Call: Classify_And_Respond
Action: generatePromptResponse
Template: LNA_Nova_Opt_Out_Response

Inputs:
  - Input:EmailBody → {emailBody}
  - Input:Locale → {varLocale}

Output:
  - promptResponse → varPTResponse (JSON string)
```

### 4. Parse PT Response

The Prompt Template returns a JSON object:
```json
{
  "classification": "SPAM | NOT_INTERESTED | OPT_OUT",
  "reply": "the generated reply email text"
}
```

```
Assignment: Parse_Classification
  varClassification = Extract "classification" from varPTResponse
  varReplyBody = Extract "reply" from varPTResponse
  varEmailOutput = varReplyBody
```

> **Implementation note:** Use a Formula or Apex Action to parse the JSON. Alternatively, use two separate PT output parameters if the platform supports structured outputs.

### 5. Deterministic Record Update (Decision Branch)

```
Decision: Apply_Classification

Rule: "SPAM"
  Condition: {varClassification} = "SPAM"
  → Record Update: Unqualify_Spam
      Object: Lead
      Filter: Id = {InputLeadId}
      Fields:
        - Status = "Unqualified"
        - UnqualifyReason__c = "Spam"

Rule: "NOT_INTERESTED"
  Condition: {varClassification} = "NOT_INTERESTED"
  → Record Update: Unqualify_Not_Interested
      Object: Lead
      Filter: Id = {InputLeadId}
      Fields:
        - Status = "Unqualified"
        - UnqualifyReason__c = "Customer Not Interested"

Rule: "OPT_OUT"
  Condition: {varClassification} = "OPT_OUT"
  → Record Update: Unqualify_Opt_Out
      Object: Lead
      Filter: Id = {InputLeadId}
      Fields:
        - Status = "Unqualified"
        - UnqualifyReason__c = "Opt-out"
        - HasOptedOutOfEmail = true
```

### 6. Return

Flow ends. `varEmailOutput` is returned to the agent.

---

## Flow Diagram

```
Start
  │
  ▼
Get Lead Record
  │
  ▼
Resolve Locale ──┬── US → "en-US"
                 └── Default → "en-GB"
  │
  ▼
Classify & Generate Response (PT: LNA_Nova_Opt_Out_Response)
  │
  ▼
Parse JSON → varClassification + varReplyBody
  │
  ▼
Decision: Apply_Classification
  ├── SPAM → Update: Status="Unqualified", Reason="Spam"
  ├── NOT_INTERESTED → Update: Status="Unqualified", Reason="Customer Not Interested"
  └── OPT_OUT → Update: Status="Unqualified", Reason="Opt-out", HasOptedOutOfEmail=true
  │
  ▼
End (return varEmailOutput)
```

---

## Key Design Decision

Picklist values are NEVER in the planner's hands. The Flow Decision element maps the PT's classification output to exact field values using deterministic branching. This eliminates the V1 risk where the planner might predict "Not Interested" instead of "Customer Not Interested" and silently break downstream automations.
