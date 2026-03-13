# Task 1: Call an LLM from Code - Implementation Plan

## LLM Provider
- **Qwen Code API** (deployed on VM Gresh001)
- **Model**: `qwen3-coder-plus` (strong tool calling support)
- **Base URL**: `http://10.93.26.101:42005/v1`
- **API Key**: `my-secret-qwen-key` (from `.env.agent.secret`)

## Architecture

```
user question → agent.py → openai-python-client → Qwen API → JSON response
```

## Implementation Steps

1. **CLI**: Parse `sys.argv[1]` for the question
2. **Config**: Load environment variables using `python-dotenv` from `.env.agent.secret`
3. **Client**: Use `openai.OpenAI` (compatible with Qwen OpenAI API)
4. **Request**: Call `/v1/chat/completions` with `messages=[{"role": "user", "content": question}]`
5. **Response**: Output `{"answer": response.content, "tool_calls": []}` to stdout as JSON

## Dependencies

```text
openai>=1.0.0
python-dotenv
```

## Error Handling

- **Timeout**: 60s (`timeout=60.0`)
- **JSON validation**: `json.dumps(ensure_ascii=False)`
- **API errors**: Print to stderr + exit code 1
- **Missing env**: Print to stderr + exit code 1

## Output Format

```json
{"answer": "Representational State Transfer.", "tool_calls": []}
```