from numpy import exp

from mlflow.tracking import MlflowClient
client = MlflowClient(tracking_uri="http://localhost:5000")

def list_experiments():
    return [{"id": e.experiment_id, "name": e.name} for e in client.search_experiments()]

def list_runs(experiment_name: str = "iris-training", max_results: int = 20):
    exp = client.get_experiment_by_name(experiment_name)
    runs = client.search_runs([exp.experiment_id], max_results=max_results)
    return [{"run_id": r.info.run_id, "params": r.data.params, "metrics": r.data.metrics} for r in runs]

def get_run_details(run_id: str):
    r = client.get_run(run_id)
    return {"params": r.data.params, "metrics": r.data.metrics, "tags": r.data.tags, "artifact_uri": r.info.artifact_uri}

def get_best_run(metric_name: str = "f1_score", experiment_name: str = "iris-training", mode: str = "max"):
    runs = [r for r in client.search_runs([exp.experiment_id]) if metric_name in r.data.metrics]
    if not runs:
        return {"error": f"no runs with metric {metric_name}"}
    best = (max if mode == "max" else min)(runs, key=lambda r: r.data.metrics[metric_name])
    return {
        "run_id": best.info.run_id, "metrics": best.data.metrics, "tags": best.data.tags,
        "production_ready": False,
        "note": "Highest metric alone does not imply production readiness.",
    }

def compare_runs(run_ids: list[str]):
    return [get_run_details(r) for r in run_ids]

def get_model_versions(model_name: str = "iris-model"):
    try:
        return [{"version": v.version, "stage": v.current_stage} for v in client.search_model_versions(f"name='{model_name}'")]
    except Exception:
        return []