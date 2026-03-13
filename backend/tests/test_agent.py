import subprocess
import sys
import json

def test_agent_json_output():
    result = subprocess.run(
        ["uv", "run", "agent.py", "What is 2+2?"],
        capture_output=True, text=True, timeout=70
    )
    assert result.returncode == 0
    data = json.loads(result.stdout.strip())
    assert "answer" in data and data["answer"]
    assert data["tool_calls"] == []
    print("✅ Test passed!")

if __name__ == "__main__":
    test_agent_json_output()
