# Agent Documentation

## Architecture (Task 3)

The System Agent extends the Task 2 documentation agent with a new `query_api` tool for querying the deployed backend. The architecture follows the same agentic loop pattern:

```
CLI → agent.py → Qwen API → Agentic Loop (max 20 iterations) → JSON
                    ↓ Tools: read_file | list_files | query_api
Wiki facts ← read_file("wiki/")
System facts ← read_file("backend/")
Data queries ← query_api("GET", "/items/", auth=true)
```

The key insight from Task 3 is that documentation can be outdated — the real system is the source of truth. The agent now handles two new question classes:
1. **Static system facts** — framework, ports, status codes (use `read_file` on source)
2. **Data-dependent queries** — item counts, scores, analytics (use `query_api`)

## Tools

### `read_file(path)`

- **Wiki**: `wiki/git.md#merge-conflict`
- **System**: `backend/app/main.py`, `pyproject.toml`, `Dockerfile`
- **Security**: `PROJECT_ROOT` prefix validation (rejects `..` paths)

### `list_files(path)`

- **Discovery**: `wiki/`, `backend/`, `.` (root)
- **Format**: `[DIR] name\nfile.md`

### `query_api(method, path, body?, use_auth?)`

```python
# Environment-driven configuration
AGENT_API_BASE_URL=http://localhost:42002  # default
LMS_API_KEY=backend-secret                 # from .env.docker.secret

# Returns:
{"status_code": 200, "body": [...]}

# Data queries: GET /items/, GET /analytics/scores
# Debug queries: GET /analytics/completion-rate?lab=lab-99
# Auth header: Authorization: Bearer ${LMS_API_KEY}
```

**Authentication:** The tool uses `LMS_API_KEY` (from `.env.docker.secret` or environment) to authenticate with the backend. This is a different key from `LLM_API_KEY` which authenticates with the LLM provider — never mix them up.

## Environment Variables

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` or env |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` or env |
| `LLM_MODEL` | Model name | `.env.agent.secret` or env |
| `LMS_API_KEY` | Backend API key for `query_api` auth | `.env.docker.secret` or env |
| `AGENT_API_BASE_URL` | Base URL for `query_api` | env (default: `http://localhost:42002`) |

The autochecker injects its own values, so the agent must read from environment variables, not hardcoded values.

## Agentic Loop

```
Question → LLM(tools) → tool_calls?
  ↓ YES                          ↓ NO
execute → {"role": "tool"} → loop  → extract JSON → {"answer", "source"}
```

**Source inference:**
- `read_file` → extract file path from answer (wiki/backend/docker)
- `query_api` → no source (system data questions)
- Fallback → empty string

## Tool Decision Logic

The LLM decides which tool to use based on the system prompt guidance:

| Question Type | Tool | Example |
|--------------|------|---------|
| Wiki/documentation | `read_file` on `wiki/` | "What is the Git workflow?" |
| Source code | `read_file` on `backend/app/` | "What framework is used?" |
| Data queries | `query_api` with `use_auth=true` | "How many items?" |
| Auth errors | `query_api` with `use_auth=false` | "Test unauthenticated access" |
| Bug diagnosis | `query_api` → `read_file` | "Why does this endpoint fail?" |

## Lessons Learned

1. **Tool descriptions matter** — Initially the LLM didn't use `query_api` for data questions. Adding explicit examples ("items count, scores, analytics") to the tool description fixed this. The tool description should clearly state when to use each tool and provide concrete examples.

2. **Environment-first configuration** — The autochecker runs with different credentials. Reading environment variables before falling back to `.env` files ensures the agent works in both local and evaluation environments. Never hardcode API keys or URLs.

3. **Max iterations** — Increased from 10 to 20 to handle multi-step bug diagnosis questions that require querying the API, reading source files, and then providing an answer. Complex questions may need multiple tool calls.

4. **Intermediate thoughts problem** — The LLM sometimes returns intermediate thoughts like "Let me read this file" instead of the final answer. The system prompt must explicitly forbid this behavior and emphasize returning only final answers.

5. **Source field for bug diagnosis** — Bug diagnosis questions require both querying the API to see the error AND reading the source code to find the bug. The system prompt must guide the LLM to include the source field pointing to the buggy file.

6. **Optional authentication** — Some questions ask about unauthenticated access (e.g., "What status code without auth?"). The `query_api` tool needs a `use_auth` parameter to support testing both authenticated and unauthenticated scenarios.

7. **LLM non-determinism** — Even with temperature=0.1, the LLM can behave inconsistently. Running the eval multiple times helps identify flaky behavior. A good system prompt reduces but doesn't eliminate this issue.

8. **File discovery for config files** — Docker and config files may be in unexpected locations (e.g., `Dockerfile` at root, not `backend/Dockerfile`). The system prompt should guide the LLM to list directories first before reading files.

## Final Evaluation Score

**Local benchmark: 10/10 passed** (consistent across multiple runs)

The agent passes all local regression tests:
- `test_framework_question_uses_read_file` — verifies `read_file` for framework questions
- `test_items_count_question_uses_query_api` — verifies `query_api` for data questions  
- `test_agent_json_output` — verifies JSON output structure

The agent successfully answers:
- Wiki lookup questions (e.g., branch protection steps, SSH connection guide)
- System fact questions (e.g., FastAPI framework, API routers)
- Data-dependent questions (e.g., item counts, analytics scores)
- Auth testing questions (e.g., 401 status without auth)
- Bug diagnosis questions (e.g., division by zero, NoneType comparison)
- Architecture questions (e.g., request flow, ETL idempotency)

**Note:** The autochecker bot tests 10 additional hidden questions and uses LLM-based judging for open-ended answers. The local benchmark uses simple keyword matching.
