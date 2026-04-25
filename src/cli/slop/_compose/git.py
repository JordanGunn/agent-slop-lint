"""Git log primitive for AUx.

Provides shared git-history walkers used by history-aware skills (hotspots,
future: change coupling, ownership churn). Placed in util/ because these are
primitives — they do not emit AUx-shaped result objects, they just walk
`git log` and return per-commit records.

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
from dataclasses import dataclass
from pathlib import Path

from slop._util.subprocess import run_tool, which

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
class GitLogResult:
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
class GitNumstatResult:
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
_FORMAT = f"%x1e%H%x1f%aI%x1f%P"


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


def _parse_log_output(output: str) -> list[CommitRecord]:
    """Parse ``git log --name-only`` output into CommitRecords."""
    if not output:
        return []

    records: list[CommitRecord] = []
    for block in output.split(_RS):
        if not block or not block.strip():
            continue
        parsed = _parse_header(block)
        if parsed is None:
            continue
        commit_hash, author_date, parent_count, file_text = parsed
        files = tuple(
            line for line in file_text.split("\n") if line and line.strip()
        )
        records.append(
            CommitRecord(
                commit_hash=commit_hash,
                author_date=author_date,
                files_changed=files,
                parent_count=parent_count,
            )
        )
    return records


def _parse_numstat_log_output(output: str) -> list[NumstatCommitRecord]:
    """Parse ``git log --numstat`` output into NumstatCommitRecords.

    Each file line is ``insertions\\tdeletions\\tpath``.
    Binary files report ``-\\t-\\tpath`` — mapped to (0, 0).
    """
    if not output:
        return []

    records: list[NumstatCommitRecord] = []
    for block in output.split(_RS):
        if not block or not block.strip():
            continue
        parsed = _parse_header(block)
        if parsed is None:
            continue
        commit_hash, author_date, parent_count, file_text = parsed

        file_records: list[FileChurnRecord] = []
        for line in file_text.split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t", 2)
            if len(parts) < 3:
                continue
            ins_str, del_str, path = parts
            # Binary files: "-\t-\tpath"
            insertions = int(ins_str) if ins_str != "-" else 0
            deletions = int(del_str) if del_str != "-" else 0
            file_records.append(
                FileChurnRecord(file=path, insertions=insertions, deletions=deletions)
            )

        records.append(
            NumstatCommitRecord(
                commit_hash=commit_hash,
                author_date=author_date,
                files=tuple(file_records),
                parent_count=parent_count,
            )
        )
    return records


# ---------------------------------------------------------------------------
# Shared git log infrastructure
# ---------------------------------------------------------------------------


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

    Returns (stdout_or_none, repo_root, is_shallow, errors).
    stdout is None on failure; errors is populated with reasons.
    """
    # --- Argument validation (flag-injection guard) ---
    if since is not None:
        _reject_flag_like(since, "since")
    if until is not None:
        _reject_flag_like(until, "until")
    if paths is not None:
        for p in paths:
            _reject_flag_like(p, "paths element")

    errors: list[str] = []

    # --- Git availability ---
    if which("git") is None:
        return None, None, False, [
            "git not found — install git and ensure it is in PATH"
        ]

    # --- Resolve repo root ---
    cwd_for_rev = cwd if cwd.is_dir() else cwd.parent
    top_result = run_tool(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd_for_rev,
    )
    if not top_result.ok:
        err = top_result.stderr.strip() or f"git rev-parse failed (exit {top_result.returncode})"
        return None, None, False, [f"not a git repository: {err}"]

    repo_root = Path(top_result.stdout.strip())

    # --- Empty-repo short-circuit ---
    head_result = run_tool(
        ["git", "rev-parse", "--verify", "--quiet", "HEAD"],
        cwd=repo_root,
    )
    if not head_result.ok:
        # No commits yet — return empty stdout, not an error
        return "", repo_root, False, []

    # --- Shallow repo detection ---
    shallow_result = run_tool(
        ["git", "rev-parse", "--is-shallow-repository"],
        cwd=repo_root,
    )
    is_shallow = False
    if shallow_result.ok and shallow_result.stdout.strip() == "true":
        is_shallow = True
        errors.append(
            "repository is shallow; git log history is truncated — "
            "run `git fetch --unshallow` for complete history"
        )

    # --- Build log command ---
    log_args: list[str] = [
        "git",
        "log",
        log_mode,
        f"--pretty=format:{_FORMAT}",
    ]
    if not include_merges:
        log_args.append("--no-merges")
    if since is not None:
        log_args.append(f"--since={since}")
    if until is not None:
        log_args.append(f"--until={until}")
    if paths:
        log_args.append("--")
        log_args.extend(paths)

    # --- Run log ---
    try:
        log_result = run_tool(log_args, cwd=repo_root, timeout=timeout)
    except subprocess.TimeoutExpired:
        errors.append(f"git log timed out after {timeout}s")
        return None, repo_root, is_shallow, errors

    if not log_result.ok:
        err = log_result.stderr.strip() or f"git log failed (exit {log_result.returncode})"
        errors.append(err)
        return None, repo_root, is_shallow, errors

    return log_result.stdout, repo_root, is_shallow, errors


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def git_log_file_changes(
    cwd: Path,
    *,
    since: str | None = None,
    until: str | None = None,
    include_merges: bool = False,
    paths: list[str] | None = None,
    timeout: float = 300.0,
) -> GitLogResult:
    """Walk ``git log --name-only`` and return per-commit file-change records.

    Args:
        cwd: Any path inside the git repo.
        since: Git-style time specifier (``"90 days ago"``, ``"2025-01-01"``).
        until: Upper bound on author date, same format as ``since``.
        include_merges: If False (default), merge commits are excluded.
        paths: Pathspec limits. Each element must not begin with ``-``.
        timeout: Seconds to wait for ``git log`` (default 300).

    Returns:
        :class:`GitLogResult`. ``ok=False`` on operational errors.

    Raises:
        ValueError: If any argument begins with ``-``.
    """
    stdout, repo_root, is_shallow, errors = _run_git_log(
        cwd, since=since, until=until, include_merges=include_merges,
        paths=paths, timeout=timeout, log_mode="--name-only",
    )

    if stdout is None:
        return GitLogResult(
            commits=(), repo_root=repo_root, ok=False,
            is_shallow=is_shallow, errors=tuple(errors),
        )

    commits = _parse_log_output(stdout)
    return GitLogResult(
        commits=tuple(commits), repo_root=repo_root, ok=True,
        is_shallow=is_shallow, errors=tuple(errors),
    )


def git_log_numstat(
    cwd: Path,
    *,
    since: str | None = None,
    until: str | None = None,
    include_merges: bool = False,
    paths: list[str] | None = None,
    timeout: float = 300.0,
) -> GitNumstatResult:
    """Walk ``git log --numstat`` and return per-commit per-file line stats.

    Same interface as :func:`git_log_file_changes`, but returns
    :class:`GitNumstatResult` with per-file insertion/deletion counts
    instead of bare file names.

    Args:
        cwd: Any path inside the git repo.
        since: Git-style time specifier.
        until: Upper bound on author date.
        include_merges: If False (default), merge commits are excluded.
        paths: Pathspec limits.
        timeout: Seconds to wait for ``git log`` (default 300).

    Returns:
        :class:`GitNumstatResult`. ``ok=False`` on operational errors.

    Raises:
        ValueError: If any argument begins with ``-``.
    """
    stdout, repo_root, is_shallow, errors = _run_git_log(
        cwd, since=since, until=until, include_merges=include_merges,
        paths=paths, timeout=timeout, log_mode="--numstat",
    )

    if stdout is None:
        return GitNumstatResult(
            commits=(), repo_root=repo_root, ok=False,
            is_shallow=is_shallow, errors=tuple(errors),
        )

    commits = _parse_numstat_log_output(stdout)
    return GitNumstatResult(
        commits=tuple(commits), repo_root=repo_root, ok=True,
        is_shallow=is_shallow, errors=tuple(errors),
    )
