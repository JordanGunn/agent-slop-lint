"""lexical.verbosity — scope-leak verdict only (local verbosity is cut)."""
from __future__ import annotations

from pathlib import Path

from slop.finding import Action, Disposition, Severity
from slop.rules import RULE_REGISTRY
from slop.rules.verbosity import VerbosityRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind


def _corpus_with_spread(tmp_path: Path):
    # tokens user/account/data recur across 3 files (high spread + frequency head)
    for f in ("a.py", "b.py", "c.py"):
        (tmp_path / f).write_text(
            "def get_user(user): return user\n"
            "def get_account(account): return account\n"
            "def get_data(data): return data\n"
        )
    (tmp_path / "big.py").write_text(
        "def load_user_account_data(user, account, data): return 1\n"
    )
    return scan_corpus(tmp_path, config=None)


def test_default_config():
    rc = VerbosityRule.default_config()
    assert VerbosityRule.altitudes == frozenset({ScopeKind.CORPUS})
    assert rc.param("max_tokens") == 3


def test_registered():
    assert any(isinstance(r, VerbosityRule) for r in RULE_REGISTRY)


def test_fires_on_scope_leak(tmp_path: Path):
    corpus = _corpus_with_spread(tmp_path)
    cfg = VerbosityRule.default_config()
    cfg.params["min_mean_spread"] = 3
    findings = list(VerbosityRule().check(corpus, cfg))
    assert len(findings) == 1
    f = findings[0]
    assert f.disposition is Disposition.VERDICT
    assert f.action is Action.NARROW_SCOPE
    assert f.severity is Severity.WARNING
    assert f.metadata["name"] == "load_user_account_data"


def test_local_long_name_is_not_flagged(tmp_path: Path):
    # A long name whose tokens are local (spread 1) is NOT a defect — cut.
    (tmp_path / "solo.py").write_text(
        "def serialize_widget_to_xml_blob(widget): return widget\n"
    )
    corpus = scan_corpus(tmp_path, config=None)
    assert list(VerbosityRule().check(corpus, VerbosityRule.default_config())) == []
