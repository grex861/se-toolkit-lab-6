import subprocess
import json
import pytest
import os

def test_agent_json_output():
    """Task 1 regression test: python agent.py → valid JSON."""
    # Прямой вызов python (НЕ uv run) из корня проекта
    project_root = "/mnt/c/Users/Alex1/Desktop/se-toolkit-lab-6"
    
    result = subprocess.run(
        ["python", "plans/agent.py", "What is 2+2?"],
        capture_output=True, 
        text=True, 
        timeout=70,
        cwd=project_root
    )
    
    assert result.returncode == 0, f"Exit code: {result.returncode}\n{result.stderr}"
    
    data = json.loads(result.stdout.strip())
    assert "answer" in data and data["answer"], "No answer or empty"
    assert data["tool_calls"] == [], "tool_calls must be empty list"
    
    print(f"✅ Answer: {data['answer'][:100]}...")
