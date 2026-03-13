import subprocess
import json
import pytest
import os

def test_agent_json_output():
    """Task 1 regression test: python agent.py → valid JSON."""
    # Запуск из backend/tests/ → корень проекта
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    
    result = subprocess.run(
        ["python", os.path.join(project_root, "agent.py"), "What is 2+2?"],
        capture_output=True, 
        text=True, 
        timeout=70,
        cwd=project_root
    )
    
    assert result.returncode == 0, f"Exit code: {result.returncode}\n{result.stderr}"
    
    data = json.loads(result.stdout.strip())
    assert "answer" in data 
    assert data["tool_calls"] == []
    
    print(f"✅ Answer: {data['answer'][:100]}...")
