# Task 3: The System Agent - Implementation Plan

## Overview

Extend the Task 2 documentation agent with a `query_api` tool to query the deployed backend. This enables the agent to answer:
1. **Static system facts** - framework, ports, status codes (via `read_file` on source)
2. **Data-dependent queries** - item counts, scores, analytics (via `query_api`)

## Tool Schema Design

### `query_api` Function Schema

```python
{
    "type": "function",
    "function": {
        "name": "query_api",
        "description": "Query the backend API. Use for data-dependent questions like item counts, scores, analytics.",
        "parameters": {
            "type": "object",
            "properties": {
                "method": {"type": "string", "description": "HTTP method: GET, POST, PUT, DELETE"},
                "path": {"type": "string", "description": "API path, e.g., '/items/', '/analytics/scores'"},
                "body": {"type": "string", "description": "Optional JSON request body for POST/PUT"}
            },
            "required": ["method", "path"]
        }
    }
}
```

## Authentication Strategy

The `query_api` tool must authenticate using `LMS_API_KEY`:

1. Read `LMS_API_KEY` from environment variable (falls back to `.env.docker.secret`)
2. Read `AGENT_API_BASE_URL` from environment (default: `http://localhost:42002`)
3. Add header: `Authorization: Bearer ${LMS_API_KEY}`
4. Construct URL: `${AGENT_API_BASE_URL}${path}`

**Important:** Two distinct keys:
- `LLM_API_KEY` - authenticates with LLM provider (in `.env.agent.secret`)
- `LMS_API_KEY` - authenticates with backend API (in `.env.docker.secret`)

## System Prompt Update

The system prompt must guide the LLM to choose the right tool:

| Question Type | Tool | Example |
|--------------|------|---------|
| Wiki/documentation | `read_file` on `wiki/` | "What is the Git workflow?" |
| Source code facts | `read_file` on `backend/` | "What framework is used?" |
| Data queries | `query_api` | "How many items?" |
| Bug diagnosis | `query_api` → `read_file` | "Why does this endpoint fail?" |

## Environment Variables

All configuration must come from environment variables (autochecker injects its own values):

| Variable | Purpose | Default |
|----------|---------|---------|
| `LLM_API_KEY` | LLM provider API key | - |
| `LLM_API_BASE` | LLM API endpoint URL | - |
| `LLM_MODEL` | Model name | `qwen3-coder-plus` |
| `LMS_API_KEY` | Backend API key | - |
| `AGENT_API_BASE_URL` | Backend base URL | `http://localhost:42002` |

## Implementation Steps

1. Add `query_api` to `TOOLS` list with proper schema
2. Implement `query_api(method, path, body)` function:
   - Read env vars for base URL and API key
   - Build request with auth header
   - Return JSON string with `status_code` and `body`
3. Update `execute_tool()` to handle `query_api`
4. Update system prompt with tool selection guidance
5. Update output format - `source` is now optional for data queries

## Testing Strategy

Run `uv run run_eval.py` to test against 10 local questions:
- Wiki lookup questions
- System fact questions
- Data-dependent questions
- Bug diagnosis questions
- Reasoning questions

Iterate based on failures:
- If tool not called → improve tool description
- If tool returns error → fix implementation
- If wrong arguments → clarify schema

## Initial Benchmark Results

First run results after implementing `query_api`:

- **Initial Score:** 5/10 passed
- **First failures:**
  1. Question 2 (SSH wiki): Agent returned intermediate thoughts instead of final answer
  2. Question 4 (API routers): Agent didn't use tools, returned intermediate thoughts
  3. Question 6 (auth status): Agent used auth when it should test without auth
  4. Question 7 (completion-rate bug): Agent found bug but didn't include source field

- **Iteration strategy:**
  1. Updated system prompt to emphasize "NEVER return intermediate thoughts"
  2. Added explicit step-by-step instructions for each question type
  3. Added `use_auth` parameter to `query_api` for testing unauthenticated access
  4. Updated system prompt to include source field for bug diagnosis questions
  5. Added guidance for Docker/config file discovery

## Final Benchmark Results

- **Final Score:** 10/10 passed (consistent across multiple runs)
- **Tests added:** 3 regression tests (1 existing + 2 new)
  - `test_agent_json_output` - verifies JSON output structure
  - `test_framework_question_uses_read_file` - verifies read_file for framework questions
  - `test_items_count_question_uses_query_api` - verifies query_api for data questions

## Lessons Learned

*(To be filled after completing the task)*
