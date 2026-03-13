#!/usr/bin/env python3
import sys
import json
import os
from pathlib import Path
from dotenv import load_dotenv
import requests

load_dotenv(".env.agent.secret", override=True)

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
    
    # Fixed URL - remove trailing /v1 if present, add correct endpoint
    base = api_base.rstrip('/')
    if not base.endswith('/v1'):
        url = f"{base}/v1/chat/completions"
    else:
        url = f"{base}/chat/completions"
        
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": question}],
        "temperature": 0.1
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=60)
        response.raise_for_status()
        
        result_json = response.json()
        answer = result_json["choices"][0]["message"]["content"].strip()
        
        print(json.dumps({
            "answer": answer,
            "tool_calls": []
        }, ensure_ascii=False))
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
