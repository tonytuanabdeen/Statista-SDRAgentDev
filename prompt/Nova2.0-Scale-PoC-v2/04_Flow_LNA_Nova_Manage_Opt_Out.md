# Flow: LNA Nova - Manage Opt-Out

**API Name:** `LNA_Nova_Manage_Opt_Out`  
**Type:** AutoLaunchedFlow  
**Description:** Orchestrates opt-out classification, response generation, deterministic lead unqualification, and conversation logging

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
| `varSummary` | String | Conversation log bullet from PT |
| `varPTResponse` | String | Raw JSON response from the PT |

---

## Flow Steps

### 1. Get Lead Record

```
Record Lookup: Get_Lead_Record
Object: Lead
Filter: Id = {InputLeadId}
Fields: Id, FirstName, Country, LeadDescription__c
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
  "reply": "the generated reply email text",
  "summary": "1 bullet summarizing the opt-out event"
}
```

```
Apex Action: Parse_Opt_Out_Response
  Input: varPTResponse
  Outputs:
    - classification → varClassification
    - reply → varReplyBody
    - summary → varSummary
  
Assignment: Set_Email_Output
  varEmailOutput = varReplyBody
```

> **Implementation note:** Use the shared Apex invocable JSON parser. See `09_Apex_JSON_Parser.md`.

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

### 6. Update LeadDescription__c (Conversation Log)

```
Apex Action: Update_Lead_Description
  Inputs:
    - existingDescription: {Get_Lead_Record.LeadDescription__c}
    - newSummary: {varSummary}
  Output:
    - mergedDescription → varNewDescription

Record Update: Update_Description
Object: Lead
Filter: Id = {InputLeadId}
Fields:
  - LeadDescription__c = {varNewDescription}
```

> **Implementation note:** The Apex action prepends the new bullet, preserves existing bullets verbatim, and enforces the 5-bullet cap.

### 7. Return

Flow ends. `varEmailOutput` is returned to the agent.

---

## Flow Diagram

```
Start
  │
  ▼
Get Lead Record (Id, FirstName, Country, LeadDescription__c)
  │
  ▼
Resolve Locale ──┬── US → "en-US"
                 └── Default → "en-GB"
  │
  ▼
Classify & Generate Response (PT: LNA_Nova_Opt_Out_Response)
  │
  ▼
Parse JSON → varClassification + varReplyBody + varSummary
  │
  ▼
Decision: Apply_Classification
  ├── SPAM → Update: Status="Unqualified", Reason="Spam"
  ├── NOT_INTERESTED → Update: Status="Unqualified", Reason="Customer Not Interested"
  └── OPT_OUT → Update: Status="Unqualified", Reason="Opt-out", HasOptedOutOfEmail=true
  │
  ▼
Update LeadDescription__c (prepend summary bullet)
  │
  ▼
End (return varEmailOutput)
```

---

## Key Design Decisions

1. **Picklist values are NEVER in the planner's hands.** The Flow Decision element maps the PT's classification output to exact field values using deterministic branching. This eliminates the V1 risk where the planner might predict "Not Interested" instead of "Customer Not Interested".

2. **Classification is PT output, not planner judgment.** The PT classifies the reply using structured reasoning; the Flow routes deterministically based on the result.

3. **HasOptedOutOfEmail only set for OPT_OUT.** The branching ensures this flag is never accidentally set for SPAM or NOT_INTERESTED leads.

4. **Conversation logging is Flow-managed.** The PT returns a `summary` field; the Apex action handles the merge logic. No planner-side string manipulation.

## Fault Handling

If the Apex JSON parser fails (malformed PT output), the Flow should:
1. Create a Task assigned to the Lead Owner with subject "Nova: Opt-Out Processing Failed"
2. NOT send any email to the lead
3. NOT update any Lead fields
