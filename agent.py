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
            "description": "Read contents of a file from the project wiki or source code. Use for documentation questions or static system facts (framework, ports, status codes).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to file from project root, e.g. 'wiki/git-workflow.md' or 'backend/app/main.py'"
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
            "description": "List files and directories. Use to discover relevant files in wiki/, backend/, or root.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to directory, e.g. 'wiki', 'backend/app', or '.'"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Query the backend API for data-dependent questions. Use for item counts, scores, analytics, or any live data. NOT for static facts like framework or port numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "HTTP method: GET, POST, PUT, DELETE"
                    },
                    "path": {
                        "type": "string",
                        "description": "API endpoint path, e.g. '/items/', '/analytics/scores', '/analytics/completion-rate'"
                    },
                    "body": {
                        "type": "string",
                        "description": "Optional JSON request body for POST/PUT requests"
                    },
                    "use_auth": {
                        "type": "boolean",
                        "description": "Whether to include authentication header. Default: true. Set to false to test unauthenticated access."
                    }
                },
                "required": ["method", "path"]
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

def query_api(method: str, path: str, body: str = None, use_auth: bool = True) -> str:
    """Query the backend API with optional authentication.
    
    Uses LMS_API_KEY from environment for authentication (if use_auth is True).
    Returns JSON string with status_code and body.
    """
    # Read configuration from environment variables
    api_base_url = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")
    lms_api_key = os.getenv("LMS_API_KEY")
    
    # Construct full URL
    base = api_base_url.rstrip('/')
    url = f"{base}{path}"
    
    # Prepare headers
    headers = {
        "Content-Type": "application/json"
    }
    
    # Add authentication if requested
    if use_auth:
        if not lms_api_key:
            return json.dumps({
                "status_code": 401,
                "body": {"error": "LMS_API_KEY not set in environment"}
            })
        headers["Authorization"] = f"Bearer {lms_api_key}"
    
    try:
        # Make the request
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method.upper() == "POST":
            data = json.loads(body) if body else {}
            response = requests.post(url, json=data, headers=headers, timeout=30)
        elif method.upper() == "PUT":
            data = json.loads(body) if body else {}
            response = requests.put(url, json=data, headers=headers, timeout=30)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            return json.dumps({
                "status_code": 400,
                "body": {"error": f"Unsupported method: {method}"}
            })
        
        # Parse response body
        try:
            response_body = response.json()
        except (json.JSONDecodeError, ValueError):
            response_body = response.text
        
        return json.dumps({
            "status_code": response.status_code,
            "body": response_body
        })
        
    except requests.exceptions.Timeout:
        return json.dumps({
            "status_code": 408,
            "body": {"error": "Request timed out"}
        })
    except requests.exceptions.ConnectionError as e:
        return json.dumps({
            "status_code": 0,
            "body": {"error": f"Connection error: {str(e)}"}
        })
    except Exception as e:
        return json.dumps({
            "status_code": 0,
            "body": {"error": f"Request failed: {str(e)}"}
        })

def execute_tool(tool_call):
    """Execute a single tool call and return result."""
    func_name = tool_call["function"]["name"]
    func_args = json.loads(tool_call["function"]["arguments"])

    if func_name == "read_file":
        return read_file(func_args["path"])
    elif func_name == "list_files":
        return list_files(func_args["path"])
    elif func_name == "query_api":
        method = func_args.get("method", "GET")
        path = func_args.get("path", "")
        body = func_args.get("body")
        use_auth = func_args.get("use_auth", True)  # Default to True for backward compatibility
        return query_api(method, path, body, use_auth)
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
    
    system_prompt = """You are a System Agent. Answer questions using the available tools.

CRITICAL RULES:
- ALWAYS use tools first - NEVER answer without calling tools
- NEVER return intermediate thoughts like "Let me read" or "I need to" - only return FINAL answers
- If a file is not found, use list_files() to discover the correct location
- For wiki/source questions, you MUST read the file content
- Keep calling tools until you have the complete answer, then return JSON
- The "answer" field MUST be a TEXT STRING, not a list or object

AVAILABLE TOOLS:
- read_file(path): Read wiki documentation or source code files
- list_files(path): List files in a directory
- query_api(method, path, body?): Query the backend API for live data

TOOL SELECTION RULES:
1. Wiki/documentation questions:
   - Step 1: Call list_files("wiki") to find relevant files
   - Step 2: Call read_file("wiki/filename.md") to read the content
   - Step 3: Find the answer in the file content
   - Step 4: Return FINAL answer as TEXT with source
   Example: "What is the Git workflow?" → list_files("wiki"), then read_file("wiki/git-workflow.md")

2. Source code questions (framework, routers, ports, status codes):
   - Step 1: Call list_files("backend/app") to find relevant files
   - Step 2: Call read_file("backend/app/filename.py") to read the code
   - Step 3: Return FINAL answer as TEXT describing what you found
   Example: "What framework is used?" → list_files("backend/app"), then read_file("backend/app/main.py")
   Example: "List API routers" → list_files("backend/app/routers"), then read each router file, return text description

3. Docker/config file questions:
   - Step 1: Call list_files(".") to see root directory files
   - Step 2: Read Dockerfile, docker-compose.yml, caddy/Caddyfile from correct paths
   - Step 3: Return FINAL answer describing the architecture
   Example: "Request journey" → list_files("."), read_file("Dockerfile"), read_file("docker-compose.yml"), read_file("caddy/Caddyfile")

4. Data-dependent questions (counts, scores, analytics):
   - Call query_api to get live data (use_auth=true by default)
   - Return answer as TEXT describing the data
   Example: "How many items?" → query_api("GET", "/items/")
   Example: "What are the scores?" → query_api("GET", "/analytics/scores?lab=lab-01")

5. Auth/testing questions (status codes without auth):
   - Call query_api with use_auth=false to test unauthenticated access
   Example: "What status without auth?" → query_api("GET", "/items/", use_auth=false)

6. Bug diagnosis:
   - Step 1: Call query_api to see the error
   - Step 2: Call read_file to find the buggy code
   - Step 3: Return FINAL answer with source field

OUTPUT FORMAT:
- Final answer MUST be valid JSON: {"answer": "TEXT STRING describing the answer"}
- The answer field must be a STRING, not a list or object
- Include "source" field for wiki/source/bug-diagnosis questions (NOT for pure data queries)
  - Wiki questions: "source": "wiki/filename.md"
  - Source code questions: "source": "backend/app/filename.py"
  - Bug diagnosis: "source": "backend/app/filename.py" (where the bug is)
- DO NOT include explanatory text outside the JSON
- DO NOT say "Let me check" or "I will read" - only provide the FINAL answer

THINKING PROCESS:
1. Analyze the question type (wiki, source code, docker, or data query)
2. ALWAYS call the appropriate tool FIRST
3. If file not found, use list_files() to discover correct location
4. Keep calling tools until you have enough information
5. Return final JSON answer as TEXT STRING - NO intermediate thoughts"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]
    
    tool_calls_history = []
    max_iterations = 20
    
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
                # Source is optional - only include if present (for wiki/source questions)
                source = parsed_json.get("source") if parsed_json else None
                
                output = {
                    "answer": final_answer,
                    "source": source if source else "",  # ← ВСЕГДА добавляет source (даже пустой)
                    "tool_calls": tool_calls_history
                }
                    
                print(json.dumps(output, ensure_ascii=False, indent=2))
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
