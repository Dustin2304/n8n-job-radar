# n8n Workflow - Job Radar

This folder contains the n8n workflow that consumes the Job Radar API and sends a weekly HTML email report. It is the downstream half of the end-to-end flow: the FastAPI service produces scored jobs, and n8n re-ranks them with a local LLM, filters the shortlist, and emails the result.

## Flow Overview
```text
Manual Trigger
   -> Trigger Fresh Scrape   (HTTP GET  to :8001/jobs)
   -> Fetch Cached Jobs      (HTTP GET  to :8001/jobs/cached)
   -> Parse API Response     (flatten jobs array)
   -> Split in Batches       (10 jobs per batch)
        -> Prepare LLM Prompt
        -> Basic LLM Chain   (Ollama: qwen2.5:3B)
        -> Filter Relevant Jobs   (parse JSON array, keep score >= 50)
        -> loop back to Split in Batches
   -> Aggregate Batches
   -> Build HTML Report
   -> Send Email Report
```

## Nodes
| Node | Type | Purpose |
| --- | --- | --- |
| Manual Trigger | manualTrigger | Starts the workflow manually |
| Trigger Fresh Scrape | httpRequest | Calls `GET /jobs` to refresh the cache |
| Fetch Cached Jobs | httpRequest | Reads the latest cached results from `GET /jobs/cached` |
| Parse API Response | code | Maps `response.jobs[]` to n8n items |
| Split in Batches | splitInBatches | Sends 10 jobs at a time to the LLM |
| Prepare LLM Prompt | code | Builds the scoring prompt with profile data |
| Basic LLM Chain | chainLlm | Runs the prompt through the connected Ollama model |
| Ollama Model | lmOllama | Local `qwen2.5:3B` model |
| Filter Relevant Jobs | code | Parses the LLM JSON array and keeps `score >= 50` |
| Aggregate Batches | aggregate | Collects all filtered jobs into one array |
| Build HTML Report | code | Renders the grouped HTML email report |
| Send Email Report | gmail | Sends the HTML report via Gmail OAuth2 |

## Setup
1. Install and run n8n locally.
   - npm: `npm install -g n8n`
   - or Docker: `docker run --name n8n -p 5678:5678 -v ~/.n8n:/home/node/.n8n docker.n8n.io/n8nio/n8n`
2. Import `workflow.json` via *Workflows -> Import from File*.
3. Configure credentials in n8n:
   - **Ollama account**: connect to your local Ollama instance and make sure `qwen2.5:3b` is available.
   - **Gmail account**: create or bind a Gmail OAuth2 credential for the sender mailbox.
4. Set `REPORT_EMAIL` in your n8n environment, or replace the fallback value in the *Send Email Report* node.
5. Start the FastAPI service on `http://127.0.0.1:8001`.

## Customizing the Prompt
The scoring rubric lives inside the *Prepare LLM Prompt* node as an inline JavaScript template. Update the profile section, target roles, region, and exclusion rules to match your own background before using the workflow.

## Notes on Sanitization
The committed `workflow.json` has been scrubbed for portfolio use:
- `pinData`, `versionId`, top-level workflow `id`, `meta.instanceId`, and `webhookId` have been removed.
- Credential IDs have been cleared so credentials can be rebound after import.
- The report recipient is templated via `REPORT_EMAIL` with a placeholder fallback.
- Node names were translated to English for readability.
- Internal node IDs were retained to keep the imported workflow stable.
