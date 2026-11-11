import pytest
from agent.tools import dvc_tools

def test_rejects_non_allowlisted_subcommand():
    with pytest.raises(PermissionError):
        dvc_tools._run_dvc(["remove"])