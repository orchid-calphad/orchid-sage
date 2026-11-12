"""Exact bookkeeping; composition relations never imply energy relations."""
from fractions import Fraction
from itertools import product
from math import prod
from .core import validate, _identity


def _basis(columns):
    """Return independent column indices using exact elimination."""
    pivots, selected = {}, []
    for index, column in enumerate(columns):
        v = list(column)
        for row, pivot in sorted(pivots.items()):
            factor = v[row]
            v = [a - factor*b for a, b in zip(v, pivot)]
        row = next((i for i, value in enumerate(v) if value), None)
        if row is not None:
            divisor = v[row]
            pivots[row] = [value/divisor for value in v]
            selected.append(index)
    return selected


def basis(spec, max_corners=4096):
    errors = validate(spec)
    if errors:
        raise ValueError('; '.join(errors))
    if type(max_corners) is not int or not 1 <= max_corners <= 4096:
        raise ValueError('max_corners must be an integer from 1 to 4096')
    sites = spec['sublattices']
    count = prod(len(s['constituents']) for s in sites)
    if count > max_corners:
        raise ValueError(f'{count} formal corners exceed limit {max_corners}')
    configurations = list(product(*(s['constituents'] for s in sites)))
    ratios = [Fraction(str(s['site_ratio'])) for s in sites]
    compositions = [[sum((a for a, c in zip(ratios, config) if c == el), Fraction(0))
                     for el in spec['elements']] for config in configurations]
    occupancy = [[a if config[i] == c else Fraction(0)
                  for i, (s, a) in enumerate(zip(sites, ratios)) for c in s['constituents']]
                 for config in configurations]
    cb, ob = _basis(compositions), _basis(occupancy)
    return {**_identity(spec), 'formal_corner_count': count,
            'configurations': configurations,
            'composition_rows': spec['elements'],
            'composition_columns': [[str(x) for x in c] for c in compositions],
            'composition_basis_indices': cb, 'composition_rank': len(cb),
            'occupancy_basis_indices': ob, 'occupancy_rank': len(ob),
            'composition_nullity': count-len(cb), 'occupancy_nullity': count-len(ob),
            'independent_energy_parameters': None,
            'interpretation': 'Exact linear ranks of formula-unit atom counts and site occupant counts, including formal vacancy corners. Neither rank determines independent energies; no endmember may be omitted on this evidence alone.'}


def reciprocal(spec):
    """Solve AC+BD-AD-BC=delta for at most one missing energy."""
    required = {'energies', 'delta', 'energy_basis', 'reference_state', 'assumption'}
    if not isinstance(spec, dict) or set(spec) != required:
        raise ValueError(f'reciprocal input requires exactly {sorted(required)}')
    if spec['energy_basis'] != 'J/mol_formula':
        raise ValueError('reciprocal energies require a common J/mol_formula basis')
    for key in ('reference_state', 'assumption'):
        if not isinstance(spec[key], str) or not spec[key].strip() or spec[key].strip().lower() == 'unknown':
            raise ValueError(f'{key} must explicitly document the common reference or assumption')
    energies = spec['energies']
    signs = {'AC': 1, 'BD': 1, 'AD': -1, 'BC': -1}
    if not isinstance(energies, dict) or set(energies) != set(signs):
        raise ValueError('energies must contain AC, BD, AD, BC; use null for one unknown')
    def number(value):
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            raise ValueError('energies and delta must be finite rational numbers')
        try:
            return Fraction(str(value))
        except (ValueError, ZeroDivisionError):
            raise ValueError('energies and delta must be finite rational numbers') from None
    delta = number(spec['delta'])
    missing = [k for k, v in energies.items() if v is None]
    if len(missing) > 1:
        raise ValueError('at most one energy may be unknown')
    values = {k: number(v) for k, v in energies.items() if v is not None}
    total = sum((signs[k]*v for k, v in values.items()), Fraction(0))
    if missing:
        values[missing[0]] = (delta-total)/signs[missing[0]]
    residual = sum(signs[k]*v for k, v in values.items())-delta
    return {'equation': 'G_AC + G_BD - G_AD - G_BC = delta',
            'energies': {k: str(values[k]) for k in signs}, 'delta': str(delta),
            'solved': missing, 'residual': str(residual), 'exactly_consistent': residual == 0,
            'energy_basis': spec['energy_basis'], 'reference_state': spec['reference_state'],
            'assumption': spec['assumption'], 'advisory_only': True,
            'interpretation': 'Algebra under a caller-supplied reciprocal constraint at a common state. Site labels A/B and C/D must denote a valid two-site rectangle with all other occupations fixed. This does not establish symmetry, EBEF equivalence, or physical validity.'}
