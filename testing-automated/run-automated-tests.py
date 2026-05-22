#!/usr/bin/env python3
"""
Author: Tuan Abdeen, Salesforce
Date: 11/Aug/2026
Description: LNA Nova — automated test runner.

STEP 1 — Create test Leads in the default target org.
  * Read leads from input-data/manufacturing_test_leads.json
  * Create one Salesforce Lead per entry via `sf data create record`
  * Capture the 15-character Record Id and write it back to the same JSON
    file under a new `salesforce_id` field on each entry.

Usage:
    python3 run-automated-tests.py [--org <alias>] [--skip-leads] [--step N]

    --org          Salesforce org alias or username (default: uses default org)
    --skip-leads   Skip Step 1 (lead creation). Use the existing salesforce_id values in the leads JSON file.
    --step N       Run only step N (1=Leads creation, 2=Initial Outreach, 3=Nudge / Meeting Response / Opt-Out).
                   If omitted, all steps run.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

import yaml  # pip install pyyaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Populated in main() — single timestamp shared across all suites in one run.
RUN_TIMESTAMP_DISPLAY = ""  # yyyymmddThh:mm:ss — goes into the spec's display `name`
RUN_TIMESTAMP_API     = ""  # yyyymmddThhmmss  — goes into the --api-name (no colons allowed)

TEST_AUTO_DIR = Path(__file__).parent
LEADS_FILE = TEST_AUTO_DIR / "input-data" / "manufacturing_test_leads.json"

TEST_SUITES_DIR           = TEST_AUTO_DIR / "test-suites"

OUTPUT_RESULTS_DIR        = TEST_AUTO_DIR / "output-results"

INITIAL_OUTREACH_TEMPLATE = TEST_AUTO_DIR / "input-test-suites" / "initial-outreach-test-template.yaml"
NUDGE_TEMPLATE            = TEST_AUTO_DIR / "input-test-suites" / "nudges-test-template.yaml"
MEETING_TEMPLATE          = TEST_AUTO_DIR / "input-test-suites" / "meeting-response-test-template.yaml"
OPT_OUT_TEMPLATE          = TEST_AUTO_DIR / "input-test-suites" / "opt-out-test-template.yaml"

TEST_RESULTS_FILE_NAME    = "initial-outreach-test-results"

# Internal test suite API names (must be <=40 chars, alphanumeric + underscore).
# A timestamp is appended at runtime (see build_suite_names).
SUITE_INITIAL  = "LNA_Nova_Initial_Outreach"
SUITE_NUDGE    = "LNA_Nova_Nudge"
SUITE_MEETING  = "LNA_Nova_Meeting_Response"
SUITE_OPT_OUT  = "LNA_Nova_Opt_Out"

# Target agent for `subjectName` in the generated test spec.
AGENT_API_NAME = "Agentforce_Sales_Development_Rep_2"

# Fields that are local metadata only — not real Lead fields in Salesforce.
NON_SF_FIELDS = {"id", "persona_expected", "salesforce_id","initial_outreach_subject","initial_outreach_body"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def run(cmd: list[str]) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"\n[ERROR] Command failed: {' '.join(cmd)}")
        print(result.stderr or result.stdout)
        sys.exit(1)
    return result

def parse_sf_json(result: subprocess.CompletedProcess) -> dict:
    raw = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", result.stdout)
    return json.loads(raw)


def split_subject_and_body(outcome: str) -> tuple[str, str]:
    """Split the agent's drafted email outcome into (subject, body).

    Looks for a `Subject:` line (case-insensitive). Everything after that line
    is treated as the body; anything before is discarded. If no Subject line is
    found, returns ("", outcome).
    """
    if not outcome:
        return "", ""
    outcome = outcome.replace("**Subject:**", "Subject:")  # Handle bolded "Subject:" from markdown templates.
    match = re.search(r"(?im)^\s*subject\s*:\s*(.+?)\s*$", outcome)
    if not match:
        return "", outcome.strip()
    subject = match.group(1).strip()
    body = outcome[match.end():].lstrip("\r\n").rstrip()
    return subject, body

# ---------------------------------------------------------------------------
# Step 1 — Create Test Lead records
# ---------------------------------------------------------------------------
def build_values_arg(lead: dict, timestamp: str) -> str:
    """Build the `Field='Value' Field2='Value2'` string for `sf data create record --values`.

    LastName is suffixed with `_<timestamp>` so each test run produces uniquely
    identifiable Lead records in the org.
    """
    parts = []
    for k, v in lead.items():
        if k in NON_SF_FIELDS or v is None:
            continue
        value = f"{v}_{timestamp}" if k == "LastName" else v
        # Escape single quotes in the value.
        safe = str(value).replace("'", "\\'")
        parts.append(f"{k}='{safe}'")
    return " ".join(parts)


def create_lead(lead: dict, org: str | None, timestamp: str) -> str:
    cmd = [
        "sf", "data", "create", "record",
        "--sobject", "Lead",
        "--values", build_values_arg(lead, timestamp),
        "--json",
    ]
    if org:
        cmd += ["--target-org", org]

    result = run(cmd)
    data = parse_sf_json(result)
    full_id = data["result"]["id"]
    return full_id[:15]

# ---------------------------------------------------------------------------
# Step 2 — Generic helpers: render template, deploy, run
# ---------------------------------------------------------------------------
def generate_suite_from_template(template_path: Path, leads_subset: list[dict], suite_base: str) -> Path:
    """
    Render a test-suite YAML from a template by repeating the template's single
    `testCases:` block once per Lead in `leads_subset`.

    Substitutions:
      * {{DATETIME}}                    — RUN_TIMESTAMP_API (header only)
      * {{AGENT_API_NAME}}              — AGENT_API_NAME (header only)
      * {{DYNAMIC_LEAD_RECORD_15_ID}}   — each Lead's 15-char Salesforce Id
      * {{PREVIOUS_EMAIL_BODY}}         — initial-outreach email body for that
                                          Lead (if `prev_email_body_by_lead_id`
                                          is provided)
    """
    template_text = template_path.read_text()
    header, _, case_block = template_text.partition("testCases:")
    if not case_block:
        print(f"[ERROR] Template missing 'testCases:' section: {template_path}")
        sys.exit(1)

    case_template = case_block.strip("\n")    
    rendered_cases: list[str] = []
    for lead in leads_subset:
        sf_id = lead.get("salesforce_id")
        if not sf_id:
            print(f"  [WARN] Skipping {lead.get('id')} — no salesforce_id present")
            continue
        prev_email_subject = lead.get("initial_outreach_subject")
        prev_email_body = lead.get("initial_outreach_body")
        if not prev_email_body:
            print(f"  [WARN] — no Previous Initial Outreach Email content present")
            continue

        case = case_template.replace("{{DYNAMIC_LEAD_RECORD_15_ID}}", sf_id)
        if "{{PREVIOUS_EMAIL_BODY}}" in case:            
            # YAML-safe: collapse newlines to spaces and escape double quotes.            
            safe_body = prev_email_body.replace('"', '\\"').replace("\r", " ").replace("\n", " ").strip()
            email_content = f"{prev_email_subject} {safe_body}"
            case = case.replace("{{PREVIOUS_EMAIL_BODY}}", email_content)
        
        if "{{PREVIOUS_EMAIL_SUBJECT}}" in case:  
            case = case.replace("{{PREVIOUS_EMAIL_SUBJECT}}", prev_email_subject)

        rendered_cases.append(case)

    if not rendered_cases:
        print(f"[ERROR] No leads with a salesforce_id for suite {suite_base} — cannot build test cases.")
        sys.exit(1)

    rendered = (
        header.replace("{{DATETIME}}", RUN_TIMESTAMP_DISPLAY).replace("{{AGENT_API_NAME}}", AGENT_API_NAME)
        + "testCases:\n"
        + "\n".join(rendered_cases)
        + "\n"
    )    

    run_suites_dir = TEST_SUITES_DIR / RUN_TIMESTAMP_DISPLAY
    print(f"  run_suites_dir: {run_suites_dir}")
    run_suites_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_suites_dir / f"{AGENT_API_NAME}_{suite_base}_{RUN_TIMESTAMP_API}.yaml"
    out_path.write_text(rendered)
    print(f"  Generated test suite: {out_path}")
    return out_path


def deploy_and_run_suite(spec_path: Path, suite_name: str, org: str | None) -> dict:
    """Deploy the suite via `sf agent test create`, run it, and return parsed results."""
    print(f"\n  Deploying suite '{suite_name}'...")
    run([
        "sf", "agent", "test", "create",
        "--spec", str(spec_path),
        "--api-name", suite_name,
        "--force-overwrite",
        "--json",
        *(["--target-org", org] if org else []),
    ])

    print(f"  Running suite '{suite_name}' (waiting up to 20 min)...")
    run_result = run([
        "sf", "agent", "test", "run",
        "--api-name", suite_name,
        "--wait", "20",
        "--result-format", "json",
        "--json",
        *(["--target-org", org] if org else []),
    ])
    run_data = parse_sf_json(run_result)
    job_id = run_data["result"]["runId"]

    print(f"  Fetching results for job {job_id}...")
    results_result = run([
        "sf", "agent", "test", "results",
        "--job-id", job_id,
        "--result-format", "json",
        "--json",
        *(["--target-org", org] if org else []),
    ])
    return parse_sf_json(results_result)

# ---------------------------------------------------------------------------
# Step 2.2 — Result parsing & Persist generated email bodies as a markdown artifact
# ---------------------------------------------------------------------------
def extract_email_bodies(results: dict, leads: list[dict], spec_path: Path, suite_name: str) -> list[dict]:
    """
    Match each test case back to its source Lead via $Context.currentRecordId
    and capture the agent's generated outcome text (the drafted email).

    contextVariables are not echoed back in the run results, so we read them
    from the originating spec YAML at `spec_path` and align by test-case index.
    """
    id_to_lead = {lead["salesforce_id"]: lead for lead in leads if lead.get("salesforce_id")}    
    
    test_cases = results.get("result", {}).get("testCases", [])

    spec = yaml.safe_load(spec_path.read_text()) or {}
    spec_test_cases = spec.get("testCases", []) or []  

    passed = failed = 0
    extracted: list[dict] = []
    for i, tc in enumerate(test_cases):

        utterance = tc.get("inputs", {}).get("utterance", "")
        outcome = tc.get("generatedData", {}).get("outcome", "")
        actual_topic = tc.get("generatedData", {}).get("topic", "")
        start_time = tc.get("startTime", {})
        end_time = tc.get("endTime", {})
        overall_test_status = tc.get("status", {})
        
        test_results = {r["name"]: r["result"] for r in tc.get("testResults", [])}
        topic_assertion  = test_results.get("topic_assertion",  "N/A")
        action_assertion = test_results.get("actions_assertion", "N/A")
        output_validation = test_results.get("output_validation", "N/A")
        status = "PASS" if output_validation == "PASS" else "FAIL"
        if status == "PASS":
            passed += 1
        else:
            failed += 1

        spec_tc = spec_test_cases[i] if i < len(spec_test_cases) else {}
        ctx_vars = {cv.get("name"): cv.get("value") for cv in spec_tc.get("contextVariables", []) or []}
        sf_id = ctx_vars.get("$Context.currentRecordId", "")
        lead = id_to_lead.get(sf_id, {})

        email_body_outcome = outcome.strip()

        # For Initial Outreach, persist the drafted subject/body back onto the
        # lead so downstream suites (e.g. Nudge) can reference them.
        if suite_name == "Initial Outreach" and lead:
            subject, body = split_subject_and_body(email_body_outcome)
            lead["initial_outreach_subject"] = "Subject: " + subject
            lead["initial_outreach_body"] = "Body: " + body
            LEADS_FILE.write_text(json.dumps(leads, indent=2) + "\n")

        extracted.append({
            "lead_local_id": lead.get("id", "(unmapped)"),
            "salesforce_id": sf_id,
            "first_name": lead.get("FirstName", ""),
            "last_name": lead.get("LastName", ""),
            "title": lead.get("Title", ""),
            "company": lead.get("Company", ""),
            "industry": lead.get("Industry", ""),
            "persona_expected": lead.get("persona_expected", ""),
            "email_body": email_body_outcome,

            "status": status,
            "utterance": utterance,
            "topic_assertion": topic_assertion,
            "action_assertion": action_assertion,
            "output_validation": output_validation,
            "actual_topic": actual_topic
        })

    if suite_name == "Initial Outreach":
        LEADS_FILE.write_text(json.dumps(leads, indent=2) + "\n")
        print(f"  Persisted initial_outreach_subject / initial_outreach_body to {LEADS_FILE.name}")

    print(f"  {suite_name}: {passed} passed, {failed} failed")
    return {"suite_name": suite_name, "passed": passed, "failed": failed, "extracted": extracted, "start_time": start_time, "end_time": end_time, "overall_test_status": overall_test_status}

def convertUtcToLocalTime(utc_time_str: str) -> str:
    """Convert a UTC time string (e.g., '2026-04-30T11:14:03Z') to local time string."""

    try:
        # Parse the UTC datetime
        utc_dt = datetime.strptime(utc_time_str, '%Y-%m-%dT%H:%M:%SZ')

        # Attach UTC timezone
        utc_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC"))

         # Convert to local timezone
        local_dt = utc_dt.astimezone(ZoneInfo("Asia/Dubai"))        

        return local_dt

    except ValueError:
        return utc_time_str  # Return original if parsing fails
    

def write_markdown_report(summaries: list[dict], filename: str, title: str, org: str | None) -> Path:
    run_output_res_dir = OUTPUT_RESULTS_DIR / RUN_TIMESTAMP_DISPLAY
    run_output_res_dir.mkdir(parents=True, exist_ok=True)            
    out_path = run_output_res_dir / filename

    lines: list[str] = []
    lines.append(f"# LNA Nova — {title} Test Results")    
    lines.append("")
    lines.append(f"- **Agent:** `{AGENT_API_NAME}`")
    lines.append(f"- **Run timestamp:** `{RUN_TIMESTAMP_DISPLAY}`")    
    lines.append(f"- **Org:** `{org or '(default org)'}`")  

    smr = summaries[0]
    startTime = smr.get("start_time", "")
    endTime = smr.get("end_time", "")    
    lines.append(f"- **Status:** `{smr['overall_test_status']}`")  
    lines.append(f"- **Start Time:** `{ convertUtcToLocalTime(startTime)}`")
    lines.append(f"- **End Time:** `{ convertUtcToLocalTime(endTime)}`")

    lines.append("")    
    lines.append("---")
    lines.append("")

    # Overall summary
    total_passed = sum(s["passed"] for s in summaries)
    total_failed = sum(s["failed"] for s in summaries)
    lines.append("## Summary")
    lines.append("")
    lines.append("| Suite | Passed | Failed |")
    lines.append("|---|---:|---:|")
    for s in summaries:
        lines.append(f"| {s['suite_name']} | {s['passed']} | {s['failed']} |")        
    lines.append(f"| **Total** | **{total_passed}** | **{total_failed}** |")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Detailed Results")

    for i, item in enumerate(s["extracted"], start=1):    
        full_name = f"{item['first_name']} {item['last_name']}".strip()
    
        lines.append(f"## {i}. {full_name} - {item['title'] or '(blank)'}")
        lines.append("")

        lines.append(f"- **Salesforce Id:** `{item['salesforce_id']}`")        
        lines.append(f"- **Company:** `{item['company'] or '(blank)'}`")
        lines.append(f"- **Industry:** `{item['industry'] or '(blank)'}`")
        lines.append(f"- **Expected persona:** `{item['persona_expected'] or '(none)'}`")
        lines.append("")
        lines.append(f"- **Utterance:** `{item['utterance']}`")
        lines.append(f"- **Topic assertion:** `{item['topic_assertion']}`")
        lines.append(f"- **Action assertion:** `{item['action_assertion']}`")
        lines.append(f"- **Output validation:** `{item['output_validation']}`")
        if item["actual_topic"]:
            lines.append(f"- **Actual topic:** `{item['actual_topic']}`")
        lines.append("")          
        lines.append("**Agent response:**")
        lines.append("")
        lines.append("```")

        email_body = item["email_body"] or "(no outcome captured)"
        email_body = email_body.replace("**Subject:**", "Subject:")

        lines.append(email_body)
        lines.append("```")
        lines.append("")

    out_path.write_text("\n".join(lines))
    print(f"  {title} report written to {out_path}")
    return out_path

def pickLeadsByLocalIds(local_ids: list[str], leads: list[dict]) -> list[dict]:    
    subset: list[dict] = []
    for lid in local_ids:        
        lead = next((lead for lead in leads if lead["id"] == lid), None)
    
        if not lead:
            print(f"  [WARN] {lid} not in leads file — skipping for this suite")
            continue
        subset.append(lead)
    return subset  


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="STEP 1 — Create test Leads and persist their Salesforce Ids.")
    parser.add_argument("--org", default=None, help="Salesforce org alias or username (default org if omitted)")
    parser.add_argument("--skip-leads", action="store_true", help="Skip Step 1 (lead creation). Use the existing salesforce_id values in the leads JSON file.")
    parser.add_argument("--step", type=int, choices=[1, 2, 3], default=None, help="Run only step N (1=Leads creation, 2=Initial Outreach, 3=Nudge / Meeting Response / Opt-Out). If omitted, all steps run.")
    args = parser.parse_args()

    run_step_1 = args.step is None or args.step == 1
    run_step_2 = args.step is None or args.step == 2
    run_step_3 = args.step is None or args.step == 3

    # Single timestamp shared across all suites created in this run.
    global RUN_TIMESTAMP_DISPLAY, RUN_TIMESTAMP_API
    now = datetime.now()
    RUN_TIMESTAMP_DISPLAY = now.strftime("%Y-%m-%dT%H:%M:%S")
    RUN_TIMESTAMP_API     = now.strftime("%Y%m%dT%H%M%S")
    print(f"Run timestamp Display: {RUN_TIMESTAMP_DISPLAY}")
    print(f"Run timestamp: {RUN_TIMESTAMP_API}")

    # Accumulates per-suite summaries so they can be written into one markdown report at the end
    summaries: list[dict] = []

    # ------------------------------------------------------------------
    # Load leads file (needed by all steps)
    # ------------------------------------------------------------------
    if not LEADS_FILE.exists():
        print(f"[ERROR] Leads file not found: {LEADS_FILE}")
        sys.exit(1)

    leads = json.loads(LEADS_FILE.read_text())
    timestamp = datetime.now().strftime(RUN_TIMESTAMP_API)
    print(f"Loaded {len(leads)} leads from {LEADS_FILE.name}")
    print(f"Target org: {args.org or '(default org)'}")
    print(f"LastName suffix: _{timestamp}\n")

    # ------------------------------------------------------------------
    # Step 1: Create leads (skipped when --skip-leads is set or --step != 1)
    # ------------------------------------------------------------------
    if run_step_1:
        if args.skip_leads:
            print("\n[--skip-leads] Skipping Step 1 (lead creation). Using existing salesforce_id values.")
            missing = [lead.get("id", "(no id)") for lead in leads if not lead.get("salesforce_id")]
            if missing:
                print(f"[ERROR] --skip-leads was set but the following leads have no salesforce_id: {missing}")
                print("       Run without --skip-leads first, or backfill the IDs in the JSON file.")
                sys.exit(1)
        else:
            print("\n=== Step 1: Create test Leads ===")
            for lead in leads:
                local_id = lead.get("id", "(no id)")
                stamped_lastname = f"{lead.get('LastName', '')}_{timestamp}"
                name = f"{lead.get('FirstName', '')} {stamped_lastname}".strip()
                print(f"  Creating {local_id}: {name} — {lead.get('Title', '')}")

                sf_id = create_lead(lead, args.org, timestamp)
                lead["salesforce_id"] = sf_id
                print(f"    -> {sf_id}")

                # Persist after every successful creation so a mid-run failure
                # doesn't lose Ids that were already created in the org.
                LEADS_FILE.write_text(json.dumps(leads, indent=2) + "\n")

            print(f"\nLeads created. Updated {LEADS_FILE}")
    else:
        print(f"\n[--step {args.step}] Skipping Step 1 (lead creation).")
        missing = [lead.get("id", "(no id)") for lead in leads if not lead.get("salesforce_id")]
        if missing:
            print(f"[ERROR] Step {args.step} requires existing salesforce_id values, but missing for: {missing}")
            print("       Run Step 1 first, or backfill the IDs in the JSON file.")
            sys.exit(1)

    # ------------------------------------------------------------------
    # Step 2.1: Initial Outreach — generate, deploy, run
    # ------------------------------------------------------------------
    if run_step_2:
        print("\n=== Step 2.1: Initial Outreach test suite ===")
        spec_path = generate_suite_from_template(INITIAL_OUTREACH_TEMPLATE, leads, SUITE_INITIAL)
        suite_api_name = f"{SUITE_INITIAL}_{RUN_TIMESTAMP_API}"
        results = deploy_and_run_suite(spec_path, suite_api_name, args.org)        

        # ------------------------------------------------------------------
        # Step 2.2: Extract drafted emails and write the markdown artifact
        # ------------------------------------------------------------------
        print("\n=== Step 2.2: Extract drafted emails ===")
        summaries: list[dict] = []
        summaries.append(extract_email_bodies(results, leads, spec_path, "Initial Outreach"))        

        test_results_output_name = f"{TEST_RESULTS_FILE_NAME}_{RUN_TIMESTAMP_API}.md"
        write_markdown_report(summaries, test_results_output_name, "Initial Outreach", args.org)
    else:
        print(f"\n[--step {args.step}] Skipping Step 2 (Initial Outreach).")

    # ------------------------------------------------------------------
    # Step 3: Nudge / Meeting Response / Opt-Out
    #   - Nudge          uses LEAD-001, LEAD-002
    #   - Meeting Resp.  uses LEAD-003, LEAD-004
    #   - Opt-Out        uses LEAD-005, LEAD-006
    # ------------------------------------------------------------------
    if run_step_3:
        print("\n=== Step 3: Nudge / Meeting Response / Opt-Out test suites ===")

        test_suite_base = [
            ("Nudge",            SUITE_NUDGE,    NUDGE_TEMPLATE,   ["LEAD-001", "LEAD-002"], f"nudge-test-results_{RUN_TIMESTAMP_API}.md"),
            ("Meeting Response", SUITE_MEETING,  MEETING_TEMPLATE, ["LEAD-003", "LEAD-004"], f"meeting-response-test-results_{RUN_TIMESTAMP_API}.md"),
            ("Opt-Out",          SUITE_OPT_OUT,  OPT_OUT_TEMPLATE, ["LEAD-005", "LEAD-006"], f"opt-out-test-results_{RUN_TIMESTAMP_API}.md"),
        ]

        # ------------------------------------------------------------------
        # Step 3.1: Nudge / Meeting Response / Opt-Out — generate, deploy, run
        # ------------------------------------------------------------------        
        for title, suite_base, template_path, _local_ids, _report_filename in test_suite_base:
            print(f"\n=== Step 3.1: {title} test suite ===")
            filteredLeads = pickLeadsByLocalIds(_local_ids, leads)            
            spec_path = generate_suite_from_template(template_path, filteredLeads, suite_base)            
            suite_api_name = f"{suite_base}_{RUN_TIMESTAMP_API}"                
            results = deploy_and_run_suite(spec_path, suite_api_name, args.org)       

            # ------------------------------------------------------------------
            # Step 3.2: Extract drafted emails and write the markdown artifact
            # ------------------------------------------------------------------            
            print("\n=== Step 3.2: Extract drafted emails ===")
            summaries: list[dict] = []
            summaries.append(extract_email_bodies(results, filteredLeads, spec_path, suite_base))            
            
            write_markdown_report(summaries, _report_filename, title, args.org)
                             
    else:
        print(f"\n[--step {args.step}] Skipping Step 3 (Nudge / Meeting Response / Opt-Out).")

    print("\nDone.")

if __name__ == "__main__":
    main()
