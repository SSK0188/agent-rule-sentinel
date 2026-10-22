"""Local-only, non-destructive project instruction synchronization."""
from __future__ import annotations

import difflib
import os
import re
import secrets
import stat
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SOURCE = Path('.agent-rule-sentinel/source.md')
TARGETS = {'codex': Path('AGENTS.md'), 'claude': Path('CLAUDE.md')}
START = '<!-- agent-rule-sentinel:BEGIN; managed block; edits will be replaced -->'
END = '<!-- agent-rule-sentinel:END -->'
MAX_BYTES = 1024 * 1024

class GuardError(Exception):
    """A refusal to proceed safely."""

@dataclass(frozen=True)
class Change:
    target: str
    path: Path
    before: str | None
    after: str

    @property
    def dirty(self) -> bool:
        return self.before != self.after


def _checked_path(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or '..' in relative.parts:
        raise GuardError(f'Unsafe path: {relative}')
    root = root.expanduser().absolute()
    if root.is_symlink() or not root.is_dir():
        raise GuardError(f'Project root must be a real directory: {root}')
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise GuardError(f'Refusing symbolic link: {current}')
    if current.exists() and not current.is_file():
        raise GuardError(f'Expected a regular file: {current}')
    return current


def _read(path: Path) -> str | None:
    if not path.exists():
        return None
    if path.stat().st_size > MAX_BYTES:
        raise GuardError(f'File exceeds {MAX_BYTES} bytes: {path}')
    try:
        with path.open('r', encoding='utf-8', newline='') as stream:
            return stream.read()
    except (UnicodeDecodeError, OSError) as error:
        raise GuardError(f'Cannot read UTF-8 file {path}: {error}') from error


_LEAK_PATTERNS = (
    re.compile(r'-----BEGIN (?:OPENSSH |RSA |EC |DSA )?PRIVATE KEY-----'),
    re.compile(r'(?i)\b(?:api[_-]?key|access[_-]?token|secret|password)\b\s*[:=]\s*["\']?[^\s"\']{8,}'),
    re.compile(r'\bsk-[a-zA-Z0-9_-]{20,}\b'),
    re.compile(r'\bgh[pousr]_[a-zA-Z0-9]{20,}\b'),
)

def validate_source(source: str) -> None:
    if not source.strip():
        raise GuardError('Source instructions cannot be empty.')
    if START in source or END in source:
        raise GuardError('Source instructions cannot contain managed-block markers.')
    for pattern in _LEAK_PATTERNS:
        if pattern.search(source):
            raise GuardError('Possible credential in source instructions; inspect before syncing.')


def _managed_block(source: str, newline: str = '\n') -> str:
    normalized = source.replace('\r\n', '\n').replace('\r', '\n').strip()
    return f'{START}{newline}{normalized.replace(chr(10), newline)}{newline}{END}'


def render(existing: str | None, source: str) -> str:
    """Replace exactly one managed block; preserve other text byte-for-byte."""
    newline = '\r\n' if existing is not None and '\r\n' in existing else '\n'
    block = _managed_block(source, newline)
    if existing is None:
        return '# AI Agent Project Instructions\n\n' + block + '\n'
    starts, ends = existing.count(START), existing.count(END)
    if starts == 0 and ends == 0:
        sep = '' if not existing else (newline if existing.endswith('\n') else newline * 2)
        return existing + sep + block + newline
    if starts != 1 or ends != 1:
        raise GuardError('Malformed or duplicate managed-block markers; refusing overwrite.')
    start_index = existing.index(START)
    end_index = existing.index(END)
    if end_index < start_index:
        raise GuardError('Managed-block end marker appears before start.')
    return existing[:start_index] + block + existing[end_index + len(END):]


def plan(root: Path, selected: tuple[str, ...]) -> list[Change]:
    source_path = _checked_path(root, SOURCE)
    source = _read(source_path)
    if source is None:
        raise GuardError(f'Missing {SOURCE}. Run `agent-rule-sentinel init` first.')
    validate_source(source)
    result = []
    for target in dict.fromkeys(selected):
        if target not in TARGETS:
            raise GuardError(f'Unknown target: {target}')
        path = _checked_path(root, TARGETS[target])
        before = _read(path)
        result.append(Change(target, path, before, render(before, source)))
    return result


def preview(changes: list[Change]) -> str:
    lines = []
    for change in changes:
        status = 'CHANGED' if change.dirty else 'UNCHANGED'
        lines.append(f'[{status}] {change.path.name}')
        if change.dirty:
            lines.extend(difflib.unified_diff(
                (change.before or '').splitlines(keepends=True),
                change.after.splitlines(keepends=True),
                fromfile=f'{change.path.name} (current)',
                tofile=f'{change.path.name} (proposed)',
            ))
    return '\n'.join(lines)


def _atomic_write(path: Path, content: str) -> None:
    """Place replacement in the same directory and atomically rename it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.ars-', dir=path.parent)
    try:
        if path.exists():
            os.fchmod(fd, stat.S_IMODE(path.stat().st_mode))
        else:
            os.fchmod(fd, 0o644)
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def apply(root: Path, changes: list[Change]) -> str | None:
    """Back up existing targets first, then apply. No partial writes on preflight error."""
    dirty = [change for change in changes if change.dirty]
    if not dirty:
        return None
    root = root.expanduser().absolute()
    backup_root = root / '.agent-rule-sentinel' / 'backups'
    for directory in (root / '.agent-rule-sentinel', backup_root):
        if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
            raise GuardError(f'Refusing unsafe backup directory: {directory}')
    for change in dirty:
        _checked_path(root, TARGETS[change.target])
        if _read(change.path) != change.before:
            raise GuardError(f'Concurrent change detected in {change.path.name}; run plan again.')
    backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Refuse permissive or symlinked backup folder. Original targets may contain secrets.
    if backup_root.is_symlink() or stat.S_IMODE(backup_root.stat().st_mode) & 0o077:
        raise GuardError('Backup directory must be private (mode 0700).')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    ident = stamp + '-' + secrets.token_hex(4)
    backup_dir = backup_root / ident
    backup_dir.mkdir(mode=0o700)
    try:
        for change in dirty:
            if change.before is not None:
                backup = backup_dir / change.path.name
                backup.write_bytes(change.before.encode('utf-8'))
                backup.chmod(0o600)
        for change in dirty:
            _atomic_write(change.path, change.after)
    except Exception:
        # Restore exactly those already changed, preserve created-file absence.
        for change in dirty:
            try:
                if _read(change.path) != change.after:
                    continue
                if change.before is None:
                    change.path.unlink()
                else:
                    _atomic_write(change.path, change.before)
            except OSError:
                pass
        raise
    return str(backup_dir)


def initialize(root: Path) -> Path:
    path = _checked_path(root, SOURCE)
    if path.exists():
        raise GuardError(f'Source exists; refusing to overwrite {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(path, (
        '# Shared project guidance\n\n'
        '- Describe the project purpose and architecture here.\n'
        '- Explain how to run tests.\n'
        '- List the coding style, review and safety expectations.\n'
        '- Never put keys, passwords or personal secrets here.\n'
    ))
    return path
