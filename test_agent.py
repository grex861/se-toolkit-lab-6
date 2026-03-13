import subprocess
import json
import pytest

def test_agent_json_output():
    result = subprocess.run(
        ["python", "agent.py", "What is 2+2?"],
        capture_output=True, text=True, timeout=70
    )
    assert result.returncode == 0
    data = json.loads(result.stdout.strip())
    assert "answer" in data
    assert data["tool_calls"] == []
