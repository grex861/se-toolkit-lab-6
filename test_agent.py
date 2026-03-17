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


def test_framework_question_uses_read_file():
    """Test that framework questions use read_file tool to check source code."""
    result = subprocess.run(
        ["python", "agent.py", "What Python web framework does this project's backend use?"],
        capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0
    data = json.loads(result.stdout.strip())
    
    assert "answer" in data
    assert "tool_calls" in data
    
    # Verify read_file was used to check source code
    tools_used = [tc.get("tool") for tc in data["tool_calls"]]
    assert "read_file" in tools_used, f"Expected read_file in tool_calls, got: {tools_used}"
    
    # Verify the answer mentions FastAPI
    answer = data.get("answer", "").lower()
    assert "fastapi" in answer, f"Expected 'fastapi' in answer, got: {data.get('answer')}"


def test_items_count_question_uses_query_api():
    """Test that data-dependent questions use query_api tool."""
    result = subprocess.run(
        ["python", "agent.py", "How many items are currently stored in the database?"],
        capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0
    data = json.loads(result.stdout.strip())
    
    assert "answer" in data
    assert "tool_calls" in data
    
    # Verify query_api was used to get live data
    tools_used = [tc.get("tool") for tc in data["tool_calls"]]
    assert "query_api" in tools_used, f"Expected query_api in tool_calls, got: {tools_used}"
    
    # Verify the answer contains a number
    answer = data.get("answer", "")
    import re
    numbers = re.findall(r'\d+', answer)
    assert len(numbers) > 0, f"Expected a number in answer, got: {answer}"
