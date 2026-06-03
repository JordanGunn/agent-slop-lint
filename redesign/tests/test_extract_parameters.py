"""Language-agnostic parameter extraction — the root fix for the v3 Python-overfit.

Before this, only Python extracted parameters; every other grammar returned () (the
base helper matched Python tree-sitter node types), silently deadening sentinels /
hidden-mutators / imposters / slackers and dropping parameter tokens from the lexicon
on all non-Python code. Each case below asserts the parameter NAMES are recovered.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind

CASES = {
    "m.py":  ("def f(a, b=1, *args): return a\n", ("a", "b", "args")),
    "m.go":  ("package m\nfunc Save(a int, b string) int { return a }\n", ("a", "b")),
    "m.rs":  ("fn process(cfg: i32, name: String) -> i32 { cfg }\n", ("cfg", "name")),
    "M.java": ("class M { int save(int cfg, String name){ return cfg; } }\n", ("cfg", "name")),
    "m.ts":  ("function process(cfg: number, name: string){ return cfg; }\n", ("cfg", "name")),
    "m.js":  ("function process(cfg, name){ return cfg; }\n", ("cfg", "name")),
    "m.rb":  ("def process(cfg, name)\n  cfg\nend\n", ("cfg", "name")),
    "m.c":   ("int save(int cfg, char *name){ return cfg; }\n", ("cfg", "name")),
    "m.cpp": ("int save(int cfg, std::string name){ return cfg; }\n", ("cfg", "name")),
    "m.jl":  ("function process(cfg, name)\n  cfg\nend\n", ("cfg", "name")),
}


def _params(tmp_path: Path, fname: str, src: str):
    (tmp_path / fname).write_text(src)
    corpus = scan_corpus(tmp_path, config=None)

    def walk(s):
        yield s
        for c in s.children():
            yield from walk(c)

    return [c.parameters() for c in walk(corpus) if c.KIND is ScopeKind.CALLABLE]


@pytest.mark.parametrize("fname,case", [(f, c) for f, c in CASES.items()])
def test_parameters_extracted_per_language(tmp_path: Path, fname, case):
    src, expected = case
    got = _params(tmp_path, fname, src)
    assert any(p == expected for p in got), f"{fname}: expected {expected} in {got}"


def test_go_first_param_clustering_now_works(tmp_path: Path):
    # Downstream win: imposters/slackers depend on first_param_clusters, which was
    # dead on Go because parameters were empty. Three Go funcs sharing a first param.
    from slop.metrics.lexical import Lexical
    (tmp_path / "m.go").write_text(
        "package m\n"
        "func LoadCfg(cfg *Config, p string) string { return cfg.path }\n"
        "func SaveCfg(cfg *Config, d string) string { return cfg.dest }\n"
        "func ResetCfg(cfg *Config) string { return cfg.value }\n"
    )
    corpus = scan_corpus(tmp_path, config=None)
    clusters = Lexical.over(corpus).first_param_clusters(min_cluster=3, root=str(tmp_path))
    assert any(c.parameter_name == "cfg" for c in clusters)
