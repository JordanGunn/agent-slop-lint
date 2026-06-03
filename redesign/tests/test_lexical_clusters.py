"""metrics/lexical first_param_clusters — implicit-receiver clustering + profile.

Exercises the full pipeline: group by first parameter, hierarchical scope claim,
and the body-signal profile (Jaccard / receiver-call density) over v3 raw nodes.
"""
from __future__ import annotations

from pathlib import Path

from slop.metrics.lexical import Lexical
from slop.scope import scan_corpus

# Three functions sharing first param 'cfg', each treating it as a receiver
# (cfg.attr) with near-identical body shape → a missing-class cluster.
RECEIVER = '''\
def load_cfg(cfg, path):
    cfg.path = path
    return cfg.value

def save_cfg(cfg, dest):
    cfg.dest = dest
    return cfg.value

def reset_cfg(cfg):
    cfg.value = 0
    return cfg.value
'''


def _lexical(tmp_path: Path, src: str) -> Lexical:
    (tmp_path / "a.py").write_text(src)
    return Lexical.over(scan_corpus(tmp_path, config=None))


def test_clusters_group_by_first_parameter(tmp_path: Path):
    lx = _lexical(tmp_path, RECEIVER)
    clusters = lx.first_param_clusters(min_cluster=3, root=str(tmp_path))
    assert len(clusters) == 1
    c = clusters[0]
    assert c.parameter_name == "cfg"
    assert {m[0] for m in c.members} == {"load_cfg", "save_cfg", "reset_cfg"}


def test_profile_detects_missing_class(tmp_path: Path):
    lx = _lexical(tmp_path, RECEIVER)
    c = lx.first_param_clusters(min_cluster=3, root=str(tmp_path))[0]
    # high body-shape similarity + receiver-call density → missing_class
    assert c.profile_label == "missing_class"
    assert c.body_jaccard_mean >= 0.7
    assert c.mean_receiver_calls >= 1.0


def test_below_min_cluster_is_silent(tmp_path: Path):
    lx = _lexical(tmp_path, RECEIVER)
    # only 3 members; a floor of 4 yields nothing
    assert lx.first_param_clusters(min_cluster=4, root=str(tmp_path)) == []
