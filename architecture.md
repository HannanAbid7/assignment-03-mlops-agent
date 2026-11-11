# Architecture

## System overview

```
User / Engineer (natural language)
        |
        v
FastAPI /chat endpoint (agent/main.py)
        |
        v
Orchestrator (agent/orchestrator.py)
  - sends system prompt + 21 tool schemas + conversation to an LLM
    (Groq, OpenAI-compatible API, model openai/gpt-oss-120b)
  - LLM decides which tool(s) to call
  - orchestrator executes the real tool function
  - result (status/data/error) is fed back to the LLM
  - loop continues until the LLM produces a final answer
    (capped at 16 iterations; retries on 429 with real backoff)
        |
   -----+-----+-----+-----
   |    |     |     |
   v    v     v     v
  DVC  MLflow Airflow Kubernetes
```

Tool-calling framework: implemented directly against the OpenAI-compatible
chat-completions API (no agent framework such as LangChain) so that every
tool call is explicit, inspectable, and logged.

## Why Groq / OpenAI-compatible API

A free, fast-inference endpoint with an OpenAI-compatible schema was used so
the orchestrator could rely on the standard `tools=[...]` function-calling
contract. This decision has a real tradeoff documented in Limitations below:
free-tier rate limits (8,000 TPM, 200,000 TPD) were hit during testing.

## Tool definitions and permissions

Every tool returns `{"status": "ok"|"error", "data": ..., "error": ...}`.
Tool JSON schemas are generated automatically from each function's Python
signature via `inspect.signature` (agent/orchestrator.py `_schema`), so
required/optional parameters and types are always consistent with the real
implementation.

| Module | Tool | Permission / safety guard |
|---|---|---|
| DVC | `list_tracked_datasets` | read-only |
| DVC | `get_current_version` | read-only |
| DVC | `compare_versions` | read-only |
| DVC | `has_data_changed` | read-only |
| DVC | `get_reproduction_instructions` | read-only, no subprocess call |
| DVC (internal) | `_run_dvc` | subprocess calls restricted to an allow-list: `status`, `list`, `diff`, `checkout` only — no destructive DVC commands reachable |
| MLflow | `list_experiments` | read-only |
| MLflow | `list_runs` | read-only |
| MLflow | `get_run_details` | read-only |
| MLflow | `get_best_run` | read-only; explicitly returns `production_ready: false` and a caveat note so the agent cannot treat "highest metric" as "safe to deploy" |
| MLflow | `compare_runs` | read-only |
| MLflow | `get_model_versions` | read-only |
| Airflow | `list_dags` | read-only; filtered to this project's own DAGs (excludes Airflow's ~115 bundled example DAGs) |
| Airflow | `get_dag_run_status` | read-only |
| Airflow | `trigger_dag` | **state-changing** — restricted to an allow-list (`training_pipeline` only); any other `dag_id` raises `PermissionError` |
| Airflow | `get_failed_tasks` | read-only |
| Airflow | `get_task_logs` | read-only |
| Kubernetes | `list_pods_and_deployments` | read-only; restricted to `mlops-agent` namespace |
| Kubernetes | `get_pod_status_and_logs` | read-only; namespace-restricted |
| Kubernetes | `inspect_services` | read-only; namespace-restricted |
| Kubernetes | `get_unhealthy_pods` | read-only; namespace-restricted |
| Kubernetes | `get_deployed_version` | read-only; namespace-restricted |
| Kubernetes | `restart_deployment` | **state-changing** — requires explicit `confirm=True` *and* the approved namespace; refuses both silently otherwise (raises `PermissionError`) |

## Safety behaviors (system prompt + orchestrator)

1. The system prompt instructs the LLM to only state facts that came from a
   tool result, and to say so explicitly when a tool errors or a service is
   unavailable, rather than guessing.
2. Retraining and any cluster-state change are never auto-triggered; the
   system prompt instructs the model to only recommend such actions, and the
   only state-changing tools (`trigger_dag`, `restart_deployment`) require an
   allow-listed id / explicit confirmation respectively.
3. Tool results are truncated to 1,500 characters before being sent back to
   the LLM, to control token usage against rate limits (see Limitations).
4. Every tool call is logged with a request id, tool name, status, and
   duration (no secrets) via Python's `logging` module.
5. Malformed tool-call arguments from the LLM are caught and reported as a
   structured tool error rather than crashing the request.

## Data flow example: the mandatory integration scenario

"Find the best recent model, identify the dataset version used to train it,
check the deployment status, and explain whether retraining is necessary."

1. `get_best_run` → MLflow returns the best run by F1, tagged with the git
   commit and DVC data hash that produced it.
2. `get_current_version` → DVC/git are queried for the *current* dataset
   hash.
3. The orchestrator (via the LLM) compares the two hashes to detect drift.
4. `list_pods_and_deployments` / `get_deployed_version` → Kubernetes is
   queried for the live deployment's image version.
5. `get_model_versions` → MLflow registry is checked (empty in our case).
6. The LLM synthesizes a "Known facts / Uncertainties / Recommendations"
   answer, recommending retraining only because real data drift was
   detected — never auto-triggering it.

Full transcript is in the technical report.

## Known limitations and proposed improvements

1. **Third-party API rate limits.** The free Groq tier enforces an 8,000
   token/minute and 200,000 token/day cap. Long multi-tool conversations
   (especially ones that pull Airflow task logs) can exceed this, causing
   either slow responses (while the orchestrator backs off and retries) or,
   once the *daily* cap is hit, a hard failure that cannot be retried around.
   This was observed directly during testing (see failure injection 2).
   **Improvement:** move to a paid tier / self-hosted model, or add a token
   budget tracker that proactively stops exploring once close to the limit.
2. **Tool-result truncation can hide information.** Capping tool output at
   1,500 characters (added to control token usage) can cut off relevant
   content in large responses (e.g. `list_dags` before an explicit project
   filter was added, or long pod logs). **Improvement:** summarize large
   payloads server-side instead of blind truncation.
3. **`evaluate_and_log_mlflow` evaluates the best historical run, not
   necessarily the run just produced**, since `get_best_run`-style ordering
   is used in the DAG without filtering to the current DAG run. This means
   the quality gate can pass even if the *current* training run performed
   worse than a historical one. **Improvement:** tag each MLflow run with
   its Airflow `run_id` and filter on that in the quality gate.
4. **No formal model registry workflow.** Models are logged to MLflow runs
   but never registered/promoted; `get_model_versions` will return an empty
   list until a human (or a future automation step) explicitly registers a
   model. This is intentional per the assignment's requirement that
   retraining/promotion never happen automatically, but it does mean the
   agent cannot yet answer "what's in production" from the registry alone.
5. **Single-node demo setup.** Airflow runs via `airflow standalone` (not a
   multi-worker deployment) and Kubernetes runs on a local `kind` cluster;
   this is appropriate for a course assignment but not representative of a
   production topology.
