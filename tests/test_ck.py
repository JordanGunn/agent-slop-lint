from pathlib import Path
from slop.metrics.structural.view import Structure
from slop.scope import scan_corpus

SRC = '''\
class Base:
    pass

class Mid(Base):
    pass

class Leaf(Mid):
    def m(self):
        x = Base()
        return x
'''

def _classes(tmp_path: Path) -> dict:
    (tmp_path / "ck.py").write_text(SRC)
    mod = scan_corpus(tmp_path, config=None).realms()[0].packages()[0].modules()[0]
    return {c.name: c for c in mod.children() if c.KIND.name == "CLASS"}

def test_dit(tmp_path: Path):
    cs = _classes(tmp_path)
    assert (Structure.over(cs["Base"]).dit(), Structure.over(cs["Mid"]).dit(), Structure.over(cs["Leaf"]).dit()) == (0, 1, 2)

def test_noc(tmp_path: Path):
    cs = _classes(tmp_path)
    assert (Structure.over(cs["Base"]).noc(), Structure.over(cs["Mid"]).noc(), Structure.over(cs["Leaf"]).noc()) == (1, 1, 0)

def test_cbo(tmp_path: Path):
    cs = _classes(tmp_path)
    assert (Structure.over(cs["Base"]).cbo(), Structure.over(cs["Mid"]).cbo(), Structure.over(cs["Leaf"]).cbo()) == (0, 1, 2)

def test_ck_record(tmp_path: Path):
    cs = _classes(tmp_path)
    ck = Structure.over(cs["Leaf"]).ck()
    # `m` reaches no instance member and is reached by none: detached, not a group.
    assert (ck.dit, ck.noc, ck.cbo, ck.nom, ck.lcom4) == (2, 0, 2, 1, 0)
    assert ck.cohesion.detached == ("m",)


# ---- homonymous classes must not merge ------------------------------------
#
# Base classes are written as simple names. Two packages that each define ``Params`` used
# to be merged into one index entry ("last wins"), so every ``Params`` reported the
# combined subclass count and ``Deep`` could chain through the wrong parent.

def _homonyms(tmp_path: Path) -> dict:
    files = {
        "a/__init__.py": "",
        "a/params.py": "class Params:\n    pass\n\nclass A1(Params):\n    pass\n\n"
                       "class A2(Params):\n    pass\n\nclass Deep(A1):\n    pass\n",
        "b/__init__.py": "",
        "b/params.py": "class Params:\n    pass\n\nclass B1(Params):\n    pass\n",
        "c/__init__.py": "",
        "c/use.py": "class Stray(Params):\n    pass\n",
    }
    for rel, body in files.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(body)
    corpus = scan_corpus(tmp_path, config=None)
    return {
        (c.id.spans[0].path.removeprefix(str(tmp_path) + "/"), c.name): c
        for c in corpus._iter_classes()
    }


def test_homonym_classes_count_only_their_own_subclasses(tmp_path: Path):
    cs = _homonyms(tmp_path)
    assert Structure.over(cs[("a/params.py", "Params")]).noc() == 2   # A1, A2
    assert Structure.over(cs[("b/params.py", "Params")]).noc() == 1   # B1


def test_a_base_with_no_nearer_match_is_left_unresolved_not_guessed(tmp_path: Path):
    # c/use.py's Stray names 'Params', which matches both packages equally. Counting it
    # for either would be a guess, so neither Params gains a child.
    cs = _homonyms(tmp_path)
    assert Structure.over(cs[("a/params.py", "Params")]).noc() == 2
    assert Structure.over(cs[("b/params.py", "Params")]).noc() == 1
    assert Structure.over(cs[("c/use.py", "Stray")]).dit() == 0


def test_depth_follows_the_nearest_parent(tmp_path: Path):
    cs = _homonyms(tmp_path)
    assert Structure.over(cs[("a/params.py", "Deep")]).dit() == 2     # Deep -> A1 -> Params
    assert Structure.over(cs[("b/params.py", "B1")]).dit() == 1


def test_ck_says_when_its_numbers_may_not_be_exact(tmp_path: Path):
    cs = _homonyms(tmp_path)
    twin = Structure.over(cs[("a/params.py", "Params")]).ck().caveats
    assert len(twin) == 2 and "shares its name with 1 other class" in twin[0]
    # Stray (c/use.py) names 'Params' but could not be placed on either, so the parent
    # must say its NOC may be undercounted rather than print 2 as if exact.
    assert "1 subclass(es) naming it could not be placed" in twin[1] and "undercounted" in twin[1]
    stray = Structure.over(cs[("c/use.py", "Stray")]).ck().caveats
    assert len(stray) == 1 and "Params" in stray[0] and "not resolved" in stray[0]
    assert Structure.over(cs[("a/params.py", "Deep")]).ck().caveats == ()   # unique name, exact


def test_children_rule_counts_only_this_classes_own_subclasses(tmp_path: Path):
    from slop.config import RuleConfig
    from slop.rules.class_design import ChildrenRule
    cs = _homonyms(tmp_path)
    cfg = RuleConfig(name="class.children", thresholds={"class": 1})
    (violation,) = list(ChildrenRule().check(cs[("a/params.py", "Params")], cfg))
    assert (violation.value, violation.threshold) == (2, 1)   # not 3: b.Params's B1 is not its child
    assert "2 direct subclasses" in violation.message


# ---- an explicit import beats proximity -----------------------------------

def _import_case(tmp_path: Path) -> dict:
    files = {
        "a/__init__.py": "",
        "a/params.py": "class Params:\n    pass\n",
        "b/__init__.py": "",
        "b/params.py": "class Params:\n    pass\n\nclass B1(Params):\n    pass\n",
        # Same package as a.Params, but it extends the Params it IMPORTS from b.
        "a/use.py": "from b.params import Params\n\nclass Mad(Params):\n    pass\n",
    }
    for rel, body in files.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(body)
    corpus = scan_corpus(tmp_path, config=None)
    return {
        (c.id.spans[0].path.removeprefix(str(tmp_path) + "/"), c.name): c
        for c in corpus._iter_classes()
    }


def test_an_imported_base_beats_a_nearer_homonym(tmp_path: Path):
    cs = _import_case(tmp_path)
    # Proximity alone would attach Mad to a/params.py (same package). The import says b.
    assert Structure.over(cs[("b/params.py", "Params")]).noc() == 2    # B1 and Mad
    assert Structure.over(cs[("a/params.py", "Params")]).noc() == 0
    assert Structure.over(cs[("a/use.py", "Mad")]).dit() == 1


def test_a_resolved_import_leaves_no_ambiguity_note_on_the_child(tmp_path: Path):
    cs = _import_case(tmp_path)
    assert Structure.over(cs[("a/use.py", "Mad")]).ck().caveats == ()
