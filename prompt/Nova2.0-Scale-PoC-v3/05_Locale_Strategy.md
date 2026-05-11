# Locale Strategy: Meeting Response (V3)

## Problem

V1 has no locale support — all emails are generated in implicit British English. As Statista scales SDR coverage to US and APAC markets, emails must match the recipient's English dialect.

---

## Architecture

Locale handling is split across two layers:

| Layer | Responsibility | Example |
|-------|---------------|---------|
| **Flow** (Resolution) | Map Lead.Country → locale code | "United States" → "en-US" |
| **PT** (Application) | Generate email in the resolved locale | "organisation" (en-GB) vs "organization" (en-US) |

The **planner** has zero locale awareness. It doesn't know or care what locale the lead is in.

---

## Flow: Locale Resolution Decision

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

---

## PT: Locale Application

The PT receives `{!$Input:Locale}` and applies spelling rules:

```
## Spelling & Locale

Write in {!$Input:Locale} English.
- If en-GB: Use British spelling (colour, organisation, programme, centre, travelled, behaviour).
- If en-US: Use American spelling (color, organization, program, center, traveled, behavior).
Apply this consistently throughout the entire email.
```

---

## Extensibility: Adding New Locales

### Step 1 — Flow Decision Rule

Add a new rule to the `Resolve_Locale` Decision:

```
Rule: "AU_Locale"
  Condition: {Get_Lead_Record.Country} = "Australia"
             OR {Get_Lead_Record.Country} = "AU"
  → Assignment: varLocale = "en-AU"
```

### Step 2 — PT Locale Block

Add to the Spelling & Locale section:

```
- If en-AU: Use Australian spelling (same as British: colour, organisation, centre).
  Use Australian idioms where natural (e.g., "keen to" instead of "interested in").
```

### Step 3 — No Other Changes

- No topic instruction changes
- No planner bundle changes
- No Apex changes
- No new PT needed (same template handles all English locales)

---

## Locale Differences (en-GB vs en-US)

Beyond spelling, the locale can influence:

| Aspect | en-GB | en-US |
|--------|-------|-------|
| Spelling | -ise, -our, -re | -ize, -or, -er |
| Date format (in summary bullets) | Same (YYYY-MM-DD ISO) | Same (YYYY-MM-DD ISO) |
| Formality | Slightly more formal | Slightly more casual |
| Common phrasing | "I'd be happy to arrange..." | "I'd love to set up..." |

The PT handles these naturally through the locale instruction. No explicit per-locale templates needed for the current scope.

---

## Country Field Quality

The locale resolution depends on `Lead.Country` being populated and normalized.

| Scenario | Behavior |
|----------|----------|
| Country = "United States" | en-US |
| Country = "US" | en-US |
| Country = "USA" | en-US |
| Country = "United Kingdom" | en-GB (default) |
| Country = "Germany" | en-GB (default — English email regardless) |
| Country = blank/null | en-GB (default) |
| Country = "Murica" (junk data) | en-GB (default) |

**Design choice:** Default to en-GB rather than failing. British English is Statista's home market and the safer default for international leads receiving English-language emails.

---

## Future: Non-English Locales

This architecture supports a path to non-English locales (e.g., `de-DE` for German leads), but that would require:
1. PT content in the target language (or a translation instruction)
2. Tone/cultural adaptation beyond spelling
3. Business decision on which markets get native-language outreach

This is out of scope for V3 but the locale-as-input pattern makes it structurally possible without refactoring.
