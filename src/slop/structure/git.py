"""Git log primitive for slop.

Provides shared git-history walkers used by history-aware rules (hotspots,
future: change coupling, ownership churn). These are substrate primitives —
they do not emit slop result objects, they just walk `git log` and return
per-commit records (consumed by `structure/hotspots.py`).

Two flavours:
    ``git_log_file_changes``  — ``--name-only``, returns file names per commit.
    ``git_log_numstat``       — ``--numstat``, returns per-file insertions/deletions.

Security contract:
    The `since`, `until`, and `paths` parameters are passed directly to git as
    command-line arguments. To prevent git-flag injection, any value beginning
    with '-' is rejected at call time with ValueError. A `--` sentinel is
    inserted before pathspec arguments so git cannot interpret them as flags.
    subprocess.run is invoked with no shell, so OS-level metacharacter
    injection is impossible by construction.

Failure-mode contract:
    Operational errors (not-a-git-repo, git missing, timeout, git exit
    failure) are captured in result errors with ok=False. The functions
    never raise for these. ValueError is reserved for programmer errors
    (argument validation).
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from slop.shell import run_tool, which

# ---------------------------------------------------------------------------
# Data structures — name-only mode
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CommitRecord:
    """One commit's metadata plus the files it touched."""

    commit_hash: str
    author_date: str                 # ISO 8601 with timezone (%aI)
    files_changed: tuple[str, ...]   # repo-relative, forward-slash
    parent_count: int                # 0 for root, 1 normal, >= 2 merge


@dataclass(frozen=True)
class LogResult:
    """Result of a git log walk (name-only mode)."""

    commits: tuple[CommitRecord, ...]
    repo_root: Path | None           # None if cwd is not inside a git repo
    ok: bool
    is_shallow: bool
    errors: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Data structures — numstat mode
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FileChurnRecord:
    """Per-file line-level churn from a single commit."""

    file: str           # repo-relative, forward-slash
    insertions: int     # lines added (0 for binary)
    deletions: int      # lines removed (0 for binary)


@dataclass(frozen=True)
class NumstatCommitRecord:
    """One commit's metadata plus per-file numstat."""

    commit_hash: str
    author_date: str         # ISO 8601 (%aI)
    files: tuple[FileChurnRecord, ...]
    parent_count: int


@dataclass(frozen=True)
class NumstatResult:
    """Result of a git log walk (numstat mode)."""

    commits: tuple[NumstatCommitRecord, ...]
    repo_root: Path | None
    ok: bool
    is_shallow: bool
    errors: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Pretty-format encoding
# ---------------------------------------------------------------------------
#
# We use ASCII control characters as delimiters in git's --pretty=format:
# because they cannot appear in commit hashes, ISO dates, or parent hash
# lists. Filenames *can* technically contain newlines, but git's default
# core.quotePath setting escapes such names with octal sequences in
# --name-only output, so plain newline-splitting is safe in the common case.
#
# Record separator (0x1e): between commits
# Unit separator (0x1f):   between header fields within a commit

_RS = "\x1e"
_US = "\x1f"
_FORMAT = "%x1e%H%x1f%aI%x1f%P"


# ---------------------------------------------------------------------------
# Security guards
# ---------------------------------------------------------------------------


def _reject_flag_like(value: str, field: str) -> None:
    """Raise ValueError if a caller-supplied value looks like a git flag.

    Defense against git-flag injection: any value beginning with '-' could be
    parsed as an option by git. Reject early.
    """
    if value.startswith("-"):
        raise ValueError(
            f"{field} value {value!r} cannot begin with '-' "
            f"(guards against git-flag injection)"
        )


# ---------------------------------------------------------------------------
# Output parsers
# ---------------------------------------------------------------------------


def _parse_header(block: str) -> tuple[str, str, int, str] | None:
    """Parse a commit header block into (hash, date, parent_count, file_text).

    Returns None for malformed headers.
    """
    newline_idx = block.find("\n")
    if newline_idx == -1:
        header = block
        file_text = ""
    else:
        header = block[:newline_idx]
        file_text = block[newline_idx + 1:]

    header = header.rstrip("\r\n")
    fields = header.split(_US)
    if len(fields) < 3:
        return None

    commit_hash = fields[0]
    author_date = fields[1]
    parents_str = fields[2]
    parent_count = len(parents_str.split()) if parents_str.strip() else 0

    return commit_hash, author_date, parent_count, file_text


def _iter_commit_blocks(output: str) -> Iterator[tuple[str, str, int, str]]:
    """Yield ``(hash, date, parent_count, file_text)`` per commit block.

    Shared skeleton for both log parsers: split on the record separator,
    skip blank blocks, parse each header (dropping malformed ones). The two
    parsers differ only in how they turn ``file_text`` into file records.
    """
    if not output:
        return
    for block in output.split(_RS):
        if not block or not block.strip():
            continue
        parsed = _parse_header(block)
        if parsed is not None:
            yield parsed


def _parse_log_output(output: str) -> list[CommitRecord]:
    """Parse ``git log --name-only`` output into CommitRecords."""
    records: list[CommitRecord] = []
    for commit_hash, author_date, parent_count, file_text in _iter_commit_blocks(output):
        files = tuple(
            line for line in file_text.split("\n") if line and line.strip()
        )
        records.append(CommitRecord(
            commit_hash=commit_hash,
            author_date=author_date,
            files_changed=files,
            parent_count=parent_count,
        ))
    return records


def _parse_numstat_line(line: str) -> FileChurnRecord | None:
    """Parse one ``insertions\\tdeletions\\tpath`` numstat line.

    Binary files report ``-`` counts → mapped to 0. Returns None for blank
    or malformed (< 3 field) lines.
    """
    line = line.strip()
    if not line:
        return None
    parts = line.split("\t", 2)
    if len(parts) < 3:
        return None
    ins_str, del_str, path = parts
    insertions = int(ins_str) if ins_str != "-" else 0
    deletions = int(del_str) if del_str != "-" else 0
    return FileChurnRecord(file=path, insertions=insertions, deletions=deletions)


def _parse_numstat_log_output(output: str) -> list[NumstatCommitRecord]:
    """Parse ``git log --numstat`` output into NumstatCommitRecords."""
    records: list[NumstatCommitRecord] = []
    for commit_hash, author_date, parent_count, file_text in _iter_commit_blocks(output):
        files = tuple(
            rec
            for line in file_text.split("\n")
            if (rec := _parse_numstat_line(line)) is not None
        )
        records.append(NumstatCommitRecord(
            commit_hash=commit_hash,
            author_date=author_date,
            files=files,
            parent_count=parent_count,
        ))
    return records


# ---------------------------------------------------------------------------
# Shared git log infrastructure
# ---------------------------------------------------------------------------


def _validate_log_args(
    since: str | None, until: str | None, paths: list[str] | None,
) -> None:
    """Reject flag-like argument values (git-flag injection guard)."""
    if since is not None:
        _reject_flag_like(since, "since")
    if until is not None:
        _reject_flag_like(until, "until")
    for p in paths or ():
        _reject_flag_like(p, "paths element")


def _resolve_repo_root(cwd: Path) -> tuple[Path | None, list[str]]:
    """Resolve the repo top-level for ``cwd``; ``(None, errors)`` if not a repo."""
    cwd_for_rev = cwd if cwd.is_dir() else cwd.parent
    result = run_tool(["git", "rev-parse", "--show-toplevel"], cwd=cwd_for_rev)
    if not result.ok:
        err = result.stderr.strip() or f"git rev-parse failed (exit {result.returncode})"
        return None, [f"not a git repository: {err}"]
    return Path(result.stdout.strip()), []


def _has_commits(repo_root: Path) -> bool:
    """True if the repo has at least one commit (HEAD resolves)."""
    return run_tool(
        ["git", "rev-parse", "--verify", "--quiet", "HEAD"], cwd=repo_root,
    ).ok


def _detect_shallow(repo_root: Path) -> tuple[bool, list[str]]:
    """Whether the repo is shallow, with a truncation warning if so."""
    result = run_tool(["git", "rev-parse", "--is-shallow-repository"], cwd=repo_root)
    if result.ok and result.stdout.strip() == "true":
        return True, [
            "repository is shallow; git log history is truncated — "
            "run `git fetch --unshallow` for complete history"
        ]
    return False, []


def _build_log_args(
    log_mode: str,
    include_merges: bool,
    since: str | None,
    until: str | None,
    paths: list[str] | None,
) -> list[str]:
    """Assemble the ``git log`` argv for the requested window and mode."""
    args = ["git", "log", log_mode, f"--pretty=format:{_FORMAT}"]
    if not include_merges:
        args.append("--no-merges")
    if since is not None:
        args.append(f"--since={since}")
    if until is not None:
        args.append(f"--until={until}")
    if paths:
        args.append("--")
        args.extend(paths)
    return args


def _run_git_log(
    cwd: Path,
    *,
    since: str | None = None,
    until: str | None = None,
    include_merges: bool = False,
    paths: list[str] | None = None,
    timeout: float = 300.0,
    log_mode: str = "--name-only",
) -> tuple[str | None, Path | None, bool, list[str]]:
    """Run ``git log`` and return raw stdout plus metadata.

    Returns ``(stdout_or_none, repo_root, is_shallow, errors)``. stdout is
    None on failure; "" for an empty repo; errors carries the reasons.
    Orchestrates the validate → resolve → guard → build → run pipeline.
    """
    _validate_log_args(since, until, paths)

    if which("git") is None:
        return None, None, False, [
            "git not found — install git and ensure it is in PATH"
        ]

    repo_root, errors = _resolve_repo_root(cwd)
    if repo_root is None:
        return None, None, False, errors

    if not _has_commits(repo_root):
        return "", repo_root, False, []   # no commits yet — empty, not an error

    is_shallow, errors = _detect_shallow(repo_root)
    args = _build_log_args(log_mode, include_merges, since, until, paths)

    try:
        result = run_tool(args, cwd=repo_root, timeout=timeout)
    except subprocess.TimeoutExpired:
        errors.append(f"git log timed out after {timeout}s")
        return None, repo_root, is_shallow, errors

    if not result.ok:
        errors.append(result.stderr.strip() or f"git log failed (exit {result.returncode})")
        return None, repo_root, is_shallow, errors

    return result.stdout, repo_root, is_shallow, errors


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def _finalize(stdout, repo_root, is_shallow, errors, *, parse, result_cls):
    """Wrap parser output (or a failure) in the result dataclass.

    ``LogResult`` and ``NumstatResult`` share field names, so one builder
    serves both — collapsing the near-identical tails of the two walkers.
    """
    commits = () if stdout is None else tuple(parse(stdout))
    return result_cls(
        commits=commits,
        repo_root=repo_root,
        ok=stdout is not None,
        is_shallow=is_shallow,
        errors=tuple(errors),
    )


def git_log_file_changes(
    cwd: Path,
    *,
    since: str | None = None,
    until: str | None = None,
    include_merges: bool = False,
    paths: list[str] | None = None,
    timeout: float = 300.0,
) -> LogResult:
    """Walk ``git log --name-only`` and return per-commit file-change records.

    Args:
        cwd: Any path inside the git repo.
        since: Git-style time specifier (``"90 days ago"``, ``"2025-01-01"``).
        until: Upper bound on author date, same format as ``since``.
        include_merges: If False (default), merge commits are excluded.
        paths: Pathspec limits. Each element must not begin with ``-``.
        timeout: Seconds to wait for ``git log`` (default 300).

    Returns:
        :class:`LogResult`. ``ok=False`` on operational errors.

    Raises:
        ValueError: If any argument begins with ``-``.
    """
    stdout, repo_root, is_shallow, errors = _run_git_log(
        cwd, since=since, until=until, include_merges=include_merges,
        paths=paths, timeout=timeout, log_mode="--name-only",
    )
    return _finalize(
        stdout, repo_root, is_shallow, errors,
        parse=_parse_log_output, result_cls=LogResult,
    )


def git_log_numstat(
    cwd: Path,
    *,
    since: str | None = None,
    until: str | None = None,
    include_merges: bool = False,
    paths: list[str] | None = None,
    timeout: float = 300.0,
) -> NumstatResult:
    """Walk ``git log --numstat`` and return per-commit per-file line stats.

    Same interface as :func:`git_log_file_changes`, but returns
    :class:`NumstatResult` with per-file insertion/deletion counts
    instead of bare file names.

    Args:
        cwd: Any path inside the git repo.
        since: Git-style time specifier.
        until: Upper bound on author date.
        include_merges: If False (default), merge commits are excluded.
        paths: Pathspec limits.
        timeout: Seconds to wait for ``git log`` (default 300).

    Returns:
        :class:`NumstatResult`. ``ok=False`` on operational errors.

    Raises:
        ValueError: If any argument begins with ``-``.
    """
    stdout, repo_root, is_shallow, errors = _run_git_log(
        cwd, since=since, until=until, include_merges=include_merges,
        paths=paths, timeout=timeout, log_mode="--numstat",
    )
    return _finalize(
        stdout, repo_root, is_shallow, errors,
        parse=_parse_numstat_log_output, result_cls=NumstatResult,
    )
