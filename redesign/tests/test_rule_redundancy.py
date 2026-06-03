"""structure.redundancy — sibling-callee overlap, REVIEW@WARNING, project-name precision."""
from __future__ import annotations

from pathlib import Path

from slop.finding import Action, Disposition, Severity
from slop.rules import RULE_REGISTRY
from slop.rules.redundancy import RedundancyRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind

# f1/f2 share three project helpers — genuine redundancy.
PROJECT_OVERLAP = '''\
def helper_a(): pass
def helper_b(): pass
def helper_c(): pass

def f1():
    helper_a(); helper_b(); helper_c()

def f2():
    helper_a(); helper_b(); helper_c()
'''

# parse_a/parse_b share only stdlib methods — must NOT be flagged (precision fix).
STDLIB_OVERLAP = '''\
def parse_a(s):
    return s.strip().split(",").pop()

def parse_b(s):
    return s.strip().split(";").pop()
'''


def _module(tmp_path: Path, src: str):
    (tmp_path / "m.py").write_text(src)
    return scan_corpus(tmp_path, config=None).realms()[0].packages()[0].modules()[0]


def test_default_config():
    rc = RedundancyRule.default_config()
    assert RedundancyRule.altitudes == frozenset({ScopeKind.MODULE})
    assert rc.param("min_shared") == 3


def test_registered():
    assert any(isinstance(r, RedundancyRule) for r in RULE_REGISTRY)


def test_fires_on_shared_project_helpers(tmp_path: Path):
    mod = _module(tmp_path, PROJECT_OVERLAP)
    findings = list(RedundancyRule().check(mod, RedundancyRule.default_config()))
    assert len(findings) == 1
    f = findings[0]
    assert f.disposition is Disposition.VERDICT
    assert f.action is Action.REVIEW
    assert f.severity is Severity.WARNING        # REVIEW caps at WARNING
    assert f.value == 3
    assert {f.metadata["left"], f.metadata["right"]} == {"f1", "f2"}


def test_stdlib_only_overlap_is_not_flagged(tmp_path: Path):
    # parse_a/parse_b share strip/split/pop — stdlib methods, not project callees.
    mod = _module(tmp_path, STDLIB_OVERLAP)
    cfg = RedundancyRule.default_config()
    cfg.params["min_shared"] = 2   # even at a low floor, stdlib overlap must not fire
    assert list(RedundancyRule().check(mod, cfg)) == []
