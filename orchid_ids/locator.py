"""ORC record ids and persistent locators (pid), exactly as the ORCHID release computes them.

Port of the published id rule, ``asset_ids.py`` of the SGTE-corpus tools (tools-release-v2.1.18, md5
d6a63407d8d498852490f388d37472e6, the version the v2026.10 records were built with), plus the row-suffix rule of the
release exporter (orchid-project.org ``tools/export_literature_data.py``) and the provisional ``local:`` namespace
decided by the PI on 6 Nov 2026. Standard library only.

Locator grammar (asset_ids.py):  source / asset [/ panel] / element [/ cell] [#datum]
  source   doi:<lowercased doi> | isbn:<isbn>[:ch-<n>] | sha256:<first 16 hex of the PDF>
           | local:<ORCID>/<dataset-uuid>   (provisional, unpublished data; PI 6 Nov 2026)
  asset    p<page>/tab-<label>[@<y-band>] | p<page>/fig-<label>[@<y-band>][/panel-<x>] | p<page>/text-<nn> | supp-<file>
  element  r<nn>[/c<nn>] (table row) | s-<series>/pt-<nnn> (figure point) | s-<series>/crv-<nn> (curve)
           | r-unplaced-<8 hex> (row not placed by printed position) | s<nn> (sentence of a text passage; in the release)
  datum    #<observation type> as released (#equilibrium_property, #invariant_reaction, ...), or #property-<quantity>

Compact id: ``ORC-`` + the first 10 characters of the RFC 4648 base32 encoding of SHA-256(full locator, UTF-8).
When several released values share one locator (one table row, several values), the release appends ``.`` + the first
6 hex of SHA-256(internal observation id); that internal id is not part of the released records.
"""
from __future__ import annotations

import base64
import hashlib
import re
import uuid as _uuid

_SAFE = re.compile(r"[^a-z0-9._-]+")

ORC_RE = re.compile(r"^ORC-[A-Z2-7]{10}(\.[0-9a-f]{6})?$")
ORC_CONTRIBUTED_RE = re.compile(r"^ORC-C[A-Z2-7]{10}$")  # contributions/tools/orchid_contrib.py contribution_id()
ORCID_RE = re.compile(r"^(?:https?://orcid\.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[\dX])$")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
LOCAL_SOURCE_RE = re.compile(r"^local:(\d{4}-\d{4}-\d{4}-\d{3}[\dX])/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$")
# an asset inside a locator: the first path segment that is a page asset or a supplement file
_ASSET_RE = re.compile(r"/(p\d+/(?:tab|fig|text)-[^/#]+|supp-[^/#]+)")
# element forms of the v2026.10 release: r<nn>[/c<nn>] (placed table row), r-unplaced-<8 hex> (a row whose printed
# position was not placed), s<nn> (sentence of a text passage), s-<series>/pt-<nnn> and s-<series>/crv-<nn> (figures)
ELEMENT_RE = re.compile(r"(/panel-[a-z0-9._-]+)?(/r\d{2,}(/c\d{2,})?|/r-unplaced-[0-9a-f]{8}|/s\d{2,}"
                        r"|/s-[a-z0-9._-]+/(pt-\d{3,}|crv-\d{2,}))?(/reading-[A-Za-z0-9._-]+)?")


def _norm(text) -> str:
    return _SAFE.sub("-", str(text).strip().lower()).strip("-") or "x"


def normalize_doi(doi: str) -> str:
    """Bare lowercase DOI. Strips ``https://doi.org/``, ``doi.org/`` and ``doi:`` (released DOIs carry none of these, so
    released ids are unaffected); asset_ids.source_id only strips and lowercases."""
    d = str(doi or "").strip()
    d = re.sub(r"(?i)^(https?://)?(dx\.)?doi\.org/", "", d)
    d = re.sub(r"(?i)^doi:\s*", "", d)
    return d.lower()


# ------------------------------------------------------------------ ORCID / namespace
def orcid_ok(orcid: str) -> bool:
    """ISO 7064 mod 11-2 checksum of an ORCID iD (bare or https://orcid.org/ form), as contributions/tools/orchid_contrib.py."""
    m = ORCID_RE.match(str(orcid or "").strip())
    if not m:
        return False
    digits = m.group(1).replace("-", "")
    total = 0
    for ch in digits[:-1]:
        total = (total + int(ch)) * 2
    check = (12 - total % 11) % 11
    return digits[-1] == ("X" if check == 10 else str(check))


def orcid_bare(orcid: str) -> str:
    m = ORCID_RE.match(str(orcid or "").strip())
    if not m or not orcid_ok(orcid):
        raise ValueError(f"not a valid ORCID iD (format or checksum): {orcid!r}")
    return m.group(1)


def new_dataset_uuid() -> str:
    """A fresh random dataset UUID (version 4). Generate it ONCE per dataset and keep it with the data."""
    return str(_uuid.uuid4())


def make_provisional_namespace(orcid: str, dataset_uuid: str) -> str:
    """``local:<ORCID>/<dataset-uuid>``: the source part of a locator for unpublished data (PI 6 Nov 2026).
    The ORCID is checksum-verified and written bare; the UUID in canonical lowercase 8-4-4-4-12 form."""
    o = orcid_bare(orcid)
    try:
        u = str(_uuid.UUID(str(dataset_uuid).strip()))
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"not a UUID: {dataset_uuid!r}") from exc
    return f"local:{o}/{u}"


# ------------------------------------------------------------------ locator parts (asset_ids.py)
def source_id(doi=None, isbn=None, chapter=None, pdf_sha256=None, orcid=None, dataset_uuid=None) -> str:
    """Source part. doi (a paper or a deposited dataset, e.g. Zenodo) | isbn [+ chapter] | pdf_sha256 |
    orcid + dataset_uuid (provisional ``local:`` namespace). Same precedence as asset_ids.source_id."""
    if doi:
        return "doi:" + normalize_doi(doi)
    if isbn:
        return f"isbn:{_norm(isbn)}" + (f":ch-{_norm(chapter)}" if chapter else "")
    if pdf_sha256:
        return "sha256:" + str(pdf_sha256)[:16]
    if orcid or dataset_uuid:
        return make_provisional_namespace(orcid, dataset_uuid)
    raise ValueError("a source needs a DOI (paper or dataset), an ISBN, the PDF hash, or an ORCID + dataset UUID")


def asset_id(source, page=None, kind="table", label=None, panel=None, y_band=None, n=None) -> str:
    """kind: table | figure | text | supplement. y_band separates two assets with the same label on one page."""
    prefix = {"table": "tab", "figure": "fig", "text": "text", "supplement": "supp"}[kind]
    if kind == "supplement":
        return f"{source}/supp-{_norm(label)}"
    if kind == "text":
        return f"{source}/p{int(page)}/text-{int(n):02d}"
    out = f"{source}/p{int(page)}/{prefix}-{_norm(label)}"
    if y_band is not None:
        out += f"@{int(y_band)}"
    if panel:
        out += f"/panel-{_norm(panel)}"
    return out


def row_id(asset, printed_position, column=None) -> str:
    """printed_position: 1-based row in the printed table (or the data file)."""
    out = f"{asset}/r{int(printed_position):02d}"
    return out + (f"/c{int(column):02d}" if column is not None else "")


def point_id(asset, series, n) -> str:
    return f"{asset}/s-{_norm(series)}/pt-{int(n):03d}"


def curve_id(asset, series, n) -> str:
    return f"{asset}/s-{_norm(series)}/crv-{int(n):02d}"


def datum_id(element, datum_type) -> str:
    return f"{element}#{_norm(datum_type)}"


def compact(full_id: str) -> str:
    """ORC- + the first 10 base32 characters of SHA-256(full id)."""
    digest = hashlib.sha256(full_id.encode()).digest()
    return "ORC-" + base64.b32encode(digest).decode()[:10]


def value_suffix(observation_key: str) -> str:
    """Release rule for several values on one locator: '.' + first 6 hex of SHA-256(observation key)."""
    return "." + hashlib.sha256(str(observation_key).encode()).hexdigest()[:6]


def build_pid(*, source=None, doi=None, isbn=None, chapter=None, pdf_sha256=None, orcid=None, dataset_uuid=None,
              kind="table", page=None, label=None, panel=None, y_band=None, n=None,
              row=None, column=None, series=None, point=None, curve=None, datum_type="equilibrium_property") -> str:
    """Full locator from its parts. Element: row (table / data-file row), or series + point, or series + curve."""
    src = source or source_id(doi=doi, isbn=isbn, chapter=chapter, pdf_sha256=pdf_sha256, orcid=orcid, dataset_uuid=dataset_uuid)
    asset = asset_id(src, page=page, kind=kind, label=label, panel=panel, y_band=y_band, n=n)
    if row is not None:
        element = row_id(asset, row, column)
    elif series is not None and point is not None:
        element = point_id(asset, series, point)
    elif series is not None and curve is not None:
        element = curve_id(asset, series, curve)
    elif kind == "text":
        element = asset
    else:
        raise ValueError("an element is needed: row, series + point, or series + curve")
    return datum_id(element, datum_type)


def compute_orc_id(pid: str | None = None, *, observation_key: str | None = None, **parts) -> dict:
    """ORC id of a locator. pid: the full locator; or the parts of build_pid(). observation_key: only when several values
    share one locator (the release appends value_suffix(internal observation id)). Returns {id, pid, namespace, provisional}."""
    full = pid if pid is not None else build_pid(**parts)
    parsed = parse_pid(full)
    oid = compact(full) + (value_suffix(observation_key) if observation_key is not None else "")
    return {"id": oid, "pid": full, "namespace": parsed["namespace"], "source": parsed["source"],
            "provisional": parsed["namespace"] == "local"}


# ------------------------------------------------------------------ parsing / validation
def parse_pid(pid: str) -> dict:
    """Split a locator into source, asset, element and datum; raises ValueError if it does not follow the grammar."""
    if not isinstance(pid, str) or not pid or pid != pid.strip():
        raise ValueError(f"empty or padded locator: {pid!r}")
    if pid.startswith("local:"):
        m = re.match(r"^(local:[^/]+/[^/]+)(/.*)?$", pid)
        source, rest = (m.group(1), m.group(2) or "") if m else (pid, "")
        if not LOCAL_SOURCE_RE.match(source):
            raise ValueError(f"provisional namespace must be local:<ORCID>/<dataset-uuid> (lowercase UUID): {source!r}")
        if not orcid_ok(source.split(":", 1)[1].split("/", 1)[0]):
            raise ValueError(f"ORCID checksum fails in {source!r}")
        namespace = "local"
        m2 = _ASSET_RE.match(rest)
    else:
        if not re.match(r"^(doi:10\.[^/\s]+/\S+|isbn:[a-z0-9._-]+(:ch-[a-z0-9._-]+)?|sha256:[0-9a-f]{16})/", pid):
            raise ValueError(f"locator source must be doi:, isbn:, sha256: or local:<ORCID>/<uuid>: {pid!r}")
        namespace = pid.split(":", 1)[0]
        m2 = _ASSET_RE.search(pid)
        if m2 is None:
            raise ValueError(f"no asset (p<page>/tab-|fig-|text- or supp-) in {pid!r}")
        source, rest = pid[:m2.start()], pid[m2.start():]
        m2 = _ASSET_RE.match(rest)
    if m2 is None:
        raise ValueError(f"no asset (p<page>/tab-|fig-|text- or supp-) after the source in {pid!r}")
    asset = source + m2.group(0)
    tail = rest[m2.end():]
    element, _, datum = tail.partition("#")
    if "#" in datum or (datum and not re.fullmatch(r"[a-z0-9._-]+", datum)):
        raise ValueError(f"datum must be #<lowercase token>: {pid!r}")
    if element and not ELEMENT_RE.fullmatch(element):
        raise ValueError(f"element must be r<nn>[/c<nn>], r-unplaced-<8 hex>, s<nn>, s-<series>/pt-<nnn> or "
                         f"s-<series>/crv-<nn>: {element!r} in {pid!r}")
    return {"namespace": namespace, "source": source, "asset": asset, "element": element.lstrip("/"), "datum": datum or None}


def validate_id(identifier: str) -> dict:
    """Format check of an ORCHID id: ORC- (record), ORC-C (contributed record), S- (state), C- (state class)."""
    s = str(identifier or "")
    if ORC_RE.match(s):
        return {"ok": True, "kind": "record", "suffixed": "." in s}
    if ORC_CONTRIBUTED_RE.match(s):
        return {"ok": True, "kind": "contributed_record", "suffixed": False}
    if re.fullmatch(r"S-[0-9a-f]{10}", s):
        return {"ok": True, "kind": "state"}
    if re.fullmatch(r"C-[0-9a-f]{10}", s):
        return {"ok": True, "kind": "state_class"}
    return {"ok": False, "kind": None, "error": f"not an ORCHID id: {s!r} (ORC-<10 base32>[.<6 hex>], ORC-C<10 base32>, S-/C-<10 hex>)"}


def check_link(identifier: str, pid: str, observation_key: str | None = None) -> dict:
    """An id claimed for a locator: format, grammar, and recomputation (id == compact(pid)[+suffix]). A suffixed id is
    accepted when its base recomputes and no observation_key is given (the suffix key is not released)."""
    errors = []
    fmt = validate_id(identifier)
    if not fmt["ok"] or fmt["kind"] != "record":
        errors.append(fmt.get("error") or f"{identifier} is a {fmt['kind']} id, not a record id")
    try:
        parsed = parse_pid(pid)
    except ValueError as exc:
        return {"ok": False, "errors": errors + [str(exc)]}
    base = compact(pid)
    want = base + (value_suffix(observation_key) if observation_key is not None else "")
    got = str(identifier)
    if observation_key is not None:
        if got != want:
            errors.append(f"{got} does not recompute from its locator and observation key (expected {want})")
    elif got.split(".")[0] != base:
        errors.append(f"{got} does not recompute from its locator (expected {base})")
    return {"ok": not errors, "errors": errors, "namespace": parsed["namespace"], "provisional": parsed["namespace"] == "local",
            "recomputed": want, "suffix_checked": observation_key is not None or "." not in got}
