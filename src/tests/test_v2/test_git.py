"""Characterization tests for git.py's pure output parsers.

git.py was previously untested (exercised only indirectly via hotspots).
These lock the parser behavior before the convergence-cleanup refactor —
RS/US-delimited commit blocks, header fields, name-only vs numstat file
lines, binary files, merge parent counts, and malformed-input skipping.
"""
from __future__ import annotations

from slop.structure.git import (
    _RS,
    _US,
    _parse_log_output,
    _parse_numstat_log_output,
)


def _commit(hash_: str, date: str, parents: str, body: str) -> str:
    """Build one RS-prefixed commit block as git --pretty=format emits it."""
    return f"{_RS}{hash_}{_US}{date}{_US}{parents}\n{body}"


class TestParseLogOutput:
    def test_empty_output(self):
        assert _parse_log_output("") == []

    def test_single_commit_files(self):
        out = _commit("abc123", "2025-01-01T00:00:00+00:00", "", "a.py\nb.py")
        records = _parse_log_output(out)
        assert len(records) == 1
        r = records[0]
        assert r.commit_hash == "abc123"
        assert r.author_date == "2025-01-01T00:00:00+00:00"
        assert r.files_changed == ("a.py", "b.py")
        assert r.parent_count == 0

    def test_multiple_commits(self):
        out = (
            _commit("h1", "d1", "p1", "a.py")
            + _commit("h2", "d2", "p1 p2", "b.py\nc.py")
        )
        records = _parse_log_output(out)
        assert [r.commit_hash for r in records] == ["h1", "h2"]
        assert records[1].parent_count == 2          # merge: two parents
        assert records[1].files_changed == ("b.py", "c.py")

    def test_malformed_block_skipped(self):
        # a block with < 3 header fields is dropped
        out = f"{_RS}only_one_field\nx.py"
        assert _parse_log_output(out) == []


class TestParseNumstatLogOutput:
    def test_empty_output(self):
        assert _parse_numstat_log_output("") == []

    def test_counts_and_binary(self):
        out = _commit("h1", "d1", "", "10\t2\ta.py\n-\t-\tlogo.png")
        records = _parse_numstat_log_output(out)
        assert len(records) == 1
        files = records[0].files
        assert (files[0].file, files[0].insertions, files[0].deletions) == ("a.py", 10, 2)
        # binary "-\t-" maps to (0, 0)
        assert (files[1].file, files[1].insertions, files[1].deletions) == ("logo.png", 0, 0)

    def test_malformed_file_line_skipped(self):
        out = _commit("h1", "d1", "", "10\t2\ta.py\nnotabbed")
        files = _parse_numstat_log_output(out)[0].files
        assert [f.file for f in files] == ["a.py"]

    def test_merge_parent_count(self):
        out = _commit("h1", "d1", "p1 p2 p3", "10\t2\ta.py")
        assert _parse_numstat_log_output(out)[0].parent_count == 3
