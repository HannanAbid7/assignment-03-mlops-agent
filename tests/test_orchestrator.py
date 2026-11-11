from unittest.mock import patch
from agent.orchestrator import _execute_tool

def test_no_invented_results_on_tool_failure():
    def boom(): raise ConnectionError("service down")
    with patch.dict("agent.orchestrator.TOOLS", {"boom": boom}):
        r = _execute_tool("boom", {}, "req1")
        assert r["status"] == "error" and "down" in r["error"]

def test_tool_success_path():
    with patch.dict("agent.orchestrator.TOOLS", {"ok": lambda: {"v": 1}}):
        r = _execute_tool("ok", {}, "req1")
        assert r["status"] == "ok" and r["data"]["v"] == 1

def test_logs_contain_no_secrets(caplog):
    import logging
    with patch.dict("agent.orchestrator.TOOLS", {"ok": lambda: {"v": 1}}):
        with caplog.at_level(logging.INFO):
            _execute_tool("ok", {}, "req1")
    assert "LLM_API_KEY" not in caplog.text and "secret" not in caplog.text.lower()