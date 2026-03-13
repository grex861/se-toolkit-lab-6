# Agent Documentation

## Architecture

CLI → agent.py → Qwen Code API (VM Gresh001) → JSON response

user question → requests.post() → <http://10.93.26.101:42005/v1/chat/completions> → {"answer": "...", "tool_calls": []}

## Qwen Code API Configuration

- **Base URL**: `http://10.93.26.101:42005/v1`
- **Model**: `qwen3-coder-plus` (strong tool calling support)
- **API Key**: `my-secret-qwen-key`

## Environment (.env.agent.secret)

LLM_API_KEY=my-secret-qwen-key
LLM_API_BASE=<http://10.93.26.101:42005/v1>
LLM_MODEL=qwen3-coder-plus

text

## Usage

```bash
uv run agent.py "What does REST stand for?"
Example output:

json
{"answer": "Representational State Transfer (REST) is an architectural style...", "tool_calls": []}
Dependencies
text
requests==2.32.3
python-dotenv
