"""Minimal, stdlib-only loader for the YAML subset used by ORCHID protocol documents.

Why: the protocol tools must run with the Python standard library only (no PyYAML install). The protocol
files are therefore written in a small, regular subset of YAML 1.2, and this loader reads exactly that subset.
`validate.py --crosscheck-yaml PYTHON` compares the result with PyYAML from an existing interpreter.

Supported:
  * block mappings  `key: value`, `key:` + indented block; keys are plain or quoted scalars
  * block sequences `- item`, `- key: value` (mapping items), nested blocks
  * plain scalars (null/~, true/false, ints, floats, strings), single- and double-quoted scalars
  * block scalars `|` and `>` with optional chomping `-`/`+` (indentation auto-detected)
  * flow sequences `[a, b, "c"]` and flow mappings `{k: v, k2: [x]}` (nesting allowed, no multi-line flow)
  * comments (`#` after whitespace, or at line start)
Not supported (raises YamlError): anchors/aliases, tags, multi-document streams, complex keys, multi-line flow
collections, multi-line plain scalars.
"""
import re

__all__ = ["load", "loads", "YamlError"]


class YamlError(ValueError):
    pass


_INT = re.compile(r"^[-+]?(0|[1-9][0-9_]*)$")
_FLOAT = re.compile(r"^[-+]?(\.[0-9]+|[0-9][0-9_]*(\.[0-9]*)?)([eE][-+]?[0-9]+)?$")


def _scalar(tok, lineno):
    t = tok.strip()
    if t == "" or t in ("~", "null", "Null", "NULL"):
        return None
    if t in ("true", "True", "TRUE"):
        return True
    if t in ("false", "False", "FALSE"):
        return False
    if t[0] in "'\"":
        return _quoted(t, lineno)
    if t[0] in "[{":
        val, rest = _flow(t, 0, lineno)
        if rest.strip():
            raise YamlError(f"line {lineno}: trailing text after flow collection: {rest!r}")
        return val
    if t[0] in "&*!|>%@`":
        raise YamlError(f"line {lineno}: unsupported YAML feature in {t!r}")
    if _INT.match(t):
        return int(t.replace("_", ""))
    if _FLOAT.match(t) and any(c.isdigit() for c in t):
        return float(t.replace("_", ""))
    if t in (".inf", "+.inf"):
        return float("inf")
    if t == "-.inf":
        return float("-inf")
    return t


def _quoted(t, lineno):
    q = t[0]
    if t[-1] != q or len(t) < 2:
        raise YamlError(f"line {lineno}: unterminated quoted scalar {t!r}")
    body = t[1:-1]
    if q == "'":
        return body.replace("''", "'")
    out, i = [], 0
    esc = {"n": "\n", "t": "\t", '"': '"', "\\": "\\", "/": "/", "0": "\0", "r": "\r"}
    while i < len(body):
        c = body[i]
        if c == "\\":
            n = body[i + 1]
            if n in esc:
                out.append(esc[n]); i += 2
            elif n == "u":
                out.append(chr(int(body[i + 2:i + 6], 16))); i += 6
            else:
                raise YamlError(f"line {lineno}: unsupported escape \\{n}")
        else:
            out.append(c); i += 1
    return "".join(out)


def _flow(s, i, lineno):
    """Parse a flow collection starting at s[i] ('[' or '{'); return (value, remaining string)."""
    def skip(j):
        while j < len(s) and s[j] in " \t":
            j += 1
        return j

    def atom(j, stops):
        j = skip(j)
        if j < len(s) and s[j] in "[{":
            v, rest = _flow(s, j, lineno)
            return v, len(s) - len(rest)
        if j < len(s) and s[j] in "'\"":
            q = s[j]; k = j + 1
            while k < len(s):
                if s[k] == q:
                    if q == "'" and k + 1 < len(s) and s[k + 1] == "'":
                        k += 2; continue
                    if q == '"' and s[k - 1] == "\\" and s[k - 2] != "\\":
                        k += 1; continue
                    break
                k += 1
            return _quoted(s[j:k + 1], lineno), k + 1
        k = j
        while k < len(s) and s[k] not in stops:
            k += 1
        return _scalar(s[j:k], lineno), k

    i = skip(i)
    if s[i] == "[":
        out = []; i += 1
        while True:
            i = skip(i)
            if i >= len(s):
                raise YamlError(f"line {lineno}: unterminated flow sequence")
            if s[i] == "]":
                return out, s[i + 1:]
            v, i = atom(i, ",]")
            out.append(v); i = skip(i)
            if i < len(s) and s[i] == ",":
                i += 1
    if s[i] == "{":
        out = {}; i += 1
        while True:
            i = skip(i)
            if i >= len(s):
                raise YamlError(f"line {lineno}: unterminated flow mapping")
            if s[i] == "}":
                return out, s[i + 1:]
            k, i = atom(i, ":,}")
            i = skip(i)
            if i >= len(s) or s[i] != ":":
                raise YamlError(f"line {lineno}: expected ':' in flow mapping")
            v, i = atom(i + 1, ",}")
            out[str(k) if not isinstance(k, str) else k] = v
            i = skip(i)
            if i < len(s) and s[i] == ",":
                i += 1
    raise YamlError(f"line {lineno}: not a flow collection")


def _strip_comment(line):
    """Remove a trailing comment that is outside quotes and flow brackets."""
    q = None
    skip = False
    for i, c in enumerate(line):
        if skip:
            skip = False
            continue
        if q:
            if c == q == "'" and i + 1 < len(line) and line[i + 1] == "'":
                skip = True
            elif c == q == '"' and line[i - 1] == "\\":
                pass
            elif c == q:
                q = None
            continue
        if c in "'\"" and (i == 0 or line[i - 1] in " \t[{,:-"):
            q = c
        elif c == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i].rstrip()
    return line.rstrip()


class _Lines:
    def __init__(self, text):
        self.raw = text.split("\n")
        self.i = 0

    def peek(self):
        """Next significant line as (indent, content, lineno) or None."""
        while self.i < len(self.raw):
            line = self.raw[self.i]
            if "\t" in line[:len(line) - len(line.lstrip())]:
                raise YamlError(f"line {self.i + 1}: tab indentation")
            s = _strip_comment(line)
            if s.strip() == "" or s.strip() in ("---",):
                self.i += 1; continue
            if s.strip() == "...":
                self.i = len(self.raw); return None
            return len(s) - len(s.lstrip(" ")), s.strip(), self.i + 1
        return None


_KEY = re.compile(r"""^(?P<key>"(?:[^"\\]|\\.)*"|'(?:[^']|'')*'|[^\s#'"\[\]{},:][^:#]*?)\s*:(?:\s+(?P<rest>.*))?$""")


def _split_key(content):
    m = _KEY.match(content)
    if not m:
        return None
    k = m.group("key")
    if k[0] in "'\"":
        k = _quoted(k, 0)
    return k, (m.group("rest") or "")


def _block_scalar(L, indicator, parent_indent, lineno):
    style, chomp = indicator[0], indicator[1:].strip()
    if chomp not in ("", "-", "+"):
        raise YamlError(f"line {lineno}: unsupported block scalar header {indicator!r}")
    lines, ind = [], None
    while L.i < len(L.raw):
        line = L.raw[L.i]
        if line.strip() == "":
            lines.append(""); L.i += 1; continue
        cur = len(line) - len(line.lstrip(" "))
        if ind is None:
            if cur <= parent_indent:
                break
            ind = cur
        if cur < ind:
            break
        lines.append(line[ind:]); L.i += 1
    while lines and lines[-1] == "" and chomp != "+":
        lines.pop()
    if style == "|":
        text = "\n".join(lines)
    else:
        paras, buf = [], []
        for ln in lines:
            if ln == "":
                paras.append(" ".join(buf)); buf = []
            elif ln.startswith(" "):
                if buf:
                    paras.append(" ".join(buf)); buf = []
                paras.append(ln)
            else:
                buf.append(ln)
        paras.append(" ".join(buf))
        text = "\n".join(paras)
    return text + ("\n" if chomp != "-" and text else "")


def _value_after_colon(L, rest, indent, lineno):
    if rest.startswith(("|", ">")):
        return _block_scalar(L, rest, indent, lineno)
    if rest.strip() == "":
        nxt = L.peek()
        if nxt is None:
            return None
        nind, ncont, _ = nxt
        if nind > indent or (nind == indent and ncont.startswith("- ") or (nind == indent and ncont == "-")):
            return _block(L, nind)
        return None
    return _scalar(rest, lineno)


def _block(L, indent):
    first = L.peek()
    if first is None:
        return None
    _, content, _ = first
    if content == "-" or content.startswith("- "):
        return _seq(L, indent)
    return _map(L, indent)


def _map(L, indent):
    out = {}
    while True:
        p = L.peek()
        if p is None:
            return out
        ind, content, lineno = p
        if ind < indent:
            return out
        if ind > indent:
            raise YamlError(f"line {lineno}: unexpected indentation")
        if content.startswith("- ") or content == "-":
            return out
        kv = _split_key(content)
        if kv is None:
            raise YamlError(f"line {lineno}: expected 'key: value', got {content!r}")
        k, rest = kv
        if k in out:
            raise YamlError(f"line {lineno}: duplicate key {k!r}")
        L.i += 1
        out[k] = _value_after_colon(L, rest, indent, lineno)


def _seq(L, indent):
    out = []
    while True:
        p = L.peek()
        if p is None:
            return out
        ind, content, lineno = p
        if ind < indent or not (content.startswith("- ") or content == "-"):
            return out
        if ind > indent:
            raise YamlError(f"line {lineno}: unexpected indentation in sequence")
        item = content[1:].lstrip(" ")
        item_indent = ind + (len(content) - len(item))
        if item == "":
            L.i += 1
            nxt = L.peek()
            out.append(_block(L, nxt[0]) if nxt and nxt[0] > ind else None)
            continue
        kv = _split_key(item) if not item.startswith(("'", '"', "[", "{")) or _split_key(item) else None
        if kv is not None and not item.startswith(("[", "{")):
            # mapping item: rewrite the current line as a mapping line at item_indent
            L.raw[L.i] = " " * item_indent + item
            out.append(_map(L, item_indent))
        elif item.startswith(("|", ">")):
            L.i += 1
            out.append(_block_scalar(L, item, ind, lineno))
        else:
            L.i += 1
            out.append(_scalar(item, lineno))


def loads(text):
    L = _Lines(text)
    p = L.peek()
    if p is None:
        return None
    val = _block(L, p[0])
    q = L.peek()
    if q is not None:
        raise YamlError(f"line {q[2]}: unexpected content {q[1]!r}")
    return val


def load(path):
    with open(path, encoding="utf-8") as f:
        return loads(f.read())


if __name__ == "__main__":
    import json, sys
    print(json.dumps(load(sys.argv[1]), indent=1, ensure_ascii=False))
