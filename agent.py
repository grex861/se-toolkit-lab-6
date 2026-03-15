#!/usr/bin/env python3
import sys
import json
import os
import re
from pathlib import Path
from dotenv import load_dotenv
import requests

load_dotenv(".env.agent.secret", override=True)

# Project root for path security
PROJECT_ROOT = Path(__file__).parent.resolve()

# Tool definitions for LLM
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read contents of a file from the project wiki directory. Use to find answers in documentation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to file from project root, e.g. 'wiki/git-workflow.md'"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories in wiki directory. Use first to discover relevant files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to directory, e.g. 'wiki'"
                    }
                },
                "required": ["path"]
            }
        }
    }
]

def read_file(path: str) -> str:
    """Read contents of a file by relative path from project root."""
    full_path = (PROJECT_ROOT / path).resolve()
    
    if not str(full_path).startswith(str(PROJECT_ROOT)):
        return f"Error: Access denied - path escapes project directory: {path}"
    
    if not full_path.exists():
        return f"Error: File not found: {path}"
    
    if full_path.is_dir():
        return f"Error: Path is a directory, not a file: {path}"
    
    try:
        return full_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {e}"

def list_files(path: str) -> str:
    """List files and directories at a given relative path."""
    full_path = (PROJECT_ROOT / path).resolve()
    
    if not str(full_path).startswith(str(PROJECT_ROOT)):
        return f"Error: Access denied - path escapes project directory: {path}"
    
    if not full_path.exists():
        return f"Error: Directory not found: {path}"
    
    if not full_path.is_dir():
        return f"Error: Path is not a directory: {path}"
    
    try:
        entries = []
        for entry in sorted(full_path.iterdir()):
            prefix = "[DIR] " if entry.is_dir() else ""
            entries.append(f"{prefix}{entry.name}")
        return "\n".join(entries)
    except Exception as e:
        return f"Error listing directory: {e}"

def execute_tool(tool_call):
    """Execute a single tool call and return result."""
    func_name = tool_call["function"]["name"]
    func_args = json.loads(tool_call["function"]["arguments"])
    
    if func_name == "read_file":
        return read_file(func_args["path"])
    elif func_name == "list_files":
        return list_files(func_args["path"])
    else:
        return f"Error: Unknown tool {func_name}"

def extract_json_from_text(text):
    """Extract JSON object from text that may contain explanatory content."""
    # Find JSON-like structure containing "source" field
    json_match = re.search(r'\{[^{}]*"source"[^{}]*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # Fallback: try entire text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None

def main():
    if len(sys.argv) != 2:
        print("Usage: uv run agent.py \"your question\"", file=sys.stderr)
        sys.exit(1)
    
    question = sys.argv[1]
    
    api_key = os.getenv("LLM_API_KEY")
    api_base = os.getenv("LLM_API_BASE")
    model = os.getenv("LLM_MODEL", "qwen3-coder-plus")
    
    if not all([api_key, api_base]):
        print("Missing LLM_API_KEY/LLM_API_BASE in .env.agent.secret", file=sys.stderr)
        sys.exit(1)
    
    base = api_base.rstrip('/')
    if not base.endswith('/v1'):
        url = f"{base}/v1/chat/completions"
    else:
        url = f"{base}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    system_prompt = """You are a Documentation Agent. Answer ONLY based on files in wiki/.

RULES:
1. First call list_files(path="wiki") to see available files
2. Then read_file(path="wiki/filename.md") to read relevant file  
3. Find section ## with the answer
4. Final answer MUST be valid JSON only: {"answer": "text", "source": "wiki/file.md#section"}

DO NOT include explanatory text. Output ONLY the JSON object."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]
    
    tool_calls_history = []
    max_iterations = 10
    
    for iteration in range(max_iterations):
        data = {
            "model": model,
            "messages": messages,
            "tools": TOOLS,
            "tool_choice": "auto",
            "temperature": 0.1
        }
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=60)
            response.raise_for_status()
            result_json = response.json()
            choice = result_json["choices"][0]
            message = choice["message"]
            
            messages.append(message)
            
            if message.get("tool_calls"):
                for tool_call in message["tool_calls"]:
                    result = execute_tool(tool_call)
                    
                    tool_info = {
                        "tool": tool_call["function"]["name"],
                        "args": json.loads(tool_call["function"]["arguments"]),
                        "result": result
                    }
                    tool_calls_history.append(tool_info)
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": result
                    })
            else:
                answer = message["content"].strip()
                parsed_json = extract_json_from_text(answer)
                
                final_answer = parsed_json.get("answer", answer) if parsed_json else answer
                source = parsed_json.get("source", "unknown") if parsed_json else "unknown"
                
                print(json.dumps({
                    "answer": final_answer,
                    "source": source,
                    "tool_calls": tool_calls_history
                }, ensure_ascii=False, indent=2))
                return
                
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    print(json.dumps({
        "answer": "Max iterations reached",
        "source": "unknown", 
        "tool_calls": tool_calls_history
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
