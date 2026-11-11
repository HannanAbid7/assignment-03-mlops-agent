"""Airflow REST API tools, restricted to approved DAGs."""
import requests, os

BASE = "http://localhost:8080/api/v2"
AIRFLOW_USER = "admin"
AIRFLOW_PASSWORD = os.environ.get("AIRFLOW_ADMIN_PASSWORD", "admin")
ALLOWED_DAGS = {"training_pipeline"}

_token = None


def _get_token():
    global _token
    if _token is None:
        r = requests.post(
            "http://localhost:8080/auth/token",
            json={"username": AIRFLOW_USER, "password": AIRFLOW_PASSWORD},
            timeout=10,
        )
        r.raise_for_status()
        _token = r.json()["access_token"]
    return _token


def _headers():
    return {"Authorization": f"Bearer {_get_token()}"}


def _request(method, url, **kwargs):
    global _token
    r = requests.request(method, url, headers=_headers(), timeout=10, **kwargs)
    if r.status_code == 401:
        _token = None
        r = requests.request(method, url, headers=_headers(), timeout=10, **kwargs)
    r.raise_for_status()
    return r


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def list_dags():
    """List DAGs defined in this project (excludes Airflow's bundled example DAGs)."""
    dags, offset = [], 0
    while True:
        page = _request("GET", f"{BASE}/dags?limit=100&offset={offset}").json()
        dags.extend(page.get("dags", []))
        offset += 100
        if offset >= page.get("total_entries", 0):
            break
    return [
        {"dag_id": d["dag_id"], "is_paused": d["is_paused"]}
        for d in dags
        if (d.get("fileloc") or "").startswith(PROJECT_ROOT) and ".venv" not in (d.get("fileloc") or "")
    ]


def get_dag_run_status(dag_id: str = "training_pipeline", run_id: str = None):
    """Get latest (or specific) DAG run status."""
    url = f"{BASE}/dags/{dag_id}/dagRuns/{run_id}" if run_id else f"{BASE}/dags/{dag_id}/dagRuns?order_by=-start_date&limit=1"
    d = _request("GET", url).json()
    return d.get("dag_runs", [d])[0] if "dag_runs" in d else d


def trigger_dag(dag_id: str = "training_pipeline"):
    """Trigger an approved DAG by id only."""
    if dag_id not in ALLOWED_DAGS:
        raise PermissionError(f"DAG '{dag_id}' not approved")
    return _request("POST", f"{BASE}/dags/{dag_id}/dagRuns", json={"logical_date": None}).json()


def get_failed_tasks(dag_id: str, run_id: str):
    """List failed task instances for a DAG run."""
    tasks = _request("GET", f"{BASE}/dags/{dag_id}/dagRuns/{run_id}/taskInstances").json().get("task_instances", [])
    return [t for t in tasks if t.get("state") == "failed"]


def get_task_logs(dag_id: str, run_id: str, task_id: str, try_number: int = 1):
    """Fetch logs for a specific task instance."""
    return _request(
        "GET", f"{BASE}/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/logs/{try_number}"
    ).text
