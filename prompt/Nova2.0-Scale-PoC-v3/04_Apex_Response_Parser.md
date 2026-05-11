# Apex: Meeting Response Parser (V3)

**Class Name:** `LNA_Nova_ResponseParser`  
**Type:** Invocable Apex Action  
**Purpose:** Parse JSON from Meeting Response PT; merge `LeadDescription__c` with bullet cap

---

## Why Apex?

Flow cannot natively parse arbitrary JSON strings. The Meeting Response PT returns:

```json
{
  "reply": "Subject: Re: ...\n\nHi Name,\n\n...",
  "summary": "- [2026-05-11] bullet 1<br>- [2026-05-11] bullet 2"
}
```

An invocable Apex action provides:
1. Reliable JSON extraction (handles newlines, escaped chars in email body)
2. `LeadDescription__c` merge logic (prepend new bullets, enforce 5-bullet cap)
3. Reusable across Meeting Response and Manage Opt-Out Flows

---

## Invocable Methods

### Method: `parseMeetingResponse`

**Label:** Parse Meeting Response  
**Description:** Extracts reply and summary fields from the Meeting Response PT JSON output

**Input:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `jsonResponse` | String | Yes | Raw JSON string from PT |

**Output:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `reply` | String | Generated email text (subject + body) |
| `summary` | String | Summary bullet(s) for `LeadDescription__c` |

---

### Method: `mergeLeadDescription`

**Label:** Merge Lead Description  
**Description:** Prepends new summary bullets to existing `LeadDescription__c`, enforcing a 5-bullet cap

**Input:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `existingDescription` | String | No | Current `LeadDescription__c` value (may be null/blank) |
| `newSummary` | String | Yes | New bullet(s) to prepend (from PT `summary` field) |

**Output:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `mergedDescription` | String | Final merged description ready for DML |

---

## Merge Logic

```
1. If existingDescription is null/blank:
     return "Nova's Update<br>" + newSummary

2. Extract existing bullets:
     - Strip "Nova's Update<br>" prefix if present
     - Split on "<br>"
     - Filter out empty/whitespace-only strings

3. Build combined bullet list:
     - Split newSummary on "<br>"
     - Append existing bullets after new ones (newest first)

4. Enforce 5-bullet cap:
     - If total > 5, keep only first 5 (newest at top, oldest dropped)

5. Return:
     "Nova's Update<br>" + join(bullets, "<br>")
```

---

## Class Implementation

```apex
public with sharing class LNA_Nova_ResponseParser {

    // ─── Parse Meeting Response ─────────────────────────────────────────

    public class MeetingResponseInput {
        @InvocableVariable(required=true)
        public String jsonResponse;
    }

    public class MeetingResponseOutput {
        @InvocableVariable
        public String reply;
        @InvocableVariable
        public String summary;
    }

    @InvocableMethod(label='Parse Meeting Response'
                     description='Extracts reply and summary from Meeting Response PT JSON')
    public static List<MeetingResponseOutput> parseMeetingResponse(List<MeetingResponseInput> inputs) {
        List<MeetingResponseOutput> results = new List<MeetingResponseOutput>();
        for (MeetingResponseInput input : inputs) {
            MeetingResponseOutput output = new MeetingResponseOutput();
            try {
                Map<String, Object> parsed = (Map<String, Object>) JSON.deserializeUntyped(input.jsonResponse);
                output.reply = (String) parsed.get('reply');
                output.summary = (String) parsed.get('summary');
            } catch (Exception e) {
                output.reply = null;
                output.summary = null;
            }
            results.add(output);
        }
        return results;
    }

    // ─── Merge Lead Description ─────────────────────────────────────────

    public class MergeDescriptionInput {
        @InvocableVariable
        public String existingDescription;
        @InvocableVariable(required=true)
        public String newSummary;
    }

    public class MergeDescriptionOutput {
        @InvocableVariable
        public String mergedDescription;
    }

    @InvocableMethod(label='Merge Lead Description'
                     description='Prepends summary bullets to LeadDescription__c with 5-bullet cap')
    public static List<MergeDescriptionOutput> mergeLeadDescription(List<MergeDescriptionInput> inputs) {
        List<MergeDescriptionOutput> results = new List<MergeDescriptionOutput>();
        for (MergeDescriptionInput input : inputs) {
            MergeDescriptionOutput output = new MergeDescriptionOutput();
            output.mergedDescription = doMerge(input.existingDescription, input.newSummary);
            results.add(output);
        }
        return results;
    }

    private static String doMerge(String existing, String newSummary) {
        String PREFIX = 'Nova\'s Update<br>';
        Integer MAX_BULLETS = 5;

        if (String.isBlank(existing)) {
            return PREFIX + newSummary;
        }

        String body = existing.startsWith(PREFIX)
            ? existing.substring(PREFIX.length())
            : existing;

        List<String> existingBullets = new List<String>();
        for (String bullet : body.split('<br>')) {
            if (String.isNotBlank(bullet)) {
                existingBullets.add(bullet.trim());
            }
        }

        List<String> newBullets = new List<String>();
        for (String bullet : newSummary.split('<br>')) {
            if (String.isNotBlank(bullet)) {
                newBullets.add(bullet.trim());
            }
        }

        List<String> combined = new List<String>();
        combined.addAll(newBullets);
        combined.addAll(existingBullets);

        while (combined.size() > MAX_BULLETS) {
            combined.remove(combined.size() - 1);
        }

        return PREFIX + String.join(combined, '<br>');
    }
}
```

---

## Error Handling

- If JSON parsing fails (malformed output, missing fields): return `null` for both `reply` and `summary`
- The calling Flow checks for null `reply` and routes to fault path (Task creation)
- Do NOT throw exceptions — the Flow handles errors gracefully
- If `newSummary` is null/blank in merge: return existing description unchanged

---

## Test Scenarios

| Scenario | Expected |
|----------|----------|
| Valid JSON with reply + summary | Both fields extracted correctly |
| Valid JSON with reply only (no summary key) | reply populated, summary = null |
| Malformed JSON (missing brace) | Both outputs null |
| Empty string input | Both outputs null |
| Null input | Both outputs null |
| JSON with escaped newlines in reply | Newlines preserved in output |
| mergeLeadDescription: null existing + new bullets | Returns "Nova's Update\<br\>" + new |
| mergeLeadDescription: 4 existing + 1 new | 5 bullets, new at top |
| mergeLeadDescription: 5 existing + 2 new | 5 bullets, 2 new at top, 2 oldest dropped |
| mergeLeadDescription: existing without prefix | Handles gracefully, adds prefix |
| mergeLeadDescription: blank newSummary | Returns existing unchanged |

---

## Deployment Note

This class serves both Meeting Response and Manage Opt-Out Flows. The `parseMeetingResponse` method handles the 2-field JSON (`reply`, `summary`). A separate `parseOptOutResponse` method (documented in V2 `08_Apex_JSON_Parser.md`) handles the 3-field JSON (`classification`, `reply`, `summary`) for the Opt-Out topic.

**Limitation:** Salesforce requires each `@InvocableMethod` to be in its own class OR uses a discriminator pattern. If both methods must coexist in one class, use an inner-class approach with a `responseType` discriminator input. See V2 doc for the combined pattern.
