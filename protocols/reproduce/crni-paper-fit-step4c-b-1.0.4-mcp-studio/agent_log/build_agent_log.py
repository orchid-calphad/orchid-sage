#!/usr/bin/env python3
"""Publishable log of an AI-agent session (Claude Code CLI, headless `claude -p ... --output-format stream-json`).

  build_agent_log.py --stream SESSION.jsonl --meta META.json --out OUT_DIR [--persisted DIR] [--sanitizer public_sanitize.py]
                     [--alias PATH=PLACEHOLDER ...]

Reads the stream-json transcript the client wrote (the system/init record, every assistant message with its content
blocks, every tool result returned to the model, the client's permission denials and the final result record) and writes

  OUT_DIR/agent_log.jsonl   line 1: the header (role "header"); then one record per event, in order:
                            {seq, turn, role, type, content, tool_name, tool_input, tool_result, call_id, is_error,
                             timestamp, model}
  OUT_DIR/agent_log.md      the same, readable: header, the exact prompt, then turn by turn
  OUT_DIR/agent_log_header.json

Every string is sanitized with the rules of protocols/tools/public_sanitize.py (home paths, user and host names,
session ids, addresses), then the --alias replacements (longest first: a local directory -> a named placeholder such as
<run-dir>), then any remaining home-relative path -> '<home>/...'. Identifiers of the client and the API (session id, message and request
ids, record uuids, the messaging socket) are dropped; tool-use ids become call-001, call-002, ... Thinking blocks are kept
as records, but the client stored no thinking text (empty, with an opaque signature that is omitted). Progress pings
(tool_progress), rate-limit and thinking-token counters are not model inputs or outputs and are left out (counted in
the header). Standard library only.
"""
import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path


def load_sanitizer(p):
    spec = importlib.util.spec_from_file_location("public_sanitize", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.sanitize_text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stream", required=True)
    ap.add_argument("--meta", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--persisted", help="directory of tool results the client saved to files (their full text is added)")
    ap.add_argument("--sanitizer", default=str(Path(__file__).resolve().parents[4] / "protocols/tools/public_sanitize.py"))
    ap.add_argument("--alias", action="append", default=[], help="LOCAL_PREFIX=PLACEHOLDER, applied after the sanitizer")
    a = ap.parse_args()

    san = load_sanitizer(a.sanitizer)
    raw = Path(a.stream).read_bytes()
    recs = [json.loads(l) for l in raw.decode("utf-8").splitlines() if l.strip()]
    meta = json.loads(Path(a.meta).read_text())
    init = next(r for r in recs if r.get("type") == "system" and r.get("subtype") == "init")
    result = next(r for r in recs if r.get("type") == "result")
    sid = init["session_id"]
    aliases = []
    for s in a.alias:
        k, v = s.split("=", 1)
        aliases.append((san(k), v))
    aliases.sort(key=lambda kv: -len(kv[0]))
    calls = {}

    def S(x):
        if isinstance(x, str):
            x = x.replace(sid, "<session>")
            x = san(x)
            for k, v in aliases:
                x = x.replace(k, v)
            x = re.sub(r"(?<![\w<])~(?=/)", "<home>", x)
            x = re.sub(r"\btoolu_[A-Za-z0-9]+\b", lambda m: calls.setdefault(m.group(0), f"call-{len(calls) + 1:03d}"), x)
            return x
        if isinstance(x, list):
            return [S(v) for v in x]
        if isinstance(x, dict):
            return {S(k): S(v) for k, v in x.items()}
        return x

    def cid(t):
        return calls.setdefault(t, f"call-{len(calls) + 1:03d}")

    def result_text(c):
        if isinstance(c, str):
            return c
        out = []
        for b in c or []:
            if b.get("type") == "text":
                out.append(b["text"])
            else:
                out.append(json.dumps(b, ensure_ascii=False))
        return "\n".join(out)

    persisted = {}
    if a.persisted and Path(a.persisted).is_dir():
        for f in sorted(Path(a.persisted).iterdir()):
            persisted[f.name] = f.read_text(errors="replace")

    rows, msg_turn, names, skipped = [], {}, {}, {}
    for r in recs:
        t = r.get("type")
        if t == "assistant":
            m = r["message"]
            turn = msg_turn.setdefault(m["id"], len(msg_turn) + 1)
            for b in m["content"]:
                row = dict(turn=turn, role="assistant", timestamp=r.get("timestamp"), model=m.get("model"))
                if b["type"] == "text":
                    row.update(type="text", content=b["text"])
                elif b["type"] == "thinking":
                    row.update(type="thinking", content=b.get("thinking", ""),
                               note="thinking text not stored by the client (empty; signature omitted)",
                               thinking_duration_ms=r.get("thinking_duration_ms"))
                elif b["type"] == "tool_use":
                    names[b["id"]] = (b["name"], turn)
                    row.update(type="tool_use", tool_name=b["name"], tool_input=b.get("input"), call_id=cid(b["id"]))
                else:
                    row.update(type=b["type"], content=json.dumps(b, ensure_ascii=False))
                rows.append(row)
        elif t == "user":
            c = r["message"]["content"]
            if isinstance(c, str):
                rows.append(dict(turn=0, role="user", type="prompt", content=c, timestamp=r.get("timestamp")))
                continue
            for b in c:
                if b.get("type") == "tool_result":
                    name, turn = names.get(b["tool_use_id"], (None, None))
                    txt = result_text(b.get("content"))
                    row = dict(turn=turn, role="tool", type="tool_result", tool_name=name, call_id=cid(b["tool_use_id"]),
                               tool_result=txt, is_error=bool(b.get("is_error")), timestamp=r.get("timestamp"))
                    for fn, full in persisted.items():
                        if fn in txt:
                            row["tool_result_persisted"] = {"file": fn, "text": full,
                                                            "note": "the client saved this result to a file and gave the "
                                                                    "model the notice above; the model read the file "
                                                                    "with later tool calls"}
                    rows.append(row)
                elif b.get("type") == "text":
                    rows.append(dict(turn=0, role="user", type="prompt", content=b["text"], timestamp=r.get("timestamp")))
        elif t == "system" and r.get("subtype") == "permission_denied":
            rows.append(dict(turn=None, role="system", type="permission_denied",
                             content=json.dumps({k: v for k, v in r.items() if k not in ("uuid", "session_id", "type", "subtype")},
                                                ensure_ascii=False),
                             timestamp=r.get("timestamp")))
        elif t not in ("system", "result") or (t == "system" and r.get("subtype") != "init"):
            key = t if t != "system" else f"system/{r.get('subtype')}"
            skipped[key] = skipped.get(key, 0) + 1
    # the prompt: stream-json does not echo it; it is the argument of the run (meta.prompt_file)
    prompt = Path(meta["prompt_file"]).read_text().rstrip("\n")   # the shell's "$(cat PROMPT.txt)" drops trailing newlines
    if not any(r["type"] == "prompt" for r in rows):
        rows.insert(0, dict(turn=0, role="user", type="prompt", content=prompt, timestamp=meta.get("started_utc")))
    for i, r in enumerate(rows, 1):
        r["seq"] = i
    ts = [r["timestamp"] for r in rows if r.get("timestamp")]
    models = sorted({r["model"] for r in rows if r.get("model")})
    mu = result.get("modelUsage", {})
    usage = result.get("usage", {})
    n_tool = sum(1 for r in rows if r["type"] == "tool_use")
    by_tool = {}
    for r in rows:
        if r["type"] == "tool_use":
            by_tool[r["tool_name"]] = by_tool.get(r["tool_name"], 0) + 1
    header = {
        "role": "header",
        "title": meta["title"],
        "assessment": meta["assessment"],
        "model_identifier": init.get("model"),
        "model_identifiers_in_messages": models,
        "model_usage": {k: {kk: v.get(kk) for kk in ("inputTokens", "outputTokens", "cacheReadInputTokens",
                                                      "cacheCreationInputTokens", "costUSD", "provider")} for k, v in mu.items()},
        "generation_dates_utc": {"session_started": meta.get("started_utc"), "first_record": ts[0], "last_record": ts[-1],
                                 "session_finished": meta.get("finished_utc")},
        "client": {"name": "Claude Code CLI (headless, claude -p)", "version": init.get("claude_code_version"),
                   "output_format": "stream-json --verbose", "permission_mode": init.get("permissionMode")},
        "command": meta["command"],
        "mcp_server": meta["mcp_server"],
        "mcp_servers_connected": [s.get("name") for s in init.get("mcp_servers", [])],
        "allowed_tools": meta["allowed_tools"],
        "tools_available_at_init": init.get("tools"),
        "prompt": prompt,
        "totals": {"turns_reported_by_client": result.get("num_turns"), "assistant_messages": len(msg_turn),
                   "tool_calls": n_tool, "tool_calls_by_name": dict(sorted(by_tool.items())),
                   "cost_usd": result.get("total_cost_usd"), "duration_ms": result.get("duration_ms"),
                   "duration_api_ms": result.get("duration_api_ms"),
                   "tokens": {k: usage.get(k) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens",
                                                        "cache_creation_input_tokens")},
                   "permission_denials": len(result.get("permission_denials") or []),
                   "is_error": result.get("is_error"), "stop_reason": result.get("stop_reason")},
        "records_left_out": skipped,
        "source": {"transcript": "stream-json output of the client (session.jsonl in the run directory)",
                   "transcript_sha256": hashlib.sha256(raw).hexdigest(),
                   "prompt_sha256": hashlib.sha256(Path(meta["prompt_file"]).read_bytes()).hexdigest(),
                   "persisted_tool_results": {fn: hashlib.sha256(t.encode()).hexdigest() for fn, t in persisted.items()},
                   "note": "sha256 of the unsanitized local originals (kept privately); this log is their sanitized rendering"},
        "sanitization": "protocols/tools/public_sanitize.py rules (home paths -> ~, user names -> <user>, host names -> "
                        "machine labels, session ids -> <session>), then the local directories named below -> "
                        "placeholders, then any remaining home-relative path (tilde, slash) -> <home>/; API/client ids dropped, "
                        "tool-use ids renumbered; the prompt is sanitized by the same rules (its local original is pinned by "
                        "source.prompt_sha256)",
        "placeholders": meta.get("placeholders", {}),
        "notes": meta.get("notes", []),
        "final_result_text": result.get("result"),
        "permission_denials": result.get("permission_denials"),
    }
    header = S(header)
    rows = [S(r) for r in rows]
    keys = ["seq", "turn", "role", "type", "content", "tool_name", "tool_input", "tool_result", "call_id", "is_error",
            "timestamp", "model"]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    with open(out / "agent_log.jsonl", "w") as f:
        f.write(json.dumps(header, ensure_ascii=False) + "\n")
        for r in rows:
            o = {k: r.get(k) for k in keys}
            o.update({k: v for k, v in r.items() if k not in keys})
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    (out / "agent_log_header.json").write_text(json.dumps(header, indent=1, ensure_ascii=False) + "\n")
    (out / "agent_log.md").write_text(render_md(header, rows))
    print(out, len(rows), "records")


def fence(s, lang=""):
    n = 3
    while "`" * n in s:
        n += 1
    return f"{'`' * n}{lang}\n{s.rstrip()}\n{'`' * n}\n"


def render_md(h, rows):
    T = h["totals"]; G = h["generation_dates_utc"]; C = h["client"]; M = h["mcp_server"]
    L = [f"# {h['title']}\n",
         "Log of the large-language-model inference used in the study: the exact prompt, every model message, every tool "
         "call with its input and every tool result returned to the model, in order. Machine-readable copy: "
         "`agent_log.jsonl` (line 1 is this header). Sanitized for publication (see Sanitization).\n",
         "## Header\n",
         "| field | value |", "|---|---|",
         f"| Model identifier | `{h['model_identifier']}` (every assistant message: {', '.join('`%s`' % m for m in h['model_identifiers_in_messages'])}) |",
         f"| Generation date (UTC) | {G['session_started']} to {G['session_finished']} (records {G['first_record']} to {G['last_record']}) |",
         f"| Client | {C['name']}, version {C['version']}; output {C['output_format']}; permission mode {C['permission_mode']} |",
         f"| MCP server | {M['name']} {M['version']}, {M['source']} |",
         f"| Assessment | {h['assessment']} |",
         f"| Command | `{h['command']}` |",
         f"| Allowed tools | {h['allowed_tools']} |",
         f"| Turns (client) | {T['turns_reported_by_client']} ({T['assistant_messages']} assistant messages, {T['tool_calls']} tool calls) |",
         f"| Cost | US${T['cost_usd']:.6f} (client-reported, list price) |",
         f"| Duration | {T['duration_ms'] / 1000:.0f} s wall, {T['duration_api_ms'] / 1000:.0f} s in API calls |",
         f"| Tokens | input {T['tokens']['input_tokens']}, output {T['tokens']['output_tokens']}, cache read {T['tokens']['cache_read_input_tokens']}, cache write {T['tokens']['cache_creation_input_tokens']} |",
         f"| Tool calls by name | {', '.join(f'{k} {v}' for k, v in T['tool_calls_by_name'].items())} |",
         f"| Permission denials | {T['permission_denials']} |",
         f"| Transcript sha256 (local original) | `{h['source']['transcript_sha256']}` |",
         "",
         "Tools available to the model at start (client init record): " + ", ".join(f"`{t}`" for t in h["tools_available_at_init"]) + ".\n"]
    if h.get("notes"):
        L.append("Notes:\n")
        L += [f"- {n}" for n in h["notes"]]
        L.append("")
    if h.get("placeholders"):
        L.append("Placeholders used in this log:\n")
        L += [f"- `{k}`: {v}" for k, v in h["placeholders"].items()]
        L.append("")
    L.append(f"Sanitization: {h['sanitization']}. Left out (not model inputs or outputs): "
             + ", ".join(f"{k} {v}" for k, v in h["records_left_out"].items()) + ".\n")
    L.append("## Prompt (exact)\n")
    L.append(fence(h["prompt"], "text"))
    L.append("## Transcript\n")
    cur = None
    for r in rows:
        if r["type"] == "prompt":
            continue
        if r["role"] == "assistant" and r["turn"] != cur:
            cur = r["turn"]
            L.append(f"### Turn {cur} ({r.get('timestamp')}, `{r.get('model')}`)\n")
        if r["type"] == "text":
            L.append("**Assistant:**\n")
            L.append(r["content"].rstrip() + "\n")
        elif r["type"] == "thinking":
            L.append(f"*Thinking block (text not stored by the client; {r.get('thinking_duration_ms')} ms).*\n")
        elif r["type"] == "tool_use":
            L.append(f"**Tool call {r['call_id']}: `{r['tool_name']}`**\n")
            L.append(fence(json.dumps(r["tool_input"], indent=1, ensure_ascii=False), "json"))
        elif r["type"] == "tool_result":
            err = " (error)" if r.get("is_error") else ""
            L.append(f"**Tool result {r['call_id']}{err}** ({r.get('timestamp')})\n")
            L.append(fence(r["tool_result"] or ""))
            if r.get("tool_result_persisted"):
                p = r["tool_result_persisted"]
                L.append(f"<details><summary>Full text of the saved result ({p['file']}; {len(p['text'])} characters)</summary>\n")
                L.append(fence(p["text"]))
                L.append("</details>\n")
        elif r["type"] == "permission_denied":
            L.append(f"**Client: permission denied** (time not recorded by the client)\n")
            L.append(fence(r["content"], "json"))
    L.append("## Final result (as returned by the client)\n")
    L.append(h["final_result_text"].rstrip() + "\n")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
