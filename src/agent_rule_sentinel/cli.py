"""Command-line interface for Agent Rule Sentinel."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .core import DEFAULT_TARGETS, GuardError, TARGETS, apply, initialize, plan, preview
from .features import (
    apply_adopt, apply_undo, diagnose, plan_adopt, plan_undo, preview_undo,
)

VERSION = '0.2.0.dev0'


def _select_targets(args: argparse.Namespace) -> tuple[str, ...]:
    if getattr(args, 'all', False) and getattr(args, 'target', None):
        raise GuardError('Use either --all or --target, not both.')
    if getattr(args, 'all', False):
        return tuple(TARGETS)
    return tuple(args.target or DEFAULT_TARGETS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog='agent-rule-sentinel',
        description='Review and synchronize shared AI coding instructions safely.',
    )
    parser.add_argument('--root', type=Path, default=Path.cwd(),
                        help='Project root (default: current directory)')
    parser.add_argument('--version', action='version', version=f'%(prog)s {VERSION}')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('init', help='Create shared source.md (never overwrites)')
    for name in ('plan', 'check', 'sync', 'doctor'):
        cmd = commands.add_parser(name, help={
            'plan': 'Preview changes without writing',
            'check': 'Return nonzero if files have drifted (CI-friendly)',
            'sync': 'Write only when --apply is explicitly supplied',
            'doctor': 'Read-only project diagnostics; optionally JSON',
        }[name])
        cmd.add_argument('--target', choices=sorted(TARGETS), action='append',
                         help='Select target tool (repeatable; default: codex and claude)')
        cmd.add_argument('--all', action='store_true', help='Include all supported targets')
        if name == 'sync':
            cmd.add_argument('--apply', action='store_true',
                             help='Apply reviewed changes and make private backups')
        if name == 'doctor':
            cmd.add_argument('--json', action='store_true', help='Print machine-readable JSON')
    adopt = commands.add_parser('adopt', help='Import an existing unmanaged target into an absent source')
    adopt.add_argument('--target', choices=sorted(TARGETS), required=True)
    adopt.add_argument('--apply', action='store_true',
                       help='Create canonical source file after review')
    undo = commands.add_parser('undo', help='Preview or safely restore a saved snapshot')
    undo.add_argument('--snapshot', help='Snapshot folder name; default: latest compatible')
    undo.add_argument('--target', choices=sorted(TARGETS), action='append',
                      help='Restore only a selected target in the snapshot')
    undo.add_argument('--apply', action='store_true',
                      help='Restore saved files only if current content is unchanged')

    args = parser.parse_args(argv)
    try:
        if args.command == 'init':
            print(f'Created {initialize(args.root)}')
            return 0
        if args.command == 'adopt':
            destination, text = plan_adopt(args.root, args.target)
            print(f'Import {TARGETS[args.target]} -> {destination}, '
                  f'{len(text.encode("utf-8"))} bytes, SHA256 {hashlib.sha256(text.encode("utf-8")).hexdigest()}')
            if args.apply:
                print(f'Created {apply_adopt(args.root, args.target, text)}; source target left unchanged.')
            else:
                print('Preview only. Add --apply to create the shared source.')
            return 0
        if args.command == 'undo':
            recovery = plan_undo(args.root, tuple(args.target) if args.target else None,
                                 args.snapshot)
            print(preview_undo(recovery))
            if args.apply:
                apply_undo(args.root, recovery)
                print(f'Restored {len(recovery.items)} target(s) from {recovery.snapshot}.')
            else:
                print('Preview only. Add --apply to restore these target(s).')
            return 0

        selected = _select_targets(args)
        if args.command == 'doctor':
            status, details = diagnose(args.root, selected)
            if args.json:
                print(json.dumps(details, indent=2))
            else:
                print(f'Source: {details["source"]}')
                for target, state in details['targets'].items():
                    print(f'{target}: {state}')
                for value in details.get('errors', {}).values():
                    print(f'ERROR: {value}', file=sys.stderr)
                if 'error' in details:
                    print(f'ERROR: {details["error"]}', file=sys.stderr)
            return status

        changes = plan(args.root, selected)
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
