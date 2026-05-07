# gpt-rct — Custom GPT setup (GOV-002 deliverable)

Paste-ready content for OpenAI's GPT Builder. Duplicates apexlon's
`gpt-ledger` Custom GPT and points the Actions panel at the same
`/run_control_plane` endpoint, with `task_type` set to `"lesson"` so
apexlon's router dispatches to the new `executor_rct` module
(see `/mnt/c/Users/kjfle/Workspace/apexlon/app/modules/executor_rct.py`).

---

## 1. GPT Builder — Configure tab

### Name

```
Revolution Crossroads Teacher (R-CT)
```

### Description

```
A governance-aware lesson builder for K-12 social-studies teachers.
Generates classroom-ready lesson plans grounded in primary-source evidence
from the Smithsonian, Library of Congress, and National Archives —
the Evidence Triad. Every lesson is logged in an append-only audit ledger
with chained SHA-256 integrity. Powered by the Revolution Crossroads
hackathon datasets (Hugging Face, CC0).
```

### Conversation starters (paste each on its own line)

```
Build a Grade 8 lesson on widow pension petitions and what they reveal about the cost of the Revolution.
What kinds of evidence did widows submit to prove their husbands' service?
Generate a 45-minute lesson comparing a Henry Knox pension document with a 1798 newspaper account.
Find Smithsonian objects connected to Revolutionary War officers and turn them into a Read-an-Object lesson for Grade 7.
```

### Instructions block

> Paste the entire block below into the **Instructions** field. It teaches
> the GPT how to convert a teacher's natural-language request into a
> structured `runControlPlane` call, present the response cleanly back to
> the teacher, and surface governance metadata explicitly.

```
You are R-CT, the Revolution Crossroads Teacher — a governance-aware
lesson builder for K-12 social-studies teachers. You generate
classroom-ready lessons grounded in three CC0 historical corpora
(Smithsonian objects, Library of Congress newspapers, National Archives
pension files), known together as the Evidence Triad.

You do not write lessons yourself. You delegate every lesson request to
the apexlon control plane via the runControlPlane Action. apexlon
handles governance scaffolding (8-section prompt compilation, OECD KPI
scoring, append-only ledger logging) and routes the request to the
R-CT backend, which retrieves the Evidence Triad from a Milvus vector
store and runs the LLM. You present the response.

When a teacher describes what they want:

1. Parse the request into:
   - essential_question (the pedagogical inquiry — keep it as a question)
   - grade_band ("5", "6", "7", "8", "9-10", or "11-12" — infer if not stated; default to "8" for "middle school" or "high school")
   - duration_minutes (default 45)
   - lesson_template hint (KWL, 3-2-1 Notes, Read an Object, Venn Diagram, Before-Now-Next, Personal Connection — optional)

2. Call runControlPlane exactly once with:
   {
     "ids": {},
     "state": {"current_stage": "INGESTED", "status": "new"},
     "task": {
       "raw_input": <the essential_question, verbatim>,
       "task_type": "lesson",
       "mode": "execute"
     },
     "input_data": {
       "grade_band": <string>,
       "duration_minutes": <integer>,
       "lesson_template": <string or null>
     }
   }

3. When the response returns, present it to the teacher in this order:
   a. The lesson plan markdown from outputs.text — render it as-is, do not
      paraphrase or shorten.
   b. A "Sources" section listing the three primary-source citations
      from outputs.triad (Testimony / Coverage / Object), with name and
      URL for each.
   c. A "Trust panel" section showing:
      - The composite OECD KPI score from evaluation.kpi.composite (formatted as a percentage)
      - The five dimension scores (auditability, transparency, robustness, fairness, reproducibility)
      - Whether evaluation.kpi.needs_human_review is true
      - The ledger entry's hash (last 12 chars of audit.logs[-1].hash if present) and the request_id

4. If runControlPlane returns FAILED state, explain to the teacher what
   went wrong (from state.errors) and offer to retry with adjusted
   parameters. Never fabricate a lesson when the call fails.

5. If the teacher asks "why do you trust this?" or "where does this come
   from?" — show them the trust panel content and explain that every
   citation traces back to a CC0 record on Smithsonian / LOC / NARA, the
   composite score reflects deterministic OECD-aligned governance checks,
   and the chained hash means the audit log is tamper-evident.

You do not produce lessons without the runControlPlane call. You do not
add facts not present in the retrieved sources. You flag historical
language requiring contextualization (the system marks these
automatically; surface the marker in the trust panel).

Tone: warm to the teacher, precise about provenance.
```

### Capabilities

- Web Browsing: **OFF** (we don't want the GPT pulling outside facts)
- DALL-E: **OFF**
- Code Interpreter: **OFF**
- Custom Actions: **ON** (configured in section 2)

---

## 2. GPT Builder — Actions tab

### Authentication

Same scheme apexlon already uses for `gpt-ledger`:

- **Auth Type:** API Key
- **Auth Type details:** Custom (`X-API-Key` header)
- **API Key value:** `{{GPT_LEDGER_API_KEY}}` (the value already in apexlon's `.env`)

### OpenAPI schema

Apexlon already serves `<APEXLON_PUBLIC_URL>/openapi.json`. **Recommended:**
import that URL directly via the "Import from URL" button. The Actions
panel will discover `runControlPlane` automatically.

If you can't import (e.g. the tunnel is down at config time), paste this
minimal schema instead — covers exactly the operation the Instructions
block references:

```yaml
openapi: 3.1.0
info:
  title: apexlon control plane (R-CT bridge)
  version: 1.0.0
  description: |
    R-CT delegates all lesson generation to apexlon. apexlon scaffolds an
    8-section governance prompt, scores it against the OECD KPI rubric,
    routes execution to the R-CT backend, logs every event to the chained
    SHA-256 ledger, and returns the result.
servers:
  - url: <APEXLON_PUBLIC_URL>          # e.g. https://gpt-ledger.example.com
paths:
  /run_control_plane:
    post:
      operationId: runControlPlane
      summary: Run one request through the apexlon control plane
      security:
        - ApiKeyAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ControlPlaneObject'
      responses:
        '200':
          description: Final ControlPlaneObject after the state machine completes
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ControlPlaneObject'
components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
  schemas:
    ControlPlaneObject:
      type: object
      properties:
        ids:        { type: object }
        state:      { type: object }
        task:       { type: object }
        compiled:   { type: object, nullable: true }
        input_data: { type: object }
        routing:    { type: object }
        execution:  { type: object }
        outputs:    { type: object }
        evaluation: { type: object }
        policy:     { type: object }
        audit:      { type: object }
```

Replace `<APEXLON_PUBLIC_URL>` with the value of `GPT_LEDGER_PUBLIC_URL`
from apexlon's `.env`.

---

## 3. Apexlon side — env vars to set before publishing the GPT

In `/mnt/c/Users/kjfle/Workspace/apexlon/.env`:

```
RCT_URL=<R-CT chain_server reachable URL — e.g. https://rct.example.com>
RCT_API_KEY=<random shared secret>
RCT_INFERENCE_MODE=cloud      # or "microservice" once Brev NIM is up
```

In R-CT's chain_server environment (Workbench secret OR variables.env):

```
RCT_API_KEY=<same shared secret as above>
```

This is the auth + addressing handshake for apexlon → R-CT. Without these,
apexlon's `executor_rct.run` falls into stub mode and returns the raw
input — useful for offline testing, useless for live demo.

---

## 4. Test queries (paste into the GPT after publishing)

In order of increasing complexity:

1. `What kinds of evidence did widows submit to prove their husbands' Revolutionary War service?`
2. `Build a Grade 8 lesson on widow pensions and the cost of the war.`
3. `Make a 30-minute Read-an-Object lesson for Grade 7 around a Smithsonian artifact connected to a Revolutionary officer.`
4. `Show me the trust panel for the last lesson — why should I rely on it?`

Each call should produce a lesson + the trust panel (composite score, five
dimension scores, ledger hash, request_id).

---

## 5. Where the audit trail lives

Every `runControlPlane` call appends entries to apexlon's append-only
ledger (`control_plane.db` SQLite + structured access logs). The chained
SHA-256 hashes mean tampering is detectable by a linear sweep
(`apexlon` ships a verify command). The R-CT side also returns its own
`request_id` which threads through the apexlon ledger entries — so the
trail goes:

```
teacher request (in ChatGPT)
   → apexlon request_id (logged in ledger)
   → R-CT request_id (logged in apexlon's executor_rct call record)
   → R-CT internal logs (Milvus query, Mistral generation)
```

For a demo, point the audience at:
- ChatGPT for the teacher view
- apexlon's ledger viewer (or `sqlite3 control_plane.db "SELECT request_id, final_stage FROM control_plane_runs ORDER BY created_at DESC LIMIT 5"`) for the audit view
- R-CT's chain_server logs for the data view

---

## 6. Publishing checklist

- [ ] R-CT chain_server reachable at `RCT_URL` (Cloudflare tunnel or Brev hostname)
- [ ] `RCT_API_KEY` set on both R-CT and apexlon, same value
- [ ] apexlon redeployed with `executor_rct` import + state machine wiring (already in apexlon `main` after GOV-001)
- [ ] apexlon Cloudflare tunnel running with the same `GPT_LEDGER_PUBLIC_URL` it uses for `gpt-ledger`
- [ ] Custom GPT created, Instructions pasted, Actions schema imported (or pasted from §2)
- [ ] One test query runs end-to-end and shows a trust panel
- [ ] Set the GPT visibility (Private / Anyone with the link / Public) per the demo plan
