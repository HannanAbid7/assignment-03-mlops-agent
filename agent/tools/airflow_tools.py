import requests, os
BASE = "http://localhost:8080/api/v2"
AUTH = ("admin", os.environ.get("AIRFLOW_ADMIN_PASSWORD", "admin"))
ALLOWED_DAGS = {"training_pipeline"}

def list_dags():
    r = requests.get(f"{BASE}/dags", auth=AUTH, timeout=10)
    r.raise_for_status()
    return r.json().get("dags", [])

def get_dag_run_status(dag_id: str = "training_pipeline", run_id: str = None):
    url = f"{BASE}/dags/{dag_id}/dagRuns/{run_id}" if run_id else f"{BASE}/dags/{dag_id}/dagRuns?order_by=-start_date&limit=1"
    r = requests.get(url, auth=AUTH, timeout=10)
    r.raise_for_status()
    d = r.json()
    return d.get("dag_runs", [d])[0] if "dag_runs" in d else d

def trigger_dag(dag_id: str = "training_pipeline"):
    if dag_id not in ALLOWED_DAGS:
        raise PermissionError(f"DAG '{dag_id}' not approved")
    r = requests.post(f"{BASE}/dags/{dag_id}/dagRuns", auth=AUTH, json={}, timeout=10)
    r.raise_for_status()
    return r.json()

def get_failed_tasks(dag_id: str, run_id: str):
    r = requests.get(f"{BASE}/dags/{dag_id}/dagRuns/{run_id}/taskInstances", auth=AUTH, timeout=10)
    r.raise_for_status()
    return [t for t in r.json().get("task_instances", []) if t.get("state") == "failed"]

def get_task_logs(dag_id: str, run_id: str, task_id: str, try_number: int = 1):
    r = requests.get(f"{BASE}/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/logs/{try_number}", auth=AUTH, timeout=10)
    r.raise_for_status()
    return r.text