# LNA Nova 2.0: Executive Talk Track

**Presenter Notes — Improvements to Scalability**

---

## Slide 1 — Title

> "Thank you for your time today Anjali & the team."

> "I'd like to walk you through a proposed architectural improvement to LNA Nova — which I call the LNA2.0." 

> "This is a continuation of the presenttaion we had around Agent scaling playbook. Which we talked about the previous speedboard, fast-follow, then scalling by Profit-center and scale by Lanugage/Country etc."

> "Today, once again the focus is scalability: how we take the working V1 agent and re-engineer it so it can serve multiple markets, multiple languages, and scale predictably — without increasing maintenance burden."

---

## Slide 2 — Executive Summary & The Ask

> "Quick context on where we are. Nova currently has four topics deployed in production. We shipped it fast — deliberately so — and it's working. But only one of those topics, Initial Outreach, follows the Prompt Builder pattern, orchestrated by Flows.

> The other three — Follow-up Outreach, Meeting Response, and Manage Opt-Out — still follows the out-of-the-box lead nurturing approach using instruction-based logic.

> Why does that matter? Five reasons:

> First — **locale-aware spelling.** Currently, Initial Outreach emails today are hardcoded to UK-English spelling. The LLM won't reliably apply spelling rules on its own when we consider the USA Market with US-English spelling.

> Second — **no spelling directive** The Follow-up Outreach, Meeting Response & Manage Opt-Out topic instructions contain no spelling directive at all. The model just defaults to whatever it prefers.

> Third — **Reduced Determinism.** The planner has to recall exact picklist values from instructions. If it predicts 'Not Interested' instead of 'Customer Not Interested,' downstream automations break silently.

> Fourth — **Higher maintenance Cost.** Changing one word of tone guidance or topic instructions means a full metadata redeployment. No version control, or no prompt iterations.

> Fifth — **scalability.** Adding a new locale or language today means rewriting topic instructions from scratch.

> **The ask is straightforward:** approve on the scaled design approach of the remaining 3 topics into the Prompt Builder framework, incorporating locale-aware spelling and establishing the pattern for future expansion."

---

## Slide 3 — Topic-by-Topic Review

> "Let me show you the current state side-by-side.

> On the left — Initial Outreach. This is our reference pattern. It has just two instructions: purpose and guardrails. It calls one Flow, which calls two Prompt Templates. Clean separation of concerns.

> Now compare that to Follow-up Outreach — six instructions covering role-aware reframing, output format, tone rules, guardrails. All of that logic lives in the planner's context window.

> Meeting Response is even more complex — seven instructions. It's asking the planner to read the reply, format meeting links, enforce tone, and update records, all from instruction text.

> Manage Opt-Out — six instructions including exact field values the planner must produce.

> The pattern is clear: Initial Outreach works *because* the topic says what to do, and the Flow and templates handle *how*. The other 3 try to do everything in instructions, which is brittle and non-deterministic."

> But, This decision was deliberately made to ensure the V1 Speedboat deployment was delivered on-time & within budget.

---

## Slide 4 — Recommended Target Architecture

> "Here's the target pattern. It's simple and it's the same for all 4 topics.

> **Topic** — stays minimal. Two instructions only: scope and guardrails. The planner decides *what* to do and *when*, but never *how*.

> **Flow** — this is where determinism lives. It gets the Lead record including the Country field, resolves the locale — US country maps to US spelling, everything else defaults to UK — calls the Prompt Template with that locale as a parameter, updates records, and returns the email. Fully deterministic. No guess-work.

> **Prompt Template** — this is where generation happens. Full personalisation logic, dynamic spelling-locale input. No hardcoded spelling directives anywhere in the system. The LLM decides *how* to Generate, but within the constraints we pass it.

> The key insight: we're pushing & moving away the "decision-making", *out* of the planner and *into* the right layer. Routing decisions stay with the planner. Data operations go to Flows. Language generation goes to templates. Each layer does what it's best at."

---

## Slide 5 — Target Architecture Diagram

> "Here's the full picture end-to-end.

> At the top, the Sales Cadence Orchestrator triggers based on stage — Intro, Nudge, or Reply. That hits the appropriate planner, which selects the right topic.

> Every topic follows the identical pattern: two instructions, one Flow action. Each Flow calls its own Prompt Template. 
~~and we're using Gemini 2.5 Flash for generation across the board, with GPT-4o Mini retained for persona detection where we need the speed.~~

> What's new here is the 3 Flows and 3 Prompt Templates on the right — Follow-Up Nudge, Meeting Response, and Opt-Out Response. These are the net-new deliverables.

> The beauty of this design is that every topic is now structurally identical. If you understand one, you understand all four. That's what scalability looks like."

> **Note**: Gemini 2.5 Flash stands out with a massive 1-million token context window, native multimodal capabilities (video, audio, text, images), and higher reasoning capabilities. GPT-4o Mini is generally more cost-effective (significantly cheaper for input tokens)

---

## Slide 6 — What Changes

> "Let me quantify the shift.

> Topic instructions go from **21 across the agent** — roughly 8,000 words of XML — **down to 8.** About 800 words total. That's a 90% reduction in planner cognitive load.

> Prompt Builder templates go from 2 to 5 — we're adding Follow-Up Nudge, Meeting Response, and Opt-Out.

> Orchestration Flows go from 1 to 4 — same additions.

> Record update logic moves from 'reduced determinism' — where the planner guesses field values — to 100% in Flows. Fully deterministic. No more picklist prediction errors.

> And spelling locales go from 1 hardcoded UK to 2 dynamic — UK and US — resolved per Lead data. This same mechanism scales to multi-language later without architectural changes.

> For each topic I've listed the specific scope. 
- Follow-up Outreach: migrate 6 instructions into 1 Prompt Template plus a Flow. 
- Meeting Response: 7 instructions into 1 PT plus Flow. 
- Manage Opt-Out: 6 instructions into 1 PT plus Flow with classification branching."

---

## Slide 7 — Return on Investment & Scale Readiness

> "What do we get immediately?

> **US market readiness** — US leads get properly-spelled outreach without manual editing. This unblocks the US expansion.

> **Increased Determinism** — zero picklist value prediction errors. The Flow sets exact values; the planner never touches them.

> **Iteration speed** — prompt templates deploy independently from the agent. Agent can iterate on tone and messaging without a full agent redeployment.

> **Maintenance** — every topic follows the same Flow-plus-Prompt-Template structure.

> One trade-off to flag: additional Prompt Template invocations will increase Flex Credit consumption.

> <br/><br/>
> Now — future scale. This is where the investment pays off:

> **New industry vertical?** Add one ICP knowledge article and one Flow branch. Done. (as we did with UK - Telco & IT)

> **New locale or language?** It's a parameter change in the Flow. The architecture already supports it with the Prompt Template pattern.

> **New agent** Clone the pattern, clone the instructions.

> **Control Model Selection** Change primary Model in PT metadata based on needs. This is not possible with Insutruction-based approach.

>**Important**: On the right you can see the maturity jump. V1 was deliberately hybrid — we shipped fast and within budget - with speedboat. Nova 2.0 is streamlined: deterministic, locale-aware, and every topic follows the same pattern."

> <br/><br/>
> And that's all Folks. this is what we have for today!
> Thank you!