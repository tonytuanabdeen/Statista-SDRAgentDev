### Instructions
- Execute agent test according to the configuration defined in {INPUT_NUDGES_TEST} 
- Ensure the process iterates through the {LEAD_RECORD_IDS} records. 
- During execution, for each Lead record created, dynamically pass the following input & context variables:
    - {AGENT_API_NAME}.
    - Set {DATETIME} to the current timestamp in milliseconds.
    - $Context.currentRecordId is set to {LEAD_RECORD_IDS}
    - $Context.ContactId is set to same Lead Record ID
    - $Context.emailBody is set to "Subject:" {PREVIOUS_EMAIL_SUBJECT} "Email Body:" {PREVIOUS_EMAIL_BODY}
- This ensures the agent generates the Follow-up Nudge email using the specific {LEAD_RECORD_IDS} records. 
- Save the generated agent test specification in the {OUTPUT_FOLDER} folder as a YAML file named {OUTPUT_FILE_NUDGES_TEST_SPECS}

### Response Format
 - Save the test results in the {OUTPUT_FOLDER} folder as a Markdown file named: {OUTPUT_FILE_NUDGES_TEST_RESULTS}.
 - Ensure each row in the table corresponds to the test results for a Lead record. 
 - Detailed Results Section: for each Lead record do the following:
 **Row Count**. **Lead Name** - **Title**

 | Field | Value |
 |-------|-------|
 | **Lead Name** | Lead Name |
 | **Title** | Title |
 | **Initial Outreach Email Subject** | Initial Outreach Email Subject |
 | **Nudge Email Subject** | Nudge Email Subject |
 | **Test Result** | Perform an assertion to validate that the Initial Outreach Email Subject matches the Nudge Email Subject |

 **Email Body:** 
 ```
 Email Body
 ```