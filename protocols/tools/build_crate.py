#!/usr/bin/env python3
"""Build a Workflow Run RO-Crate for one specific protocol, with a human-readable HTML and Markdown rendering.

  python3 tools/build_crate.py specific/<id>@<version>.yaml crates/<id> [--addenda] [--decisions] [--pinned-evidence] [--substitutes] [--reproduce-tree] [--public]
      (standard library only; --pinned-evidence copies only the evidence files of the pinned bundle and the pinned intake; --substitutes
       replaces the originals listed in the addenda manifests' crate_substitutes by their new versions; --reproduce-tree copies the
       reproduce records with their subfolders and adds run cards that execute this version outside its run sequence; --addenda also copies
                                                                         the assessments/<id>/addendum-*/code/ trees named in code;
                                                                         --decisions emits each decision row as a ChooseAction;
       --public (first used for crni-paper-fit-step4c-b@1.0.4, 7 Nov): every file is copied as its sanitized copy
       (tools/public_sanitize.py: home paths as <home>/, hosts as machine labels, no user, scratch or session names), file and
       directory names with host labels mapped the same way, the metadata and preview too; PUBLIC_SUBSTITUTES.json in the
       crate maps each changed file's original sha256 to its sanitized sha256, and the entity is prov:wasDerivedFrom the original)
  python3 tools/build_crate.py --render general/<file>.yaml OUT.md OUT.html  (rendering only)

Crate contents (files copied in, each with sha256): the specific and general protocol YAML, their Markdown and HTML
renderings, the run cards of the run sequence, the frozen dashboard (HTML + data) and its static figures when present,
the artifact (TDB), the schema family, and ro-crate-metadata.json + ro-crate-preview.html.
Not copied: campaign inputs. They appear as contextual entities with path and sha256; restricted ones carry
conditionsOfAccess and are never copied.
JSON-LD: RO-Crate 1.1; root Dataset conformsTo the Process Run Crate and Workflow Run Crate profiles 0.5; mainEntity = the
specific protocol as File + SoftwareSourceCode + ComputationalWorkflow + HowTo with HowToSection/HowToStep entities;
one CreateAction per run card (object = inputs, result = outputs, instrument = the protocol); PROV-O terms
(prov:wasGeneratedBy, prov:hadPlan, prov:wasDerivedFrom) added beside the schema.org ones.
"""
import html
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orchidproto as op  # noqa: E402
import public_sanitize as psan  # noqa: E402
import frozen  # noqa: E402

ROOT = op.ROOT
CTX = ["https://w3id.org/ro/crate/1.1/context",
       {"sha256": "http://schema.org/sha256", "prov": "http://www.w3.org/ns/prov#",
        "wasGeneratedBy": {"@id": "prov:wasGeneratedBy", "@type": "@id"}, "hadPlan": {"@id": "prov:hadPlan", "@type": "@id"},
        "wasDerivedFrom": {"@id": "prov:wasDerivedFrom", "@type": "@id"}, "kind": "https://orchid-project.org/terms#stepKind",
        "decisionRule": "https://orchid-project.org/terms#decisionRule", "decidedBy": "https://orchid-project.org/terms#decidedBy",
        "storageClass": "https://orchid-project.org/terms#storageClass"}]
PROFILES = [{"@id": "https://w3id.org/ro/wfrun/process/0.5"}, {"@id": "https://w3id.org/ro/wfrun/workflow/0.5"}]


# ------------------------------------------------------------------------------------------- rendering
def _fr(r):
    return f"`{r['path']}` (sha256 `{r['sha256'][:16]}…`, {r['storage_class']})" if isinstance(r, dict) and r.get("sha256") else (f"`{r['path']}`" if isinstance(r, dict) else str(r))


def render_md(d, general=None):
    L = [f"# {d['title']}", "", f"`{d['id']}@{d['version']}` · {d['type'].replace('_', ' ')} · status **{d['status']}** · licence {d.get('licence', '')}", ""]
    if d.get("status_note"):
        L += [f"> {d['status_note'].strip()}", ""]
    if d.get("purpose"):
        L += ["## Purpose", "", d["purpose"].strip(), ""]
    if d.get("instantiates"):
        L += ["## Instantiates", ""] + [f"- `{i['protocol']}` — {_fr(i['file'])}" for i in d["instantiates"]] + [""]
    if d.get("artifact"):
        a = d["artifact"]; L += ["## Artifact", "", f"- {a['kind']}: {_fr(a['file'])}", f"- produced_by `{a['produced_by']}`", ""]
    if d.get("inputs"):
        L += ["## Inputs", ""]
        for i in d["inputs"]:
            L.append(f"- **{i['id']}** — {i['name']} ({i.get('storage_class', '')})")
            for f in i.get("files", []):
                L.append(f"  - {_fr(f)}" + (f" — {f['role']}" if f.get("role") else ""))
        L.append("")
    if d.get("code"):
        L += ["## Code", ""] + [f"- **{c['id']}** ({c['kind']}): {c.get('repository') or c.get('path', '')}" + (f" @ `{c['commit']}`" if c.get("commit") else "") + (f" — entry points: {', '.join(c.get('entry_points', []))}" if c.get("entry_points") else "") for c in d["code"]] + [""]
    if d.get("environment"):
        L += ["## Environment", ""] + [f"- **{e['id']}** ({e['kind']}): {e.get('path') or e.get('image', '')}; " + ", ".join(f"{k} {v}" for k, v in (e.get("packages") or {}).items()) for e in d["environment"]] + [""]
    if d.get("parameters"):
        L += ["## Parameters", "", "| parameter | default | unit | frozen | meaning | source |", "|---|---|---|---|---|---|"]
        for k, p in d["parameters"].items():
            L.append(f"| `{k}` | {json.dumps(p['default'], ensure_ascii=False)} | {p.get('unit', '')} | {'yes' if p.get('frozen') else ''} | {p['text']} | {p.get('source', '')} |")
        L.append("")
    if d.get("overrides"):
        L += ["## Overrides of the general protocol", "", "| parameter | value here | general default | conforms | reason | source |", "|---|---|---|---|---|---|"]
        L += [f"| {o['parameter']} | {o['value']} | {o.get('general_default', '')} | {'yes' if o.get('conforms', True) else '**no**'} | {o['reason']} | {o['source']} |" for o in d["overrides"]] + [""]
    if d.get("evidence_selection"):
        e = d["evidence_selection"]; L += ["## Evidence selection", "", f"- ORCHID: {e['orchid'].get('repository')} @ `{e['orchid'].get('commit')}`; query: {e['orchid'].get('query', '')}",
                                          f"- manifest: {_fr(e['manifest'])}", f"- evidence digest `{e.get('result_sha256', '')}` from {_fr(e.get('digest_source', {}))}", ""]
        for key, title in (("exclusions", "Exclusions"), ("interpretations", "Labelled interpretations"), ("single_reader_flags", "Single-reader records")):
            if e.get(key):
                L += [f"**{title}**", ""] + [f"- {x['what']}" + (f" ({', '.join(x['record_ids'])})" if x.get("record_ids") else "") + f": {x.get('reason') or x.get('label') or x.get('note')}" + (f" — {x['source']}" if x.get("source") else "") for x in e[key]] + [""]
    for sec in d.get("sections", []) or []:
        L += [f"## {sec['name']}", ""] + ([sec["text"].strip(), ""] if sec.get("text") else []) + ([f"*Rationale: {sec['rationale']}*", ""] if sec.get("rationale") else [])
        for n, s in enumerate(sec["steps"], 1):
            L += [f"### {n}. {s['name']} (`{s['id']}`, {s['kind']})", "", s["text"].strip(), ""]
            if s.get("supply"):
                L.append("- **Inputs:** " + ", ".join(f"`{x}`" for x in s["supply"]))
            t = s["tool"]; L.append(f"- **Tool:** {t['name']}" + (f" — `{t['command']}`" if t.get("command") else "") + (f" ({t['note']})" if t.get("note") else ""))
            L.append("- **Results:** " + "; ".join(f"`{r['id']}` {r['name']}" + (f" [checks: {', '.join(r['checks'])}]" if r.get("checks") else "") for r in s["result"]))
            if s.get("decision_rule"):
                L.append(f"- **Decision rule:** {s['decision_rule']} — **decided by** {s['decided_by']}")
            for tl in s.get("tolerances", []):
                L.append(f"- **Tolerance:** {tl['quantity']}: {tl['rule']}" + (f" {tl['value']} {tl.get('unit', '')}" if tl.get("value") is not None else ""))
            if s.get("gates"):
                L.append("- **Gates:** " + ", ".join(s["gates"]))
            if s.get("rationale"):
                L.append(f"- *Rationale:* {s['rationale']}")
            L.append("")
    for key, title in (("gates", "Gates (hard)"), ("ranking_criteria", "Ranking criteria (soft)")):
        if d.get(key):
            L += [f"## {title}", ""] + [f"- **{g['id']}** — {g['text']}" for g in d[key]] + [""]
    if d.get("run_sequence"):
        L += ["## Run sequence (failed attempts and side branches kept)", "", "| run | step | status | starts | pick | from | summary |", "|---|---|---|---|---|---|---|"]
        L += [f"| `{r['run_id']}` | `{r['step']}` | {r['status']} | {r.get('starts', '')} | {r.get('pick', '')} | {r.get('start_from', '')} | {r.get('summary', '')} |" for r in d["run_sequence"]] + [""]
    if d.get("acceptance_target"):
        a = d["acceptance_target"]; L += ["## Acceptance target", "", a["text"].strip(), ""] + [f"- {t['quantity']}: {t['rule']}" + (f" {t['value']} {t.get('unit', '')}" if t.get("value") is not None else "") for t in a["tolerances"]] + [""]
    if d.get("tolerances"):
        L += ["## Tolerances", ""] + [f"- {t['quantity']}: {t['rule']}" + (f" {t['value']} {t.get('unit', '')}" if t.get("value") is not None else "") + (f" ({t['note']})" if t.get("note") else "") for t in d["tolerances"]] + [""]
    if d.get("reproduce"):
        r = d["reproduce"]; L += ["## Reproduce", "", r["command"], "", "Expected byte-identical: " + "; ".join(r["byte_identical_expected"]), "", "Not reproducible byte for byte:", ""] + [f"- {x}" for x in r["not_reproducible"]] + [""]
    if d.get("decisions"):
        L += ["## Decisions", "", "| date | who | decision | why | source |", "|---|---|---|---|---|"] + [f"| {x['date']} | {x['who']} | {x['decision']}" + (f" — “{x['quote']}”" if x.get("quote") else "") + f" | {x['why']} | {x['source']} |" for x in d["decisions"]] + [""]
    if d.get("limitations"):
        L += ["## Limitations", ""] + [f"- {x}" for x in d["limitations"]] + [""]
    if d.get("open_questions"):
        L += ["## Open questions", "", "See OPEN_QUESTIONS.md: " + ", ".join(d["open_questions"]), ""]
    if d.get("citations"):
        L += ["## Citations", ""] + [f"- {c}" for c in d["citations"]] + [""]
    return "\n".join(L)


def md_to_html(md, title):
    """Small Markdown subset -> HTML (headings, lists, tables, quotes, code spans, bold, italics)."""
    import re
    pal = json.loads((Path(__file__).parent / "palette.json").read_text())
    u, k = pal["ui"]["light"], pal["ui"]["dark"]

    def inline(s):
        s = html.escape(s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
        s = re.sub(r"(?<![*\w])\*([^*]+)\*(?!\w)", r"<i>\1</i>", s)
        return s
    out, lines, i = [], md.split("\n"), 0
    while i < len(lines):
        l = lines[i]
        if l.startswith("#"):
            n = len(l) - len(l.lstrip("#")); out.append(f"<h{n}>{inline(l[n:].strip())}</h{n}>")
        elif l.startswith("|") and i + 1 < len(lines) and lines[i + 1].startswith("|---"):
            hd = [c.strip() for c in l.strip("|").split("|")]; rows = []; i += 2
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip("|").split("|")]); i += 1
            out.append("<div class=tw><table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in hd) + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table></div>"); continue
        elif l.startswith("- ") or l.startswith("  - "):
            items = []
            while i < len(lines) and (lines[i].startswith("- ") or lines[i].startswith("  - ")):
                items.append(("<li class=sub>" if lines[i].startswith("  ") else "<li>") + inline(lines[i].strip()[2:]) + "</li>"); i += 1
            out.append("<ul>" + "".join(items) + "</ul>"); continue
        elif l.startswith("> "):
            out.append(f"<blockquote>{inline(l[2:])}</blockquote>")
        elif l.strip():
            out.append(f"<p>{inline(l)}</p>")
        i += 1
    css = (f":root{{--bg:{u['bg']};--card:{u['card']};--fg:{u['fg']};--muted:{u['muted']};--line:{u['line']};--accent:{u['accent']};--accent2:{u['accent2']}}}"
           f"@media (prefers-color-scheme:dark){{:root{{--bg:{k['bg']};--card:{k['card']};--fg:{k['fg']};--muted:{k['muted']};--line:{k['line']};--accent:{k['accent']};--accent2:{k['accent2']}}}}}"
           "body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 'IBM Plex Sans',system-ui,-apple-system,'Segoe UI',sans-serif}main{max-width:980px;margin:auto;padding:16px}"
           "h1{font-size:26px;line-height:1.25}h2{font-size:19px;border-bottom:1px solid var(--line);padding-bottom:4px;margin-top:28px}h3{font-size:15.5px;margin-top:20px}"
           "code{font-family:ui-monospace,Menlo,monospace;font-size:12.5px;overflow-wrap:anywhere}blockquote{background:var(--accent2);border-left:4px solid var(--accent);margin:0;padding:10px 14px;border-radius:6px}"
           ".tw{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px;min-width:600px}th,td{border-bottom:1px solid var(--line);padding:5px;text-align:left;vertical-align:top}th{background:var(--accent2)}"
           "li.sub{margin-left:18px;list-style:circle}a{color:var(--accent)}")
    return f"<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>{html.escape(title)}</title><style>{css}</style></head><body><main>{''.join(out)}</main></body></html>"


# ------------------------------------------------------------------------------------------- crate
def _refs(o):
    if isinstance(o, dict):
        if set(o) == {"@id"}:
            yield o
        else:
            for k, v in o.items():
                if k != "@id":
                    yield from _refs(v)
    elif isinstance(o, list):
        for v in o:
            yield from _refs(v)


def person_id(p):
    """RO-Crate Person @id: the ORCID URL when the maintainer has one (RO-Crate 1.1 recommends it), else a local #person- id."""
    return f"https://orcid.org/{p['orcid']}" if p.get("orcid") else "#person-" + p["name"].lower().replace(" ", "-")


def build(spec_path, out, addenda=False, decisions=False, pinned_evidence=False, substitutes=False, reproduce_tree=False, public=False):
    spec_path = Path(spec_path); out = Path(out)
    d = op.load_doc(spec_path)
    gen_path = op.expand(d["instantiates"][0]["file"]["path"]); g = op.load_doc(gen_path)
    out.mkdir(parents=True, exist_ok=True)
    for sub in ("protocol", "run_cards", "dashboard", "figures", "artifact", "schema"):
        (out / sub).mkdir(exist_ok=True)
    parts, graph = [], {}
    pub_rows, pub_binary = [], []

    def add_file(src, rel, types=("File",), **props):
        src = op.expand(src)
        if public:
            rel = psan.sanitize_path(rel)
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        raw = src.read_bytes()
        new, changed = psan.sanitize_bytes(raw, dst.suffix) if public else (raw, False)
        if public and src.resolve() == dst.resolve():
            dst.write_bytes(new)   # a rendering this build generated inside the new crate, sanitized in place (the record itself is untouched)
        else:
            frozen.write(dst, new, "build_crate.py")   # refuses a frozen file whose content would change
        if public:
            if changed:
                try:
                    orig = str(src.resolve().relative_to(ROOT.parent.resolve()))
                except ValueError:
                    orig = op.tilde(src)
                generated = src.resolve() == dst.resolve()
                pub_rows.append({"crate_path": rel, "original": psan.sanitize_text(orig) if not generated else "(generated by tools/build_crate.py)",
                                 "original_sha256": psan.sha(raw), "sanitized_sha256": psan.sha(new)})
                if not generated:
                    oid = f"#original-{psan.sha(raw)[:16]}"
                    wdf = props.get("wasDerivedFrom")
                    props = {**props, "wasDerivedFrom": ([wdf] if isinstance(wdf, dict) else (wdf or [])) + [{"@id": oid}]}
                    props["wasDerivedFrom"] = props["wasDerivedFrom"][0] if len(props["wasDerivedFrom"]) == 1 else props["wasDerivedFrom"]
                    graph.setdefault(oid, {"@id": oid, "@type": "CreativeWork", "name": psan.sanitize_text(orig), "sha256": psan.sha(raw), "storageClass": "local",
                                           "description": "original record (kept in the repository, not copied into this crate); this crate holds its public copy "
                                                          "(tools/public_sanitize.py; PUBLIC_SUBSTITUTES.json)"})
            elif changed is None:
                pub_binary.append(rel)
        e = {"@id": rel, "@type": list(types) if len(types) > 1 else types[0], "name": Path(rel).name, "sha256": op.sha256_file(dst),
             "contentSize": dst.stat().st_size, "encodingFormat": {".yaml": "application/yaml", ".json": "application/json", ".html": "text/html", ".md": "text/markdown",
                                                                  ".tdb": "text/plain", ".pdf": "application/pdf", ".png": "image/png"}.get(dst.suffix, "application/octet-stream")}
        e.update(props); graph[rel] = e; parts.append({"@id": rel})
        return rel

    sp_rel = add_file(spec_path, f"protocol/{spec_path.name}", ("File", "SoftwareSourceCode", "ComputationalWorkflow", "HowTo"),
                      name=d["title"], version=d["version"], identifier=f"{d['id']}@{d['version']}", programmingLanguage={"@id": "#orchid-protocol-yaml"},
                      license={"@id": "https://creativecommons.org/licenses/by/4.0/"}, creativeWorkStatus=d["status"])
    gp_rel = add_file(gen_path, f"protocol/{gen_path.name}", ("File", "SoftwareSourceCode", "HowTo"), name=g["title"], version=g["version"],
                      identifier=f"{g['id']}@{g['version']}", programmingLanguage={"@id": "#orchid-protocol-yaml"})
    graph[sp_rel]["isBasedOn"] = {"@id": gp_rel}
    for doc, rel in ((d, sp_rel), (g, gp_rel)):
        stem = Path(rel).stem
        md = render_md(doc); frozen.write(out / f"protocol/{stem}.md", md, "build_crate.py"); frozen.write(out / f"protocol/{stem}.html", md_to_html(md, doc["title"]), "build_crate.py")
        add_file(out / f"protocol/{stem}.md", f"protocol/{stem}.md", about={"@id": rel}, description="Markdown rendering")
        add_file(out / f"protocol/{stem}.html", f"protocol/{stem}.html", about={"@id": rel}, description="HTML rendering")
    # HowTo sections and steps (general protocol steps + the specific protocol's own)
    for doc, rel in ((g, gp_rel), (d, sp_rel)):
        secs = []
        for sec in doc.get("sections", []) or []:
            sid = f"#{doc['id']}-{sec['id']}"; steps = []
            for n, s in enumerate(sec["steps"], 1):
                stid = f"#{doc['id']}-step-{s['id']}"
                graph[stid] = {"@id": stid, "@type": "HowToStep", "position": n, "name": s["name"], "text": s["text"].strip(), "kind": s["kind"],
                               "tool": {"@id": f"{stid}-tool"}, "supply": [{"@id": f"{stid}-in-{k}"} for k in range(len(s["supply"]))],
                               "result": [r["name"] for r in s["result"]]}
                graph[f"{stid}-tool"] = {"@id": f"{stid}-tool", "@type": "HowToTool", "name": s["tool"]["name"], **({"description": s["tool"]["command"]} if s["tool"].get("command") else {})}
                for k, x in enumerate(s["supply"]):
                    graph[f"{stid}-in-{k}"] = {"@id": f"{stid}-in-{k}", "@type": "HowToSupply", "name": x}
                if s.get("decision_rule"):
                    graph[stid]["decisionRule"] = s["decision_rule"]; graph[stid]["decidedBy"] = s["decided_by"]
                steps.append({"@id": stid})
            graph[sid] = {"@id": sid, "@type": "HowToSection", "name": sec["name"], "step": steps}
            secs.append({"@id": sid})
        graph[rel]["step"] = secs
    # artifact
    a = d["artifact"]["file"]
    art_rel = add_file(a["path"], f"artifact/{Path(op.expand(a['path'])).name}", description=f"{d['artifact']['kind']} produced by {d['artifact']['produced_by']}",
                       wasGeneratedBy={"@id": "#run-overall"})
    # dashboard and figures
    if d.get("dashboard"):
        add_file(d["dashboard"]["html"]["path"], "dashboard/dashboard.html", description="frozen assessment dashboard (standalone)", about={"@id": art_rel})
        add_file(d["dashboard"]["data"]["path"], "dashboard/dashboard_data.json", description="assessment-results document (orchid-assessment-schema 1.0.0-draft)", about={"@id": art_rel},
                 conformsTo={"@id": "schema/assessment-results.schema.json"})
    figdir = ROOT / "figures" / d["id"]
    if figdir.exists():
        for f in sorted(figdir.iterdir()):
            add_file(f, f"figures/{f.name}", about={"@id": art_rel})
    # code snapshot, evidence bundle, released TDB, intake, statement and reproduce reports (derived facts only)
    A = ROOT.parent / "assessments" / d["id"]
    REPO = ROOT.parent
    # --substitutes (first used for crni-paper-fit-step4c-b@1.0.4): the code addenda named in the spec list crate_substitutes in
    # their MANIFEST.json ({original, replacement, reason}); an original is left out of the crate and its replacement (a new
    # version, e.g. with a home path written as <home>/) is copied where it lives, marked wasDerivedFrom the original's sha256
    subst, repl = {}, {}
    if substitutes:
        for c in d.get("code") or []:
            mf = REPO / str(c.get("path", "")) / "MANIFEST.json"
            if str(c.get("path", "")).startswith(f"assessments/{d['id']}/addendum-") and mf.exists():
                for s_ in json.loads(mf.read_text()).get("crate_substitutes", []):
                    if op.sha256_file(REPO / s_["original"]) != s_["original_sha256"] or op.sha256_file(REPO / s_["replacement"]) != s_["replacement_sha256"]:
                        sys.exit(f"crate substitute {s_['original']} -> {s_['replacement']}: sha256 differs from {mf}")
                    subst[str((REPO / s_["original"]).resolve())] = s_; repl[str((REPO / s_["replacement"]).resolve())] = s_
    skip = lambda f: str(Path(f).resolve()) in subst  # noqa: E731

    def add_tree_file(f, rel, **props):
        s_ = repl.get(str(Path(f).resolve()))
        if s_:
            props = {**props, "wasDerivedFrom": {"@id": f"#original-{s_['original_sha256'][:16]}"},
                     "description": (props.get("description", "") + f" (crate substitute for {s_['original']}: {s_['reason']})").strip()}
            graph[f"#original-{s_['original_sha256'][:16]}"] = {"@id": f"#original-{s_['original_sha256'][:16]}", "@type": "CreativeWork", "name": s_["original"],
                                                                "sha256": s_["original_sha256"], "storageClass": "local",
                                                                "description": "original record (kept in the repository, not copied into this crate)"}
        add_file(f, rel, **props)
    # --pinned-evidence: only the evidence files of the bundle the spec pins (evidence_selection.bundle.manifest) and that
    # manifest, and only the pinned intake manifest (with its README@V.md); earlier bundle versions stay in the repository
    pin_ev = pin_in = None
    if pinned_evidence:
        b_ = (d.get("evidence_selection") or {}).get("bundle") or {}
        mpath = op.expand(b_["manifest"]["path"]) if b_.get("manifest") else None
        if mpath is None or not mpath.exists():
            sys.exit("--pinned-evidence: the spec pins no evidence bundle manifest")
        pin_ev = {str((mpath.parent / f["path"]).resolve()) for f in json.loads(mpath.read_text())["files"]} | {str(mpath.resolve())}
        if b_.get("intake"):
            ip = op.expand(b_["intake"]["path"]).resolve()
            v_ = ip.stem.split("@")[1] if "@" in ip.stem else None
            pin_in = {str(ip)} | ({str(ip.parent / f"README@{v_}.md")} if v_ else {str(ip.parent / "README.md")})
    for sub in ("code", "evidence", "release", "intake"):
        if (A / sub).exists():
            for f in sorted(p for p in (A / sub).rglob("*") if p.is_file() and "__pycache__" not in str(p)):
                if skip(f) or (sub == "evidence" and pin_ev is not None and str(f.resolve()) not in pin_ev) or (sub == "intake" and pin_in is not None and str(f.resolve()) not in pin_in):
                    continue
                add_tree_file(f, f"assessment/{sub}/{f.relative_to(A / sub)}", about={"@id": art_rel})
    if addenda:  # --addenda: also the code addenda the specific protocol names in its code section (assessments/<id>/addendum-*/code/)
        for c in d.get("code") or []:
            pth = str(c.get("path", ""))
            if pth.startswith(f"assessments/{d['id']}/addendum-") and (ROOT.parent / pth).exists():
                base = ROOT.parent / pth
                for f in sorted(q for q in base.rglob("*") if q.is_file() and "__pycache__" not in str(q)):
                    if skip(f):
                        continue
                    add_tree_file(f, f"assessment/{base.parent.name}/code/{f.relative_to(base)}", about={"@id": art_rel})
    if (A / "DATA_STATEMENT.md").exists():
        add_file(A / "DATA_STATEMENT.md", "assessment/DATA_STATEMENT.md", about={"@id": art_rel})
    if reproduce_tree:
        # --reproduce-tree: every file of the reproduce records of this id (and of the Cr-Ni MLIP spot checks), subfolders included
        # (fix proofs, rerun outputs, logs); substituted originals left out
        dirs = sorted(p for p in (ROOT / "reproduce").glob(f"{d['id']}*") if p.is_dir()) + \
            (sorted(p for p in (ROOT / "reproduce").glob("crni-mlip-spotcheck*") if p.is_dir()) if d["id"].startswith("crni") else [])
        for base in dirs:
            for f in sorted(q for q in base.rglob("*") if q.is_file() and "__pycache__" not in str(q)):
                if skip(f):
                    continue
                add_tree_file(f, f"reproduce/{base.name}/{f.relative_to(base)}", about={"@id": art_rel}, description="reproduce record")
    else:
        for f in sorted((ROOT / "reproduce").glob(f"{d['id']}*/*")) + sorted((ROOT / "reproduce").glob("crni-mlip-spotcheck/comparison.*") if d["id"].startswith("crni") else []):
            if f.is_file():
                rel = f"reproduce/{f.parent.name}/{f.name}"
                add_file(f, rel, about={"@id": art_rel}, description="reproduce comparison report")
    # schema family
    for f in sorted((ROOT / "schema").glob("*.json")):
        add_file(f, f"schema/{f.name}", ("File",), description="orchid-assessment-schema 1.0.0-draft")
    # contextual input entities (not copied)
    ctxfiles = {}

    def ctx_file(r):
        key = f"#input-{r['sha256'][:16]}" if r.get("sha256") else f"#input-{abs(hash(r['path']))}"
        if key not in graph:
            e = {"@id": key, "@type": "CreativeWork", "name": r["path"], "storageClass": r["storage_class"]}
            if r.get("sha256"):
                e["sha256"] = r["sha256"]
            if r.get("role"):
                e["description"] = r["role"]
            if r["storage_class"] == "restricted":
                e["conditionsOfAccess"] = "restricted source (publisher PDF or private ORCHID export): referenced by path and sha256 only; not included"
            graph[key] = e
        ctxfiles[key] = 1
        return {"@id": key}
    for i in d.get("inputs", []):
        for f in i.get("files", []):
            ctx_file(f)
    # runs -> CreateActions
    actions = []
    for r in d["run_sequence"]:
        aid = f"#run-{r['run_id']}"
        act = {"@id": aid, "@type": "CreateAction", "name": r["run_id"], "description": f"{r['step']} ({r['status']}): {r.get('summary', '')}",
               "instrument": {"@id": sp_rel}, "hadPlan": {"@id": f"#{g['id']}-step-{r['step']}" if f"#{g['id']}-step-{r['step']}" in graph else f"#{d['id']}-step-{r['step']}"},
               "actionStatus": {"@id": "http://schema.org/CompletedActionStatus" if r["status"] in ("accepted", "side_branch") else ("http://schema.org/FailedActionStatus" if r["status"] == "failed" else "http://schema.org/PotentialActionStatus")}}
        if r.get("run_card"):
            rc_src = op.expand(r["run_card"]["path"]); rc = json.loads(rc_src.read_text())
            rel = add_file(rc_src, f"run_cards/{rc_src.name}", description=f"run card {r['run_id']}")
            act["subjectOf"] = {"@id": rel}
            if isinstance(rc.get("started"), str):
                act["startTime"] = rc["started"]
            if isinstance(rc.get("finished"), str):
                act["endTime"] = rc["finished"]
            act["object"] = [ctx_file(x) for x in rc.get("inputs", [])[:400]]
            act["result"] = [ctx_file(x) for x in rc.get("outputs", [])]
            act["agent"] = {"@id": "#host-" + rc.get("host", "unknown")}
            graph.setdefault("#host-" + rc.get("host", "unknown"), {"@id": "#host-" + rc.get("host", "unknown"), "@type": "Organization", "name": f"compute host {rc.get('host')}"})
        if r.get("start_from"):
            act["wasDerivedFrom"] = {"@id": f"#run-{r['start_from']}"}
        graph[aid] = act; actions.append({"@id": aid})
    if reproduce_tree:  # run cards that execute this exact version but are not in its run sequence (checks after the freeze)
        seq = {op.expand(r['run_card']['path']).resolve() for r in d['run_sequence'] if r.get('run_card')}
        for rc_src in sorted((ROOT / 'run_cards').glob('*.json')):
            rc = json.loads(rc_src.read_text())
            if rc_src.resolve() in seq or (rc.get('executes') or {}).get('specific_protocol') != f"{d['id']}@{d['version']}":
                continue
            rel = add_file(rc_src, f'run_cards/{rc_src.name}', description=f"run card {rc.get('run_id')} (executes {d['id']}@{d['version']}; not in the run sequence)")
            aid = f"#run-{rc.get('run_id')}"; st_ = (rc.get('executes') or {}).get('step')
            act = {'@id': aid, '@type': 'CreateAction', 'name': rc.get('run_id'), 'description': rc.get('title', ''), 'instrument': {'@id': sp_rel},
                   'hadPlan': {'@id': f"#{g['id']}-step-{st_}"} if f"#{g['id']}-step-{st_}" in graph else None, 'subjectOf': {'@id': rel},
                   'actionStatus': {'@id': 'http://schema.org/CompletedActionStatus' if rc.get('status') == 'complete' else 'http://schema.org/PotentialActionStatus'},
                   'object': [ctx_file(x) for x in rc.get('inputs', [])[:400]], 'result': [ctx_file(x) for x in rc.get('outputs', [])],
                   'agent': {'@id': '#host-' + rc.get('host', 'unknown')}}
            act = {k: v for k, v in act.items() if v is not None}
            for k in ('started', 'finished'):
                if isinstance(rc.get(k), str):
                    act['startTime' if k == 'started' else 'endTime'] = rc[k]
            graph.setdefault('#host-' + rc.get('host', 'unknown'), {'@id': '#host-' + rc.get('host', 'unknown'), '@type': 'Organization', 'name': f"compute host {rc.get('host')}"})
            graph[aid] = act; actions.append({'@id': aid})
    graph["#run-overall"] = {"@id": "#run-overall", "@type": "CreateAction", "name": f"execution of {d['id']}@{d['version']} (back-filled)", "instrument": {"@id": sp_rel},
                             "result": {"@id": art_rel}, "object": [{"@id": k} for k in ctxfiles if graph[k]["storageClass"] != "remote_record"][:200],
                             "actionStatus": {"@id": "http://schema.org/CompletedActionStatus"}, "description": d.get("status_note", "")}
    # decisions -> actions (--decisions; first used for crni-paper-fit-step4c-b@1.0.3). One schema.org ChooseAction per decision row
    # (an Action, i.e. prov:Activity in the W3C PROV / schema.org correspondence): agent = the decider (PI -> the PI Person of
    # maintainers; agent -> the ORCHID agent as SoftwareApplication), endTime = date, description = decision text, object = the
    # HowToSteps of applies_to, subjectOf = a CreativeWork naming the source (text = the quote when recorded). The reason has no
    # schema.org Action property and is kept in the description after "Why:" (gap reported in SCHEMA.md); the runs a decision
    # affected are reachable through object -> HowToStep <- run hadPlan (no profile property links a decision to a run).
    dec_ids = []
    if decisions:
        pi = next((p for p in d.get("maintainers", []) if p.get("role") == "PI"), None)
        pi_id = person_id(pi) if pi else None
        graph["#agent-orchid"] = {"@id": "#agent-orchid", "@type": "SoftwareApplication", "name": "Claude (ORCHID agent)",
                                  "description": "the ORCHID coordinating and maintaining agent; decisions labelled 'agent' in the protocol"}
        for n, x in enumerate(d.get("decisions", []) or [], 1):
            who = x["who"].strip(); ag = []
            if who.startswith("PI") and pi_id:
                ag.append({"@id": pi_id})
            if who.startswith("agent") or "agent (" in who:
                ag.append({"@id": "#agent-orchid"})
            did = f"#decision-{n:03d}"
            objs = []
            for s in x.get("applies_to", []) or []:
                for cand in (f"#{g['id']}-step-{s}", f"#{d['id']}-step-{s}"):
                    if cand in graph:
                        objs.append({"@id": cand}); break
            src = f"{did}-source"
            graph[src] = {"@id": src, "@type": "CreativeWork", "name": x["source"], **({"text": x["quote"]} if x.get("quote") else {}),
                          "description": f"source of decision {n} as recorded in {d['id']}@{d['version']} (who: {who})"}
            dname = x["decision"] if len(x["decision"]) <= 120 else x["decision"][:117].rstrip() + "..."
            graph[did] = {"@id": did, "@type": "ChooseAction", "name": dname, "description": f"{x['decision'].rstrip().rstrip('.')}. Why: {x['why']}",
                          "endTime": str(x["date"]), "agent": ag if len(ag) != 1 else ag[0], "object": objs,
                          "actionStatus": {"@id": "http://schema.org/CompletedActionStatus"}, "subjectOf": {"@id": src},
                          "instrument": {"@id": sp_rel}}
            dec_ids.append({"@id": did})
    graph["#orchid-protocol-yaml"] = {"@id": "#orchid-protocol-yaml", "@type": "ComputerLanguage", "name": "ORCHID protocol YAML", "alternateName": "orchid-assessment-schema 1.0.0-draft",
                                      "url": {"@id": "schema/protocol.schema.json"}}
    graph["https://creativecommons.org/licenses/by/4.0/"] = {"@id": "https://creativecommons.org/licenses/by/4.0/", "@type": "CreativeWork", "name": "CC BY 4.0"}
    for p in d.get("maintainers", []):
        pid = person_id(p)
        graph[pid] = {"@id": pid, "@type": "Person", "name": p["name"], **({"email": p["email"]} if p.get("email") else {}),
                      **({"identifier": f"https://orcid.org/{p['orcid']}"} if p.get("orcid") else {})}
    for prof in PROFILES:
        graph[prof["@id"]] = {"@id": prof["@id"], "@type": "CreativeWork", "name": prof["@id"].split("/")[-2].title() + " Run Crate", "version": "0.5"}
    root = {"@id": "./", "@type": "Dataset", "name": d["title"], "description": d["purpose"].strip(), "datePublished": time.strftime("%Y-%m-%d"),
            "license": {"@id": "https://creativecommons.org/licenses/by/4.0/"}, "conformsTo": PROFILES, "mainEntity": {"@id": sp_rel}, "hasPart": parts,
            "mentions": actions + [{"@id": "#run-overall"}] + dec_ids, "creativeWorkStatus": d["status"],
            "author": [{"@id": person_id(p)} for p in d.get("maintainers", [])]}
    if public:
        if pub_binary:
            sys.exit(f"--public: binary files hold local information and cannot be sanitized: {pub_binary[:10]}")
        mp = out / "PUBLIC_SUBSTITUTES.json"
        frozen.write(mp, json.dumps({"by": "tools/build_crate.py --public (rules: tools/public_sanitize.py)",
                                  "rule": "every file of this crate that held local information (home, scratch or session paths, user or host names, host addresses) is "
                                          "its sanitized copy; original_sha256 identifies the original kept in the repository, sanitized_sha256 is the file here; "
                                          "original paths are written with the same rules; recompute with: python3 tools/public_sanitize.py proof ORIGINAL COPY",
                                  "n_files": len(pub_rows), "files": sorted(pub_rows, key=lambda r: r["crate_path"])}, indent=1) + "\n", "build_crate.py")
        add_file(mp, "PUBLIC_SUBSTITUTES.json", description="original sha256 -> sanitized sha256 of every public copy in this crate")
        root["hasPart"] = parts
    meta = {"@id": "ro-crate-metadata.json", "@type": "CreativeWork", "about": {"@id": "./"}, "conformsTo": [{"@id": "https://w3id.org/ro/crate/1.1"}] + PROFILES}
    crate = {"@context": CTX, "@graph": [meta, root] + list(graph.values())}
    pub = psan.sanitize_text if public else (lambda t: t)
    frozen.write(out / "ro-crate-metadata.json", pub(json.dumps(crate, indent=1, ensure_ascii=False)), "build_crate.py")
    # preview: the specific protocol rendering + a file table
    md = render_md(d) + "\n## Files in this crate\n\n| file | sha256 | size |\n|---|---|---|\n" + "\n".join(f"| `{p['@id']}` | `{graph[p['@id']]['sha256']}` | {graph[p['@id']]['contentSize']} |" for p in parts)
    frozen.write(out / "ro-crate-preview.html", pub(md_to_html(md, d["title"])), "build_crate.py")
    frozen.write(out / "README.md", pub(f"# {d['title']}\n\nWorkflow Run RO-Crate for `{d['id']}@{d['version']}` (status {d['status']}). Open `ro-crate-preview.html` for the protocol, "
                                   f"`dashboard/dashboard.html` for the assessment dashboard. Restricted inputs are referenced by sha256 only. Built by tools/build_crate.py."
                                       + (" Public copy: files that held local information are sanitized copies; PUBLIC_SUBSTITUTES.json maps each original sha256 "
                                          "to its copy." if public else "") + "\n"), "build_crate.py")
    # self-check (--public: on the metadata as written, after sanitizing)
    if public:
        graph = {e["@id"]: e for e in json.loads((out / "ro-crate-metadata.json").read_text())["@graph"][2:]}
        parts = json.loads((out / "ro-crate-metadata.json").read_text())["@graph"][1]["hasPart"]
    bad = [p["@id"] for p in parts if op.sha256_file(out / p["@id"]) != graph[p["@id"]]["sha256"]]
    leaked = [k for k, v in graph.items() if v.get("storageClass") == "restricted" and (out / Path(v["name"]).name).exists()]
    ids = set(graph) | {"./", "ro-crate-metadata.json"}
    dangling = sorted({v["@id"] for e in graph.values() for v in _refs(e) if not v["@id"].startswith(("http://", "https://")) and v["@id"] not in ids})
    print(f"{out}: {len(parts)} files, {len(actions)} runs, {len(dec_ids)} decisions, {len(ctxfiles)} contextual inputs; hash errors {len(bad)}; "
          f"restricted files inside {len(leaked)}; dangling local @id references {len(dangling)}" + (f" {dangling[:5]}" if dangling else ""))
    return not bad and not leaked


if __name__ == "__main__":
    if sys.argv[1] == "--render":
        doc = op.load_doc(sys.argv[2]); md = render_md(doc)
        w = frozen.Writes("build_crate.py --render"); w.add(sys.argv[3], md); w.add(sys.argv[4], md_to_html(md, doc["title"])); w.commit()   # all or none
        print("rendered", sys.argv[3], sys.argv[4])
    else:
        fl = sys.argv[3:]
        sys.exit(0 if build(sys.argv[1], sys.argv[2], addenda="--addenda" in fl, decisions="--decisions" in fl, pinned_evidence="--pinned-evidence" in fl,
                            substitutes="--substitutes" in fl, reproduce_tree="--reproduce-tree" in fl, public="--public" in fl) else 1)
