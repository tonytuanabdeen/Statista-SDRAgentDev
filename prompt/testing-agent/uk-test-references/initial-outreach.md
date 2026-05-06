### Instructions
 - Execute agent test according to the configuration defined in {INPUT_INITIAL_OUTREACH_TEST} 
 - During execution, for each Lead record created, dynamically pass the following input & context variables:
    - {AGENT_API_NAME}.
    - Set {DATETIME} to the current timestamp in milliseconds.
    - $Context.currentRecordId is set to {LEAD_RECORD_IDS}
 - This ensures that the agent generates the outreach email using the specific Lead record created from the dataset. 
 - Save the generated agent test specification in the {OUTPUT_FOLDER} folder as a YAML file named {OUTPUT_FILE_TEST_SPECS}

### Response Format
 - Save the test results in the {OUTPUT_FOLDER} folder as a Markdown file named: {OUTPUT_FILE_TEST_RESULTS}.
 - Ensure each row in the table corresponds to the test results for a Lead record generated from the CSV file.
 - Summary Section: The output should be presented in a table format containing the following columns:
  | Row Count | Lead Name | Title | Detected Persona | Expected Persona | Correct | 
 - Detailed Results Section: for each Lead record do the following:
 **Row Count**. **Lead Name** - **Title**

 | Field | Value |
 |-------|-------|
 | **Lead Name** | Lead Name |
 | **Title** | Title |
 | **Detected Persona** | Detected Persona |
 | **Email Subject** | Email Subject |
 | **Angle Used** | angle_used |
 | **Personalization Tier** | personalization_tier |
 | **rationale** | rationale |

 **Email Body:** 
 ```
 Email Body
 ```

### eval Initial Outreach
 - Query Salesforce Lead records in the default target org using the Email field for each row in the CSV. 
 - For every matching record, retrieve the Lead.Status field and verify that the value equals "Outreach". 
 - Perform an assertion to validate that the status matches the expected value.