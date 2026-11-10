"""DONE check: scan a real Python source root and answer every non-graph metric
without error. Graph-dependent measures (Martin, dep cycles) are expected to
raise NotImplementedError and are excluded."""
from pathlib import Path
from slop.metrics.structural.view import Structure
from slop.scope import scan_corpus

def test_every_non_graph_metric_answers_on_real_corpus():
    corpus = scan_corpus(Path(__file__).resolve().parents[1] / "src" / "slop" / "scope", config=None)
    # aggregatable complexity at the top
    assert Structure.over(corpus).cyclomatic() >= 0 and Structure.over(corpus).volume() >= 0.0
    # analysis-wide
    assert isinstance(Structure.over(corpus).duplication(), list)
    callables = list(corpus._iter_callables())
    classes = list(corpus._iter_classes())
    assert callables and classes
    for c in callables[:50]:
        Structure.over(c).cyclomatic(); Structure.over(c).cognitive(); Structure.over(c).combinatorial(); Structure.over(c).volume()
        Structure.over(c).magic_literals()
    for k in classes[:50]:
        Structure.over(k).dit(); Structure.over(k).noc(); Structure.over(k).cbo(); Structure.over(k).method_count(); Structure.over(k).ck()
    for r in corpus.realms():
        for pkg in r.packages():
            for mod in pkg.modules():
                Structure.over(mod).definition_count(); Structure.over(mod).clone_clusters()
                mod.lexicon().hapax_ratio()
