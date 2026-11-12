import argparse
import json
import sys
from pathlib import Path
from .linear import basis, reciprocal
from .core import audit, compare, library, plan, recommend, validate, search


def main(argv=None):
    p = argparse.ArgumentParser(description='Source-backed CALPHAD model screening (advisory prototype)')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('recipes')
    q = sub.add_parser('search')
    q.add_argument('--text', default='')
    q.add_argument('--topic')
    for command in ('audit', 'recommend', 'plan', 'validate', 'basis', 'reciprocal'):
        q = sub.add_parser(command)
        q.add_argument('spec', type=Path)
        if command == 'plan':
            q.add_argument('--limit', type=int, default=20)
    q = sub.add_parser('compare'); q.add_argument('spec', type=Path); q.add_argument('other', type=Path)
    args = p.parse_args(argv)
    try:
        if args.command == 'recipes':
            result = library()
        elif args.command == 'search':
            result = search(args.text, args.topic)
        else:
            spec = json.loads(args.spec.read_text())
            if args.command == 'validate':
                errors = validate(spec)
                result = {'valid': not errors, 'errors': errors}
            elif args.command == 'compare':
                result = compare(spec, json.loads(args.other.read_text()))
            elif args.command == 'plan':
                result = plan(spec, args.limit)
            else:
                result = {'audit': audit, 'recommend': recommend, 'basis': basis, 'reciprocal': reciprocal}[args.command](spec)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 2 if args.command == 'validate' and errors else 0
    except (ValueError, OSError) as e:
        print(json.dumps({'error': str(e)}), file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())
