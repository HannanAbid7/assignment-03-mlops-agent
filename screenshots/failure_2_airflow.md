# Failure Injection 2: Airflow quality gate

## Injection
Raised `QUALITY_THRESHOLD` in `dags/training_pipeline.py` from `0.6` to `1.5`
(a value no model can reach), then triggered the DAG.

## Resulting task states
```
validate_dataset          -> success
preprocess_data           -> success
train_model               -> success
evaluate_and_log_mlflow   -> success
quality_gate              -> failed
```

## Question asked to agent
"The last training pipeline run seems to have failed, what happened and why?"

## Agent's diagnosis
The agent correctly chained `list_dags` -> `get_dag_run_status` ->
`get_failed_tasks` -> `get_task_logs`, and correctly identified `quality_gate`
as the failed task, fetching its logs as evidence. The final natural-language
summary was cut off because the project's free-tier Groq API key hit its
daily token quota (200,000 TPD) partway through this test. The tool-calling
and evidence-gathering behavior itself completed correctly and is visible in
`uvicorn.log` tool-call entries; the LLM's final text synthesis is the only
part that did not complete, which is a third-party API quota limitation, not
an agent logic bug. This is documented as a known limitation in the report.

## Root cause
`QUALITY_THRESHOLD` set above any achievable F1 score, so the model-quality
gate correctly blocked promotion of an otherwise-successfully-trained model.

## Resolution
```
QUALITY_THRESHOLD reverted to 0.6 in dags/training_pipeline.py
```
