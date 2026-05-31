"""DONE check: scan a real Python source root and answer every non-graph metric
without error. Graph-dependent measures (Martin, dep cycles) are expected to
raise NotImplementedError and are excluded."""
from pathlib import Path
from slop.model import scan_corpus
from slop.component.identity import ComponentKind

def test_every_non_graph_metric_answers_on_real_corpus():
    corpus = scan_corpus(Path(__file__).resolve().parents[1] / "src" / "slop" / "component", config=None)
    # aggregatable complexity at the top
    assert corpus.cyclomatic() >= 0 and corpus.volume() >= 0.0
    # analysis-wide
    assert isinstance(corpus.orphans(), list)
    assert isinstance(corpus.duplication(), list)
    callables = list(corpus._iter_callables())
    classes = list(corpus._iter_classes())
    assert callables and classes
    for c in callables[:50]:
        c.cyclomatic(); c.cognitive(); c.combinatorial(); c.volume(); c.halstead_density()
        c.magic_literals(); c.mutated_parameters(); c.sentinel_parameters()
    for k in classes[:50]:
        k.dit(); k.noc(); k.cbo(); k.method_count(); k.ck()
    for r in corpus.realms():
        for pkg in r.packages():
            pkg.is_runt()
            for mod in pkg.modules():
                mod.definition_count(); mod.escape_hatch_density()
                mod.redundant_siblings(); mod.call_islands(); mod.clone_clusters()
                mod.lexicon().hapax_ratio()
