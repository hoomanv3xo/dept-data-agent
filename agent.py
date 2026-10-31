"""The agent loop: the model decides which tool to call, our code runs it, and the
result goes back to the model until it can answer."""
import json
import os
import time
from datetime import datetime, timezone

import cohere
from dotenv import load_dotenv

import db_tools

load_dotenv()
MODEL = os.getenv("COHERE_MODEL", "command-a-plus-05-2026")
MAX_STEPS = 6  # hard stop so the agent can never loop forever
LOG_FILE = "logs/audit.jsonl"

SYSTEM_PROMPT = """You are a data assistant for a university department. You answer questions about
courses, terms, and class sections using ONLY the database tools provided.

Rules:
- Call get_schema first if you are unsure about table or column names.
- Use query_data with a single read-only SQLite SELECT statement. Never guess numbers.
- When a chart would help (comparisons, trends), call make_chart with values taken from query results.
- If the data cannot answer the question, say so plainly. Do not make anything up.
- The data is synthetic sample data. Never ask for or reveal personal information.
- Keep answers short: state the finding first, then one sentence of context."""

TOOLS = [
    {"type": "function", "function": {
        "name": "get_schema",
        "description": "List the database tables, their columns, and sample rows.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "query_data",
        "description": "Run ONE read-only SQLite SELECT statement and return up to 200 rows.",
        "parameters": {"type": "object",
                       "properties": {"sql": {"type": "string", "description": "A single SELECT statement."}},
                       "required": ["sql"]}}},
    {"type": "function", "function": {
        "name": "make_chart",
        "description": "Display a bar or line chart using numbers that came from query results.",
        "parameters": {"type": "object",
                       "properties": {
                           "title": {"type": "string"},
                           "chart_type": {"type": "string", "enum": ["bar", "line"]},
                           "labels": {"type": "array", "items": {"type": "string"}},
                           "values": {"type": "array", "items": {"type": "number"}}},
                       "required": ["title", "chart_type", "labels", "values"]}}},
]


def _log(entry: dict):
    entry["time"] = datetime.now(timezone.utc).isoformat()
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _run_tool(name: str, args: dict, result: dict):
    """Run one tool. Returns the text sent back to the model. Fills `result` for the UI."""
    try:
        if name == "get_schema":
            return json.dumps(db_tools.get_schema())
        if name == "query_data":
            data = db_tools.run_query(args.get("sql", ""))
            result["table"] = data  # the UI shows the latest table
            result["sql"] = args.get("sql", "")
            return json.dumps(data)
        if name == "make_chart":
            if len(args["labels"]) != len(args["values"]):
                return "Error: labels and values must be the same length."
            result["chart"] = {k: args[k] for k in ("title", "chart_type", "labels", "values")}
            return "Chart displayed to the user."
        return f"Error: unknown tool {name}."
    except db_tools.QueryRejected as e:
        return f"Error: {e}"
    except (KeyError, TypeError) as e:
        return f"Error: bad tool arguments ({e})."

def _chat_with_retry(co, **kwargs):
    """Retry when the API says 'too many requests' (HTTP 429)."""
    for attempt in range(5):
        try:
            return co.chat(**kwargs)
        except Exception as e:
            if getattr(e, "status_code", None) == 429 and attempt < 4:
                time.sleep(15 * (attempt + 1))
                continue
            raise

def ask(question: str) -> dict:
    co = cohere.ClientV2(api_key=os.getenv("COHERE_API_KEY"))
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question}]
    result = {"answer": "", "steps": [], "table": None, "chart": None, "sql": None}
    started = time.monotonic()

    for _ in range(MAX_STEPS):
        response = _chat_with_retry(co, model=MODEL, messages=messages, tools=TOOLS)
        msg = response.message
        if not msg.tool_calls:
            result["answer"] = "".join(getattr(c, "text", "") or "" for c in (msg.content or []))
            break
        messages.append(msg)
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments or "{}")
            output = _run_tool(tc.function.name, args, result)
            result["steps"].append({"tool": tc.function.name, "args": args,
                                    "ok": not output.startswith("Error")})
            _log({"question": question, "tool": tc.function.name, "args": args,
                  "output_preview": output[:300]})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": output})
    else:
        result["answer"] = "I couldn't finish this question within the step limit. Try a more specific question."

    result["seconds"] = round(time.monotonic() - started, 2)
    _log({"question": question, "answer": result["answer"], "seconds": result["seconds"]})
    return result
