"""Explicit, conservative workflows for importing, diagnosing, and recovering rules."""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import stat
from dataclasses import dataclass
from pathlib import Path

from .core import (
    DEFAULT_TARGETS, END, SOURCE, START, TARGETS, GuardError,
    _atomic_write, _checked_path, _read, plan, validate_source,
)

_SNAPSHOT_NAME = re.compile(r'\d{8}T\d{6}Z-[0-9a-f]{8}\Z')
_SHA256 = re.compile(r'[0-9a-f]{64}\Z')


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class Recovery:
    target: str
    path: Path
    current: str
    original: str | None


@dataclass(frozen=True)
class RecoveryPlan:
    snapshot: str
    items: tuple[Recovery, ...]


def _snapshot_path(root: Path, snapshot: str) -> Path:
    if not _SNAPSHOT_NAME.fullmatch(snapshot):
        raise GuardError('Invalid backup snapshot name.')
    manifest_path = Path('.agent-rule-sentinel/backups') / snapshot / 'manifest.json'
    safe_manifest = _checked_path(root, manifest_path)
    backup_dir = safe_manifest.parent
    if not backup_dir.is_dir():
        raise GuardError(f'Backup snapshot missing: {snapshot}')
    if stat.S_IMODE(backup_dir.stat().st_mode) & 0o077:
        raise GuardError('Backup snapshot directory must have owner-only permissions.')
    return backup_dir


def list_snapshots(root: Path) -> list[str]:
    """List compatible snapshots without revealing private backup contents."""
    guard = _checked_path(root, Path('.agent-rule-sentinel/backups/.gitignore'))
    backups = guard.parent
    if not backups.exists():
        return []
    candidates: list[tuple[int, str]] = []
    for item in backups.iterdir():
        if not _SNAPSHOT_NAME.fullmatch(item.name) or item.is_symlink() or not item.is_dir():
            continue
        try:
            manifest = _checked_path(
                root, Path('.agent-rule-sentinel/backups') / item.name / 'manifest.json'
            )
            if not manifest.is_file():
                continue
            # Ignore unsuitable snapshot directories rather than listing unusable entries.
            if stat.S_IMODE(item.stat().st_mode) & 0o077:
                continue
            candidates.append((item.stat().st_mtime_ns, item.name))
        except OSError:
            continue
        except GuardError:
            continue
    # Use actual directory modification times rather than the random suffix
    # when two snapshots were produced in the same second.
    return [name for _, name in sorted(candidates, reverse=True)]


def _choose_snapshot(root: Path, requested: str | None) -> str:
    if requested is not None:
        _snapshot_path(root, requested)
        return requested
    candidates = list_snapshots(root)
    if not candidates:
        raise GuardError('No compatible backup snapshots. Older backups require manual restoration.')
    return candidates[0]


def plan_undo(root: Path, target: tuple[str, ...] | None = None,
              snapshot: str | None = None) -> RecoveryPlan:
    """Validate complete snapshot and working files; refuse any changed destination."""
    snapshot = _choose_snapshot(root, snapshot)
    backup_dir = _snapshot_path(root, snapshot)
    raw = _read(_checked_path(root, Path('.agent-rule-sentinel/backups') / snapshot / 'manifest.json'))
    if raw is None:
        raise GuardError('Backup manifest is missing.')
    try:
        manifest = json.loads(raw)
    except (ValueError, TypeError) as error:
        raise GuardError('Invalid backup manifest JSON.') from error
    if not isinstance(manifest, dict) or manifest.get('schema') != 1:
        raise GuardError('Unsupported backup manifest.')
    entries = manifest.get('entries')
    if not isinstance(entries, list) or not entries:
        raise GuardError('Backup manifest has no entries.')
    seen: set[str] = set()
    indexed: dict[str, dict] = {}
    for entry in entries:
        if not isinstance(entry, dict) or entry.get('target') not in TARGETS:
            raise GuardError('Invalid target in backup manifest.')
        name = entry['target']
        before_hash = entry.get('before_sha256')
        after_hash = entry.get('after_sha256')
        if name in seen or (before_hash is not None and
                            (not isinstance(before_hash, str) or
                             not _SHA256.fullmatch(before_hash))) or \
                not isinstance(after_hash, str) or not _SHA256.fullmatch(after_hash):
            raise GuardError('Malformed or duplicate backup entry.')
        seen.add(name)
        indexed[name] = entry
    selected = tuple(dict.fromkeys(target or tuple(indexed)))
    if any(name not in indexed for name in selected):
        raise GuardError('Requested target was not changed by this snapshot.')

    results: list[Recovery] = []
    for name in selected:
        entry = indexed[name]
        original = None
        if entry['before_sha256'] is not None:
            backup_rel = Path('.agent-rule-sentinel/backups') / snapshot / TARGETS[name]
            original = _read(_checked_path(root, backup_rel))
            if original is None or _digest(original) != entry['before_sha256']:
                raise GuardError(f'Backup copy is missing or has changed for {name}.')
        current_path = _checked_path(root, TARGETS[name])
        current = _read(current_path)
        if current is None or _digest(current) != entry['after_sha256']:
            raise GuardError(
                f'{current_path.name} changed since this snapshot; '
                'refusing to overwrite newer work.'
            )
        results.append(Recovery(name, current_path, current, original))
    return RecoveryPlan(snapshot, tuple(results))


def preview_undo(recovery: RecoveryPlan) -> str:
    sections = [f'[SNAPSHOT] {recovery.snapshot}']
    for item in recovery.items:
        sections.append(f'[RESTORE] {item.path.name}' if item.original is not None
                        else f'[REMOVE CREATED FILE] {item.path.name}')
        sections.extend(difflib.unified_diff(
            item.current.splitlines(keepends=True),
            (item.original or '').splitlines(keepends=True),
            fromfile=f'{item.path.name} (now)',
            tofile=f'{item.path.name} (restored)',
        ))
    return '\n'.join(sections)


def apply_undo(root: Path, recovery: RecoveryPlan) -> None:
    """Restore only unchanged destinations; roll back our writes on I/O failure."""
    # Recheck entire snapshot and destination set before touching anything.
    verified = plan_undo(root, tuple(item.target for item in recovery.items),
                         recovery.snapshot)
    if verified != recovery:
        raise GuardError('Backup or target changed during review; preview undo again.')
    changed: list[Recovery] = []
    try:
        for item in verified.items:
            if _read(_checked_path(root, TARGETS[item.target])) != item.current:
                raise GuardError('Target changed during undo; refusing to proceed.')
            if item.original is None:
                item.path.unlink()
            else:
                _atomic_write(item.path, item.original)
            changed.append(item)
    except Exception:
        for item in reversed(changed):
            try:
                actual = _read(_checked_path(root, TARGETS[item.target]))
                if actual == item.original:
                    _atomic_write(item.path, item.current)
            except OSError:
                pass
        raise


def plan_adopt(root: Path, target: str) -> tuple[Path, str]:
    """Read an unmanaged existing target; never overwrite canonical instructions."""
    if target not in TARGETS:
        raise GuardError(f'Unknown target: {target}')
    source_path = _checked_path(root, SOURCE)
    if source_path.exists():
        raise GuardError(f'{SOURCE} already exists. Refusing to overwrite it.')
    content = _read(_checked_path(root, TARGETS[target]))
    if content is None or not content.strip():
        raise GuardError(f'{TARGETS[target]} is missing or empty.')
    if START in content or END in content:
        raise GuardError('Target contains managed markers. Cannot safely adopt it.')
    validate_source(content)
    return source_path, content


def apply_adopt(root: Path, target: str, expected: str) -> Path:
    source_path, current = plan_adopt(root, target)
    if current != expected:
        raise GuardError('Target changed since preview; refusing adoption.')
    source_path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidental clobbering if another process initialized.
    try:
        with source_path.open('x', encoding='utf-8', newline='') as stream:
            stream.write(expected)
            stream.flush()
    except FileExistsError as error:
        raise GuardError('Canonical source appeared during adoption; refusing overwrite.') from error
    return source_path


def diagnose(root: Path, selected: tuple[str, ...] = DEFAULT_TARGETS) -> tuple[int, dict]:
    """Read-only, machine-readable status. 0=clean, 1=drift, 2=unsafe/missing source."""
    result: dict = {'source': 'unknown', 'targets': {}}
    try:
        source_file = _checked_path(root, SOURCE)
        source = _read(source_file)
        if source is None:
            result['source'] = 'missing'
            return 2, result
        validate_source(source)
        result['source'] = 'ok'
    except GuardError as error:
        result['source'] = 'error'
        result['error'] = str(error)
        return 2, result

    status = 0
    for name in selected:
        try:
            changes = plan(root, (name,))
            change = changes[0]
            value = 'drift' if change.dirty else 'ok'
            result['targets'][name] = value
            if change.dirty:
                status = max(status, 1)
        except GuardError as error:
            result['targets'][name] = 'error'
            result.setdefault('errors', {})[name] = str(error)
            status = 2
    return status, result
