# tests/test_airflow_tools.py
import pytest, requests
from unittest.mock import patch
from agent.tools import airflow_tools

def test_trigger_dag_rejects_unapproved():
    with pytest.raises(PermissionError):
        airflow_tools.trigger_dag("other_dag")

def test_get_dag_run_status_timeout():
    with patch("agent.tools.airflow_tools.requests.get", side_effect=requests.Timeout):
        with pytest.raises(requests.Timeout):
            airflow_tools.get_dag_run_status()