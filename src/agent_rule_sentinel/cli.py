"""Command-line interface for Agent Rule Sentinel."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import GuardError, TARGETS, apply, initialize, plan, preview

VERSION = '0.1.0'


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog='agent-rule-sentinel',
        description='Review and synchronize shared AI coding instructions safely.',
    )
    parser.add_argument('--root', type=Path, default=Path.cwd(), help='Project root (default: current directory)')
    parser.add_argument('--version', action='version', version=f'%(prog)s {VERSION}')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('init', help='Create a canonical source.md without touching agent files')
    for name in ('plan', 'check', 'sync'):
        cmd = commands.add_parser(name, help={
            'plan': 'Preview changes without writing',
            'check': 'Return nonzero if files have drifted (CI-friendly)',
            'sync': 'Write changes only with --apply',
        }[name])
        cmd.add_argument('--target', choices=sorted(TARGETS), action='append',
                         help='Target tool (repeatable; default: both)')
        if name == 'sync':
            cmd.add_argument('--apply', action='store_true', help='Apply proposed changes and make private backups')
    args = parser.parse_args(argv)
    try:
        if args.command == 'init':
            print(f'Created {initialize(args.root)}')
            return 0
        changes = plan(args.root, tuple(args.target or TARGETS))
        print(preview(changes))
        dirty = [change for change in changes if change.dirty]
        if args.command == 'check':
            if dirty:
                print(f'ERROR: {len(dirty)} target(s) out of sync.', file=sys.stderr)
                return 1
            print('All selected targets are in sync.')
            return 0
        if args.command == 'sync':
            if not args.apply:
                print('Preview only. Add --apply to write files.')
            elif dirty:
                backup = apply(args.root, changes)
                print(f'Updated {len(dirty)} target(s). Private backups: {backup}')
            else:
                print('No changes needed.')
        return 0
    except (GuardError, OSError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
