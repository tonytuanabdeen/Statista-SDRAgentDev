### Instructions
- Execute agent test according to the configuration defined in {INPUT_OPT_OUT_TEST} 
- Ensure the process iterates through the {LEAD_RECORD_IDS} records. 
- During execution, for each Lead record created, dynamically pass the following input & context variables:
    - {AGENT_API_NAME}.
    - Set {DATETIME} to the current timestamp in milliseconds.
    - $Context.currentRecordId is set to {LEAD_RECORD_IDS}
    - $Context.ContactId is set to same Lead Record ID
- This ensures the agent generates the Negative Response email using the specific {LEAD_RECORD_IDS} records. 
- Save the generated agent test specification in the {OUTPUT_FOLDER} folder as a YAML file named {OUTPUT_FILE_OPT_OUT_TEST_SPECS}

### Response Format
 - Save the test results in the {OUTPUT_FOLDER} folder as a Markdown file named: {OUTPUT_FILE_OPT_OUT_TEST_RESULTS}.
 - Ensure each row in the table corresponds to the test results for a Lead record. 
 - Query the updated Lead records to retrieve their Status and Email Opt Out field values.	
 - Detailed Results Section: for each Lead record do the following:
 **Row Count**. **Lead Name** - **Title**

 | Field | Value |
 |-------|-------|
 | **Lead Name** | Lead Name |
 | **Title** | Title |
 | **Expected Status ** | "Unqualified" |
 | **Actual Status ** | Lead Status |
 | **Expected Opt Out ** | TRUE |
 | **Actual Opt Out ** | Lead Email Opt Out |
 | **Test Result** | Perform assertions to validate that both the Expected vs. Actual Lead Status and the Expected vs. Actual Email Opt Out values match. |