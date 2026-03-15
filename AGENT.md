# Agent Documentation

## Architecture

CLI → agent.py → Qwen Code API → Agentic Loop → JSON response
↓
Tools: read_file, list_files

text

## Qwen Code API Configuration

- **Base URL**: `http://10.93.26.101:42005/v1`
- **Model**: `qwen3-coder-plus`
- **API Key**: `my-secret-qwen-key`

## Tools

### `read_file(path: str)`

- Reads file contents from project wiki directory
- **Security**: Path must resolve within `PROJECT_ROOT`
- **Returns**: File content or error message

### `list_files(path: str)`  

- Lists files/directories at relative path
- **Security**: Path must resolve within `PROJECT_ROOT`
- **Returns**: Newline-separated list with `[DIR]` prefix

## Agentic Loop

Question → LLM + tools → tool_calls?
↓ YES ↓ NO
Execute tools → Loop → JSON {"answer", "source"}

text

1. Send question + system prompt + tools to LLM
2. Parse `tool_calls` → execute → append `{"role": "tool"}` → repeat
3. No tool_calls → extract `{"answer": "...", "source": "..."}`
4. Max 10 iterations

## Path Security

```python
full_path = (PROJECT_ROOT / user_path).resolve()
if not str(full_path).startswith(str(PROJECT_ROOT)):
    return "Error: Access denied"
Prevents ../ traversal attacks.

Environment (.env.agent.secret)
text
LLM_API_KEY=my-secret-qwen-key
LLM_API_BASE=http://10.93.26.101:42005/v1
LLM_MODEL=qwen3-coder-plus
Usage
bash
uv run agent.py "How do you resolve a merge conflict?"
Output:

json
{
  "answer": "Edit the conflicting file...",
  "source": "wiki/git.md#merge-conflict",
  "tool_calls": [{"tool": "list_files", ...}]
}
Dependencies
text
requests>=2.32.0
python-dotenv
text

## 3. Fixed `plans/task-2.md` (update existing)

Add to your existing `plans/task-2.md`:

```markdown
## JSON Parsing Fix

LLM returns text containing JSON. Added `extract_json_from_text()`:

```python
json_match = re.search(r'\{[^{}]*"source"[^{}]*\}', text, re.DOTALL)
Extracts JSON substring containing "source" field from explanatory text.

System Prompt Update
text
"Output ONLY the JSON object. DO NOT include explanatory text."
text

## 🎉 **Now it will output CORRECTLY**:

```json
{
  "answer": "A merge conflict occurs when two branches modify the same lines...",
  "source": "wiki/git.md#merge-conflict",
  "tool_calls": [...]
}
