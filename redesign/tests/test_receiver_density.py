"""Member-access (receiver-call) density is language-agnostic.

Before the ``member_access_patterns`` grammar fact, ``profile._receiver_call_count``
hardcoded Python's ``attribute``/``subscript`` node types, so the receiver-density
signal — which drives the first-param-cluster ``missing_class`` / ``dispatch_family``
classification — read 0 on every non-Python language. These cases assert the signal
is now non-zero where a shared first parameter is genuinely dereferenced as a receiver.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from slop.ast.grammar import GRAMMARS_BY_ID
from slop.metrics.lexical import Lexical
from slop.metrics.lexical.profile import _receiver_call_count
from slop.scope import scan_corpus

# 3 callables per language, each sharing first param ``cfg`` and dereferencing it as a
# receiver (member access + index). Three so they pass first_param_clusters min_cluster.
CASES = {
    "m.go": (
        "package m\n"
        "func LoadCfg(cfg *Config, p string) string { return cfg.path + cfg.root }\n"
        "func SaveCfg(cfg *Config, d string) string { return cfg.dest + cfg.root }\n"
        "func ResetCfg(cfg *Config) string { return cfg.value + cfg.root }\n"
    ),
    "m.rs": (
        "fn load_cfg(cfg: Config, p: String) -> i32 { cfg.path + cfg.root }\n"
        "fn save_cfg(cfg: Config, d: String) -> i32 { cfg.dest + cfg.root }\n"
        "fn reset_cfg(cfg: Config) -> i32 { cfg.value + cfg.root }\n"
    ),
    "M.java": (
        "class M {\n"
        "  int loadCfg(Config cfg, String p){ return cfg.path + cfg.root; }\n"
        "  int saveCfg(Config cfg, String d){ return cfg.dest + cfg.root; }\n"
        "  int resetCfg(Config cfg){ return cfg.value + cfg.root; }\n"
        "}\n"
    ),
}


@pytest.mark.parametrize("fname,src", list(CASES.items()))
def test_receiver_density_nonzero_per_language(tmp_path: Path, fname, src):
    (tmp_path / fname).write_text(src)
    corpus = scan_corpus(tmp_path, config=None)
    clusters = Lexical.over(corpus).first_param_clusters(min_cluster=3, root=str(tmp_path))
    cfg_clusters = [c for c in clusters if c.parameter_name == "cfg"]
    assert cfg_clusters, f"{fname}: expected a 'cfg' first-param cluster"
    assert any(c.mean_receiver_calls > 0 for c in cfg_clusters), (
        f"{fname}: receiver density still 0 — member_access_patterns not wired"
    )


def test_member_access_patterns_declared_for_parsing_grammars():
    """Every grammar that parses real member access declares its patterns; the base
    default (empty) would silently zero the signal."""
    expect_nonempty = {"python", "go", "rust", "julia", "java", "c", "cpp",
                       "javascript", "typescript", "ruby"}
    for gid, grammar in GRAMMARS_BY_ID.items():
        if gid in expect_nonempty:
            assert grammar.member_access_patterns(), f"{gid} declares no member access"


def test_empty_patterns_yields_zero():
    """A grammar with no member-access concept reports 0 (honest 'not measured'),
    not a crash."""
    assert _receiver_call_count(None, b"", "x", ()) == 0
