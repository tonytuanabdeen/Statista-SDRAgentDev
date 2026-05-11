# Apex: Nova Response Parser (Invocable)

**Class Name:** `LNA_Nova_ResponseParser`  
**Type:** Invocable Apex Action  
**Purpose:** Parse JSON responses from Prompt Templates and handle LeadDescription__c merge logic

---

## Why Apex?

Flow cannot natively parse arbitrary JSON strings. The Prompt Templates for Meeting Response and Manage Opt-Out return structured JSON with multiple fields. An invocable Apex action provides:

1. Reliable JSON parsing (handles edge cases like escaped characters)
2. LeadDescription__c merge logic (prepend, cap at 5 bullets, preserve existing)
3. A single reusable action across both Flows

---

## Invocable Methods

### Method 1: `parseOptOutResponse`

Parses the Opt-Out PT response and returns classification, reply, and summary separately.

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `jsonResponse` | String | Raw JSON string from PT |

**Outputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `classification` | String | SPAM, NOT_INTERESTED, or OPT_OUT |
| `reply` | String | Generated email text |
| `summary` | String | Summary bullet for LeadDescription__c |

### Method 2: `parseMeetingResponse`

Parses the Meeting Response PT response.

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `jsonResponse` | String | Raw JSON string from PT |

**Outputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `reply` | String | Generated email text |
| `summary` | String | Summary bullets for LeadDescription__c |

### Method 3: `mergeLeadDescription`

Handles the LeadDescription__c prepend + cap logic.

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `existingDescription` | String | Current LeadDescription__c value (may be null) |
| `newSummary` | String | New bullet(s) to prepend |

**Outputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `mergedDescription` | String | Final merged description string |

---

## Merge Logic (LeadDescription__c)

```
1. If existingDescription is null/blank:
     return "Nova's Update<br>" + newSummary

2. Extract existing bullets:
     - Strip "Nova's Update<br>" prefix
     - Split on "<br>"
     - Filter out empty strings

3. Build new bullet list:
     - Split newSummary on "<br>"
     - Append existing bullets

4. Enforce 5-bullet cap:
     - If total > 5, keep only first 5 (newest first)

5. Return:
     "Nova's Update<br>" + join(bullets, "<br>")
```

---

## Class Skeleton

```apex
public with sharing class LNA_Nova_ResponseParser {

    public class ParseOptOutInput {
        @InvocableVariable(required=true)
        public String jsonResponse;
    }

    public class ParseOptOutOutput {
        @InvocableVariable
        public String classification;
        @InvocableVariable
        public String reply;
        @InvocableVariable
        public String summary;
    }

    @InvocableMethod(label='Parse Opt-Out Response' description='Parses JSON from the Opt-Out PT')
    public static List<ParseOptOutOutput> parseOptOutResponse(List<ParseOptOutInput> inputs) {
        List<ParseOptOutOutput> results = new List<ParseOptOutOutput>();
        for (ParseOptOutInput input : inputs) {
            ParseOptOutOutput output = new ParseOptOutOutput();
            try {
                Map<String, Object> parsed = (Map<String, Object>) JSON.deserializeUntyped(input.jsonResponse);
                output.classification = (String) parsed.get('classification');
                output.reply = (String) parsed.get('reply');
                output.summary = (String) parsed.get('summary');
            } catch (Exception e) {
                output.classification = null;
                output.reply = null;
                output.summary = null;
            }
            results.add(output);
        }
        return results;
    }
}
```

> **Note:** The Meeting Response parser and merge logic follow the same pattern. Consider a single class with multiple `@InvocableMethod` methods, or a unified method that accepts a `responseType` discriminator. Keep as a single class for maintainability.

---

## Error Handling

- If JSON parsing fails (malformed output, missing fields), return `null` for all output fields
- The calling Flow checks for null `classification`/`reply` and routes to a fault path (create Task for Lead Owner)
- Do NOT throw exceptions — the Flow must handle gracefully

---

## Test Coverage Requirements

| Scenario | Expected |
|----------|----------|
| Valid SPAM JSON | classification=SPAM, reply populated, summary populated |
| Valid NOT_INTERESTED JSON | classification=NOT_INTERESTED, reply populated |
| Valid OPT_OUT JSON | classification=OPT_OUT, reply populated, summary populated |
| Malformed JSON (missing closing brace) | All outputs null |
| Empty string input | All outputs null |
| Null input | All outputs null |
| mergeLeadDescription with null existing | Returns "Nova's Update<br>" + new bullets |
| mergeLeadDescription with 5 existing + 1 new | Returns 5 bullets (oldest dropped) |
| mergeLeadDescription preserves existing bullets verbatim | Exact match on preserved content |
