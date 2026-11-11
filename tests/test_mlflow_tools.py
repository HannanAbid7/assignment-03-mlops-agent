# tests/test_mlflow_tools.py
from unittest.mock import patch, MagicMock
from agent.tools import mlflow_tools

def test_get_best_run_picks_highest_metric():
    run = MagicMock(); run.info.run_id = "r1"; run.data.metrics = {"f1_score": 0.9}; run.data.tags = {}
    exp = MagicMock(experiment_id="1")
    with patch.object(mlflow_tools.client, "get_experiment_by_name", return_value=exp), \
         patch.object(mlflow_tools.client, "search_runs", return_value=[run]):
        result = mlflow_tools.get_best_run()
        assert result["run_id"] == "r1" and result["production_ready"] is False

def test_get_best_run_no_matches():
    exp = MagicMock(experiment_id="1")
    with patch.object(mlflow_tools.client, "get_experiment_by_name", return_value=exp), \
         patch.object(mlflow_tools.client, "search_runs", return_value=[]):
        assert "error" in mlflow_tools.get_best_run()