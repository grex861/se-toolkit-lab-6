# Task 2: The Documentation Agent - Implementation Plan

## Overview

Transform the Task 1 CLI into an **agent** by adding tool-calling capabilities (`read_file`, `list_files`) and an agentic loop that executes tools and feeds results back to the LLM.

## Tool Definitions

Define two tools using OpenAI-compatible function-calling schemas in the `tools` parameter:

### `read_file`
- **Name**: `read_file`
- **Description**: "Read contents of a file by relative path from project root"
- **Parameters**: `path` (string, required) - relative path like "wiki/git-workflow.md"
- **Returns**: File contents as string, or error message if file doesn't exist

### `list_files`
- **Name**: `list_files`
- **Description**: "List files and directories at a given relative path"
- **Parameters**: `path` (string, required) - relative directory path like "wiki"
- **Returns**: Newline-separated list of entries

## Agentic Loop

```
Question → LLM → tool_calls? → yes → execute → append result → back to LLM
                                      │
                                      no
                                      │
                                      ▼
                                 Extract answer + source → JSON output
```

**Implementation:**

1. Send user question + system prompt + tool definitions to LLM
2. Check `response.choices[0].message.tool_calls`:
   - If non-empty: parse each call, execute the tool, append result as `{"role": "tool", "tool_call_id": id, "content": result}`, loop back to step 1
   - If empty: extract answer and source from `response.choices[0].message.content`
3. Maximum 10 tool calls per question (stop looping if exceeded)

## Path Security

Prevent directory traversal attacks (`../`):

1. Resolve the full path: `os.path.realpath(os.path.join(PROJECT_ROOT, user_path))`
2. Validate: resolved path must start with `PROJECT_ROOT` prefix
3. Reject paths that escape the project directory with a descriptive error
4. Handle both relative paths and absolute paths safely

## System Prompt Strategy

The system prompt will instruct the LLM to:

1. Use `list_files` to discover wiki files when needed
2. Use `read_file` to read relevant files and find answers
3. Include source references in the format `path#section-anchor` (e.g., `wiki/git-workflow.md#resolving-merge-conflicts`)
4. Output the final answer with the source clearly identified

## Output Format

```json
{
  "answer": "Edit the conflicting file, choose which changes to keep, then stage and commit.",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "git-workflow.md\n..."},
    {"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": "..."}
  ]
}
```

## Dependencies

- `openai` (already used in Task 1 for API calls)
- `python-dotenv` (already used for env loading)

## Error Handling

- Tool execution errors: return as tool result (e.g., "Error: File not found")
- API errors: print to stderr, exit code 1
- Path security violations: return error message as tool result
- Max tool calls exceeded: use whatever answer is available

## Testing Strategy

Two regression tests:

1. **"How do you resolve a merge conflict?"** - expects `read_file` in tool_calls, `wiki/git-workflow.md` in source
2. **"What files are in the wiki?"** - expects `list_files` in tool_calls
