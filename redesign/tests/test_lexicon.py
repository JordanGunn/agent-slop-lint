from pathlib import Path
from slop.model import scan_corpus
from slop.component.identity import ComponentKind

SRC = '''\
def process_data(raw_input):
    parsed_value = parse(raw_input)
    return parsed_value

class Widget:
    def render_widget(self):
        return self.widget_state
'''

def _corpus(tmp_path: Path):
    (tmp_path / "proc.py").write_text(SRC)
    return scan_corpus(tmp_path, config=None)

def test_lexicon_exists_at_every_scope(tmp_path: Path):
    c = _corpus(tmp_path)
    mod = c.realms()[0].packages()[0].modules()[0]
    cls = next(x for x in mod.children() if x.KIND == ComponentKind.CLASS)
    for comp in (c, c.realms()[0], mod, cls):
        assert comp.lexicon().significant_token_count() >= 0

def test_tokenisation_and_noise(tmp_path: Path):
    mod = _corpus(tmp_path).realms()[0].packages()[0].modules()[0]
    toks = set(mod.lexicon().tokens())
    assert {"process", "data", "raw", "input", "parse", "parsed", "value", "render", "widget", "state"} <= toks
    assert "result" not in toks  # Newman-14 noise

def test_class_lexicon_scoped(tmp_path: Path):
    mod = _corpus(tmp_path).realms()[0].packages()[0].modules()[0]
    cls = next(x for x in mod.children() if x.KIND == ComponentKind.CLASS)
    assert set(cls.lexicon().tokens()) == {"render", "self", "state", "widget"}

def test_hapax_in_range(tmp_path: Path):
    c = _corpus(tmp_path)
    assert 0.0 <= c.lexicon().hapax_ratio() <= 1.0

def test_slice_is_per_file_superset(tmp_path: Path):
    c = _corpus(tmp_path)
    mod = c.realms()[0].packages()[0].modules()[0]
    sliced = set(c.lexicon().slice(mod.extent).tokens())
    assert set(mod.lexicon().tokens()) <= sliced  # module tokens within the file slice
