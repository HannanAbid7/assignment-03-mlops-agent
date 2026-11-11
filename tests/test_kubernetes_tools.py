# tests/test_kubernetes_tools.py
import pytest
from agent.tools import kubernetes_tools

def test_rejects_wrong_namespace():
    with pytest.raises(PermissionError):
        kubernetes_tools.list_pods_and_deployments(namespace="default")

def test_restart_requires_confirm():
    with pytest.raises(PermissionError):
        kubernetes_tools.restart_deployment(confirm=False)