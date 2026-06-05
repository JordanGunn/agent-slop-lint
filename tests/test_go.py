from pathlib import Path
from slop.metrics.structural.view import Structure
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind

GO = '''\
package m

type Counter struct {
\tn int
}

func (c *Counter) Inc(delta int) {
\tif delta > 0 && delta < 100 {
\t\tc.n += delta
\t}
\tfor i := 0; i < delta; i++ {
\t\tc.n++
\t}
}

func Add(a int, b int) int {
\treturn a + b
}
'''

def test_go_carves_and_reparents(tmp_path: Path):
    (tmp_path / "m.go").write_text(GO)
    realm = scan_corpus(tmp_path, config=None).realms()[0]
    assert realm.language == "go"
    mod = realm.packages()[0].modules()[0]
    counter = next(c for c in mod.children() if c.KIND == ScopeKind.CLASS)
    assert [m.name for m in counter.methods()] == ["Inc"]   # receiver method reparented
    assert Structure.over(counter.methods()[0]).cyclomatic() == 4
    add = next(c for c in mod.children() if c.KIND == ScopeKind.CALLABLE and c.name == "Add")
    assert Structure.over(add).cyclomatic() == 1
