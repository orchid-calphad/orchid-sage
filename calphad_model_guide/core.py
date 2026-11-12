"""Deterministic model screening independent of any data provider or optimizer."""
import hashlib
import json
import math
from fractions import Fraction
from importlib.resources import files
from itertools import product, islice

ELEMENTS = set('H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og'.split())


def library():
    return json.loads(files(__package__).joinpath('data/recipes.json').read_text())


def search(text='', topic=None):
    """Search the complete catalog, including methods unsupported by the input schema."""
    lib = library()
    recipes = [r for r in lib['recipes'] if
               (topic is None or r['topic'] == topic) and
               text.casefold() in json.dumps(r, ensure_ascii=False).casefold()]
    source_ids = {s for r in recipes for s in r['source_ids']}
    return {'recipes': recipes, 'sources': [s for s in lib['sources'] if s['id'] in source_ids],
            'count': len(recipes), 'advisory_only': True}


def validate(spec):
    """Validate the versioned input contract. Unknown fields fail closed."""
    errors = []
    def check(condition, message):
        if not condition:
            errors.append(message)
    if not isinstance(spec, dict):
        return ['spec must be an object']
    required = {'schema_version', 'phase', 'elements', 'sublattices', 'reference_state',
                'energy_basis', 'vacancy_role', 'ordered', 'evidence', 'validity'}
    check(set(spec) == required, f'fields must be exactly {sorted(required)}')
    check(type(spec.get('schema_version')) is int and spec['schema_version'] == 1,
          'schema_version must be integer 1')
    for key in ('phase', 'reference_state'):
        check(isinstance(spec.get(key), str) and bool(spec[key].strip()), f'{key} must be nonempty')
    elements = spec.get('elements')
    if not isinstance(elements, list) or not elements or not all(isinstance(x, str) and x.strip() and x != 'VA' for x in elements):
        errors.append('elements must be a nonempty list of non-VA species identifiers')
        elements = []
    check(len(set(elements)) == len(elements), 'elements must be unique')
    check(set(elements) <= ELEMENTS, 'v1 accepts neutral elemental symbols only; ions and molecular species require a future domain adapter')
    check(spec.get('energy_basis') in ('J/mol_atoms', 'J/mol_formula', 'unknown'), 'invalid energy_basis')
    check(spec.get('vacancy_role') in ('none', 'interstitial_empty', 'constitutional', 'thermal', 'unknown'), 'invalid vacancy_role')
    check(type(spec.get('ordered')) is bool, 'ordered must be a boolean')
    sls = spec.get('sublattices')
    if not isinstance(sls, list) or not sls:
        errors.append('sublattices must be a nonempty list')
        sls = []
    ids = []
    has_va = False
    for i, sl in enumerate(sls):
        if not isinstance(sl, dict) or set(sl) != {'id', 'site_ratio', 'constituents'}:
            errors.append(f'sublattices[{i}] requires id, site_ratio, constituents only')
            continue
        sid = sl['id']
        check(isinstance(sid, str) and bool(sid.strip()), f'sublattices[{i}].id must be nonempty')
        if isinstance(sid, str):
            ids.append(sid)
        ratio = sl['site_ratio']
        check(type(ratio) in (int, float) and math.isfinite(ratio) and ratio > 0,
              f'sublattices[{i}].site_ratio must be finite and positive')
        cs = sl['constituents']
        if not isinstance(cs, list) or not cs or not all(isinstance(x, str) for x in cs):
            errors.append(f'sublattices[{i}].constituents must be nonempty strings')
            continue
        check(len(set(cs)) == len(cs), f'sublattices[{i}] has duplicate constituents')
        check(set(cs) <= set(elements) | {'VA'}, f'sublattices[{i}] contains undeclared species')
        has_va |= 'VA' in cs
    check(len(ids) == len(set(ids)), 'sublattice ids must be unique')
    used = {x for sl in sls if isinstance(sl, dict) for x in sl.get('constituents', []) if isinstance(x, str)} if all(isinstance(sl, dict) and isinstance(sl.get('constituents'), list) for sl in sls) else set()
    check(set(elements) <= used, 'all declared elements must occur on a sublattice')
    check(not has_va or spec.get('vacancy_role') != 'none', 'VA present but vacancy_role is none')
    check(has_va or spec.get('vacancy_role') == 'none', 'vacancy role declared without VA')
    ev = spec.get('evidence')
    allowed = ('crystallography', 'site_occupancy', 'phase_equilibria', 'endmember_energies', 'defect_data', 'ordering_data')
    if not isinstance(ev, list):
        errors.append('evidence must be a list')
    else:
        for i, e in enumerate(ev):
            if not isinstance(e, dict) or set(e) != {'kind', 'source', 'locator', 'status'}:
                errors.append(f'evidence[{i}] requires kind, source, locator, status only')
                continue
            check(e['kind'] in allowed, f'evidence[{i}] has unknown kind')
            check(e['status'] in ('reported', 'verified', 'conflicting'), f'evidence[{i}] has invalid status')
            for k in ('source', 'locator'):
                check(isinstance(e[k], str) and bool(e[k].strip()), f'evidence[{i}].{k} must be nonempty')
    validity = spec.get('validity')
    if not isinstance(validity, dict) or set(validity) != {'temperature_K', 'composition_scope'}:
        errors.append('validity requires temperature_K and composition_scope')
    else:
        t = validity['temperature_K']
        check(t is None or (isinstance(t, list) and len(t) == 2 and all(type(x) in (int,float) and math.isfinite(x) and x > 0 for x in t) and t[0] <= t[1]), 'temperature_K must be null or [positive Tmin, Tmax]')
        check(isinstance(validity['composition_scope'], str) and bool(validity['composition_scope'].strip()), 'composition_scope must be nonempty')
    return errors


def _require(spec):
    errors = validate(spec)
    if errors:
        raise ValueError('; '.join(errors))


def _identity(spec):
    lib = library()
    def digest(x):
        return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    return {'tool_version': '0.2.0', 'schema_version': 1, 'input_sha256': digest(spec),
            'library_sha256': digest(lib), 'advisory_only': True}


def audit(spec):
    _require(spec)
    findings = []
    def add(code, severity, message):
        findings.append({'code': code, 'severity': severity, 'message': message})
    if spec['reference_state'].lower() == 'unknown':
        add('reference_missing', 'blocker', 'Specify shared reference states before comparing energies.')
    if spec['energy_basis'] == 'unknown':
        add('basis_missing', 'blocker', 'Specify molar normalization before comparing energies.')
    if spec['vacancy_role'] == 'unknown':
        add('vacancy_role_missing', 'blocker', 'Resolve vacancy interpretation before parameterization.')
    if all('VA' in sl['constituents'] for sl in spec['sublattices']):
        add('empty_configuration', 'review', 'All-vacancy corner exists; do not treat it as an atomistic structure or assign zero energy automatically.')
    if not spec['evidence']:
        add('no_evidence', 'review', 'No source-backed evidence supplied; model suitability is unresolved.')
    for e in spec['evidence']:
        if e['status'] == 'conflicting':
            add('conflicting_evidence', 'review', f"Resolve {e['kind']} conflict at {e['source']} ({e['locator']}).")
    if spec['validity']['temperature_K'] is None:
        add('temperature_scope_missing', 'review', 'State the intended temperature domain before validation.')
    return {**_identity(spec), 'phase': spec['phase'], 'findings': findings,
            'metadata_ready': not any(f['severity'] == 'blocker' for f in findings),
            'scientifically_validated': False}


def recommend(spec):
    """Rank by evidence coverage, not by probability of scientific correctness."""
    _require(spec)
    kinds = {e['kind'] for e in spec['evidence'] if e['status'] == 'verified'}
    conflict = {e['kind'] for e in spec['evidence'] if e['status'] == 'conflicting'}
    candidates = []
    for r in library()['recipes']:
        trigger = r['trigger']
        applies = (trigger == 'always' or trigger == 'multisite' and len(spec['sublattices']) > 2
                   or trigger == 'vacancy' and spec['vacancy_role'] != 'none'
                   or trigger == 'ordering' and spec['ordered'])
        if not applies:
            continue
        missing = sorted(set(r['requires']) - kinds)
        conflicts = sorted(set(r['requires']) & conflict)
        candidates.append({**r, 'missing_verified_evidence': missing, 'conflicting_evidence': conflicts,
                           'screening_status': 'needs_evidence' if missing or conflicts else 'candidate_for_validation',
                           'verified_requirement_count': len(set(r['requires']) & kinds)})
    candidates.sort(key=lambda r: (bool(r['conflicting_evidence']), len(r['missing_verified_evidence']), r['id']))
    return {**_identity(spec), 'ranking': 'fewest missing evidence requirements, conflicts last; not scientific confidence',
            'audit': audit(spec), 'candidates': candidates,
            'manual_context_recipes': [r['id'] for r in library()['recipes'] if r['trigger'] == 'manual'],
            'context_note': 'Manual-context recipes require information absent from v1; discover them with search, not automatic applicability claims.'}


def plan(spec, limit=20):
    """Count formal corners and emit bounded hypotheses; never launch calculations."""
    _require(spec)
    if type(limit) is not int or not 0 <= limit <= 1000:
        raise ValueError('limit must be an integer from 0 to 1000')
    sls = spec['sublattices']
    count = math.prod(len(s['constituents']) for s in sls)
    empty = int(all('VA' in s['constituents'] for s in sls))
    configs = (p for p in product(*(s['constituents'] for s in sls)) if not all(x == 'VA' for x in p))
    preview = []
    for p in islice(configs, limit):
        atoms = sum(s['site_ratio'] for s,x in zip(sls,p) if x != 'VA')
        amounts = {e: sum(s['site_ratio'] for s,x in zip(sls,p) if x == e) / atoms for e in spec['elements']}
        preview.append({'occupants': dict(zip((s['id'] for s in sls), p)), 'atomic_fractions': amounts,
                        'status': 'formal_configuration_requires_structure_and_stability_review'})
    return {**_identity(spec), 'formal_endmembers': count, 'all_vacancy_corners': empty,
            'nonempty_endmembers': count-empty, 'preview': preview, 'truncated': len(preview) < count-empty,
            'independent_energy_parameters': None,
            'calculation_count': None,
            'reason': 'No certified energy relationships or structure mapping supplied; corner count is not a calculation budget.',
            'required_checks': ['reference and normalization', 'site mapping', 'magnetic state',
                                'relaxation preserves intended structure', 'held-out energies and phase equilibria'],
            'recipes': [r['id'] for r in recommend(spec)['candidates']]}


def compare(left, right):
    """Conservative structural preflight, not a proof of Gibbs-energy equivalence."""
    _require(left); _require(right)
    issues = []
    for field in ('phase', 'reference_state', 'energy_basis', 'vacancy_role', 'ordered', 'validity'):
        if left[field] != right[field]:
            issues.append(f'{field} differs')
    def signature(s):
        # Relative site ratios can be compared for structure; absolute formula normalization remains separate.
        total = sum(Fraction(str(x['site_ratio'])) for x in s['sublattices'])
        return {x['id']: (Fraction(str(x['site_ratio']))/total, tuple(sorted(x['constituents']))) for x in s['sublattices']}
    if signature(left) != signature(right):
        issues.append('site identities, relative ratios or constituents differ; explicit mapping required')
    if left['energy_basis'] == 'J/mol_formula' or right['energy_basis'] == 'J/mol_formula':
        if sum(Fraction(str(x['site_ratio'])) for x in left['sublattices']) != sum(Fraction(str(x['site_ratio'])) for x in right['sublattices']):
            issues.append('formula-unit normalization differs; energy rescaling required')
    if left['reference_state'].lower() == 'unknown' or right['reference_state'].lower() == 'unknown':
        issues.append('reference state unresolved')
    if left['energy_basis'] == 'unknown' or right['energy_basis'] == 'unknown':
        issues.append('energy basis unresolved')
    if not audit(left)['metadata_ready'] or not audit(right)['metadata_ready']:
        issues.append('resolve input metadata blockers before compatibility review')
    return {'left': _identity(left), 'right': _identity(right), 'issues': issues,
            'status': 'requires_reconciliation' if issues else 'structural_preflight_only',
            'thermodynamic_equivalence_proven': False,
            'remaining': 'Compare Gibbs-energy functions, derivatives, ordering limits, magnetic terms and subsystem extrapolation.'}
