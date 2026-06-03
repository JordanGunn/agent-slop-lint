"""metrics/lexical Lexical view — entity/vocabulary foundation over the scope tree."""
from __future__ import annotations

from pathlib import Path

from slop.metrics.lexical import Lexical
from slop.scope import scan_corpus

SRC = '''\
def process_user_data(user, mode):
    return user

class UserAccountManager:
    def save(self):
        return 1

def load(path):
    return path
'''


def _lexical(tmp_path: Path) -> Lexical:
    (tmp_path / "m.py").write_text(SRC)
    return Lexical.over(scan_corpus(tmp_path, config=None))


def test_named_entities_split_functions_and_classes(tmp_path: Path):
    lx = _lexical(tmp_path)
    ents = {e.name: e for e in lx.named_entities()}
    assert ents["process_user_data"].kind == "function"
    assert ents["process_user_data"].tokens == ("process", "user", "data")
    assert ents["UserAccountManager"].kind == "class"
    assert ents["UserAccountManager"].tokens == ("User", "Account", "Manager")
    assert ents["process_user_data"].language == "python"
    assert ents["process_user_data"].line == 1


def test_callables_excludes_classes(tmp_path: Path):
    lx = _lexical(tmp_path)
    names = {c.name for c in lx.callables()}
    assert "process_user_data" in names and "load" in names
    assert "UserAccountManager" not in names


def test_token_locations_maps_vocab_to_files(tmp_path: Path):
    lx = _lexical(tmp_path)
    locs = lx.token_locations()
    assert "user" in locs and locs["user"] == {str(tmp_path / "m.py")}
    # body identifiers (return path) are NOT in the entity/param vocabulary
    assert "return" not in locs


def test_frequency_head_orders_by_count(tmp_path: Path):
    lx = _lexical(tmp_path)
    head = lx.frequency_head(threshold=1)
    # 'user' occurs in the function name, the param, and the class name → top.
    assert head[0][0] == "user" and head[0][1] >= 3
