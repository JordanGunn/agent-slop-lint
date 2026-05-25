"""Tests for ``Lexicon`` distribution + scope-enumeration methods.

Covers ``frequencies`` / ``modal_tokens`` / ``alphabet`` / ``coverage`` /
``overlap`` / ``token_locations`` and the ``by_file`` / ``by_package``
scope axes — the substrate the lexical-signal-to-corrective-action
research line consumes.
"""
from __future__ import annotations

from pathlib import Path

from slop.lexicon.affix import UNIVERSAL_NOISE
from slop.tree.tree import Tree


def _lexicon(root: Path):
    t = Tree(root)
    t.scan()
    return t.lexicon


def _write(root: Path, rel: str, src: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(src)
    return path


# ---------------------------------------------------------------------------
# frequencies / modal_tokens / alphabet
# ---------------------------------------------------------------------------


class TestFrequencies:
    def test_counts_callable_name_tokens(self, tmp_path: Path):
        _write(tmp_path, "a.py",
               "def parse_user(data):\n    pass\n"
               "def parse_admin(data):\n    pass\n")
        freq = _lexicon(tmp_path).frequencies()
        assert freq["parse"] == 2
        assert freq["user"] == 1
        assert freq["admin"] == 1
        # `data` comes from parameter tokens (include_parameters default True).
        assert freq["data"] == 2

    def test_excludes_self_and_cls_parameters(self, tmp_path: Path):
        _write(tmp_path, "a.py",
               "class Box:\n"
               "    def open(self, key):\n        pass\n"
               "    @classmethod\n    def make(cls, name):\n        pass\n")
        freq = _lexicon(tmp_path).frequencies()
        assert "self" not in freq
        assert "cls" not in freq
        assert freq["key"] == 1
        assert freq["name"] == 1

    def test_include_parameters_false_drops_param_tokens(self, tmp_path: Path):
        _write(tmp_path, "a.py", "def f(customer):\n    pass\n")
        freq = _lexicon(tmp_path).frequencies(include_parameters=False)
        assert "customer" not in freq
        assert freq["f"] == 1

    def test_exclude_filters_listed_tokens(self, tmp_path: Path):
        _write(tmp_path, "a.py",
               "def get_user_id(data):\n    pass\n"
               "def fetch_user_id(data):\n    pass\n")
        freq = _lexicon(tmp_path).frequencies(exclude=frozenset({"id"}))
        assert "id" not in freq
        assert freq["user"] == 2

    def test_class_name_contributes_tokens(self, tmp_path: Path):
        _write(tmp_path, "a.py", "class HTTPClient:\n    pass\n")
        freq = _lexicon(tmp_path).frequencies()
        assert freq["http"] == 1
        assert freq["client"] == 1


class TestModalTokens:
    def test_top_k_descending_by_count(self, tmp_path: Path):
        _write(tmp_path, "a.py",
               "def render_quiet(): pass\n"
               "def render_human(): pass\n"
               "def render_json(): pass\n"
               "def format_quiet(): pass\n"
               "def format_human(): pass\n"
               "def aggregate(): pass\n")
        top = _lexicon(tmp_path).modal_tokens(top=2)
        assert top[0][0] == "render"
        assert top[0][1] == 3
        assert top[1][1] == 2  # render=3, format=2, quiet=2, human=2

    def test_exclude_applies_before_ranking(self, tmp_path: Path):
        # "data" would otherwise tie or win; UNIVERSAL_NOISE doesn't drop
        # it but a caller-supplied exclude does.
        _write(tmp_path, "a.py",
               "def a(data): pass\n"
               "def b(data): pass\n"
               "def c(data): pass\n"
               "def get_user(): pass\n")
        top = _lexicon(tmp_path).modal_tokens(
            top=1, exclude=frozenset({"data"}),
        )
        # With data excluded, every remaining token is count 1; assert
        # data didn't sneak through.
        assert all(t != "data" for t, _ in top)


class TestAlphabet:
    def test_returns_distinct_tokens(self, tmp_path: Path):
        _write(tmp_path, "a.py",
               "def parse_user(data): pass\n"
               "def parse_user_again(data): pass\n")
        alpha = _lexicon(tmp_path).alphabet()
        assert alpha == {"parse", "user", "data", "again"}

    def test_exclude_drops_listed(self, tmp_path: Path):
        _write(tmp_path, "a.py", "def get_id_user(): pass\n")
        alpha = _lexicon(tmp_path).alphabet(exclude=UNIVERSAL_NOISE)
        # Newman 14 contains "id"; should drop.
        assert "id" not in alpha
        assert {"get", "user"} <= alpha


# ---------------------------------------------------------------------------
# coverage / overlap
# ---------------------------------------------------------------------------


class TestCoverageAndOverlap:
    def test_coverage_full(self, tmp_path: Path):
        _write(tmp_path, "a.py", "def parse(): pass\n")
        assert _lexicon(tmp_path).coverage({"parse"}) == 1.0

    def test_coverage_partial(self, tmp_path: Path):
        _write(tmp_path, "a.py", "def parse_user(): pass\n")
        # alphabet = {parse, user}; vocab = {parse} → 0.5
        assert _lexicon(tmp_path).coverage({"parse"}) == 0.5

    def test_coverage_empty_alphabet_returns_zero(self, tmp_path: Path):
        # An empty corpus has no tokens.
        assert _lexicon(tmp_path).coverage({"anything"}) == 0.0

    def test_overlap_with_self_is_one(self, tmp_path: Path):
        _write(tmp_path, "a.py", "def parse_user(): pass\n")
        lex = _lexicon(tmp_path)
        assert lex.overlap(lex) == 1.0

    def test_overlap_disjoint_is_zero(self, tmp_path: Path):
        root_a = tmp_path / "a"
        root_b = tmp_path / "b"
        _write(root_a, "x.py", "def alpha(): pass\n")
        _write(root_b, "y.py", "def gamma(): pass\n")
        a = _lexicon(root_a)
        b = _lexicon(root_b)
        assert a.overlap(b) == 0.0

    def test_overlap_partial_jaccard(self, tmp_path: Path):
        root_a = tmp_path / "a"
        root_b = tmp_path / "b"
        _write(root_a, "x.py", "def parse_user(): pass\n")           # {parse, user}
        _write(root_b, "y.py", "def parse_admin(): pass\n")          # {parse, admin}
        a = _lexicon(root_a)
        b = _lexicon(root_b)
        # |{parse}| / |{parse, user, admin}| = 1/3
        assert abs(a.overlap(b) - 1/3) < 1e-9


# ---------------------------------------------------------------------------
# token_locations
# ---------------------------------------------------------------------------


class TestTokenLocations:
    def test_maps_token_to_files(self, tmp_path: Path):
        p1 = _write(tmp_path, "one.py", "def render_pdf(): pass\n")
        p2 = _write(tmp_path, "two.py", "def export_pdf(): pass\n")
        locs = _lexicon(tmp_path).token_locations()
        assert locs["pdf"] == {p1, p2}
        assert locs["render"] == {p1}

    def test_sprawl_candidate_pattern(self, tmp_path: Path):
        # Three files mention "pdf"; no pdf.py exists. Headline
        # research signal.
        for i, name in enumerate(("render", "export", "validate")):
            _write(tmp_path, f"f{i}.py", f"def {name}_pdf(data): pass\n")
        lex = _lexicon(tmp_path)
        locs = lex.token_locations()
        file_stems = {p.stem for p in lex.files()}
        sprawl = {
            tok: files for tok, files in locs.items()
            if len(files) >= 3 and tok not in file_stems
        }
        assert "pdf" in sprawl
        assert len(sprawl["pdf"]) == 3


# ---------------------------------------------------------------------------
# by_file / by_package
# ---------------------------------------------------------------------------


class TestByFile:
    def test_yields_one_lexicon_per_file(self, tmp_path: Path):
        _write(tmp_path, "a.py", "def alpha(): pass\n")
        _write(tmp_path, "b.py", "def beta(): pass\n")
        per_file = dict(_lexicon(tmp_path).by_file())
        assert len(per_file) == 2

    def test_sub_lexicon_isolates_file(self, tmp_path: Path):
        p_a = _write(tmp_path, "a.py", "def alpha(): pass\n")
        _write(tmp_path, "b.py", "def beta(): pass\n")
        for path, sub in _lexicon(tmp_path).by_file():
            if path == p_a:
                assert sub.alphabet() == {"alpha"}
            else:
                assert sub.alphabet() == {"beta"}


class TestByPackage:
    def test_non_recursive_excludes_subdirs(self, tmp_path: Path):
        _write(tmp_path, "pkg/a.py", "def alpha(): pass\n")
        _write(tmp_path, "pkg/sub/b.py", "def beta(): pass\n")
        per_pkg = dict(_lexicon(tmp_path).by_package())
        pkg_dir = tmp_path / "pkg"
        sub_dir = pkg_dir / "sub"
        assert pkg_dir in per_pkg
        assert sub_dir in per_pkg
        # Non-recursive: pkg/ excludes pkg/sub/
        assert per_pkg[pkg_dir].alphabet() == {"alpha"}
        assert per_pkg[sub_dir].alphabet() == {"beta"}

    def test_recursive_includes_subdirs(self, tmp_path: Path):
        _write(tmp_path, "pkg/a.py", "def alpha(): pass\n")
        _write(tmp_path, "pkg/sub/b.py", "def beta(): pass\n")
        per_pkg = dict(_lexicon(tmp_path).by_package(recursive=True))
        pkg_dir = tmp_path / "pkg"
        assert per_pkg[pkg_dir].alphabet() == {"alpha", "beta"}


# ---------------------------------------------------------------------------
# Composition: slicing + distributions
# ---------------------------------------------------------------------------


class TestCooccurrence:
    def test_callable_token_bags_per_function(self, tmp_path: Path):
        _write(tmp_path, "a.py",
               "def parse_pdf(data): pass\n"
               "def render_html(text): pass\n")
        bags = list(_lexicon(tmp_path).callable_token_bags())
        assert {"parse", "pdf", "data"} in bags
        assert {"render", "html", "text"} in bags

    def test_cooccurrences_count_pairs_per_callable(self, tmp_path: Path):
        _write(tmp_path, "a.py",
               "def f(x): pass\n"          # bag = {f, x}
               "def g(x, y): pass\n"       # bag = {g, x, y}
               "def h(x, y): pass\n")      # bag = {h, x, y}
        cooc = _lexicon(tmp_path).cooccurrences()
        # x and y co-occur in g and h → 2
        assert cooc[("x", "y")] == 2
        # f and x co-occur in f only → 1
        assert cooc[("f", "x")] == 1

    def test_packets_surfaces_find_options_pattern(self, tmp_path: Path):
        # Five tokens always travel together in 4 callables; one stray token
        # also appears 4 times but unrelated. min_association=0.9 should
        # surface the packet and exclude the stray.
        _write(tmp_path, "a.py",
               "def find_a(excludes, hidden, ignore, globs, languages): pass\n"
               "def find_b(excludes, hidden, ignore, globs, languages): pass\n"
               "def find_c(excludes, hidden, ignore, globs, languages): pass\n"
               "def find_d(excludes, hidden, ignore, globs, languages): pass\n"
               "def loader(stray): pass\n"
               "def parser(stray): pass\n"
               "def runner(stray): pass\n"
               "def shaper(stray): pass\n")
        packets = _lexicon(tmp_path).packets(
            min_bags=4, min_association=0.9,
        )
        # Find the packet containing 'excludes' — should contain all five
        # FindOptions tokens.
        find_packet = next(p for p in packets if "excludes" in p)
        assert {"excludes", "hidden", "ignore", "globs", "languages"} <= find_packet
        # 'stray' has freq=4 but doesn't tightly travel with any other token
        # (loader/parser/runner/shaper each appear in only one callable).
        assert not any("stray" in p and len(p) >= 3 for p in packets)

    def test_packets_distinguishes_hub_from_packet(self, tmp_path: Path):
        # 'root' is a hub: appears with everything, association low relative
        # to its frequency. 'a' and 'b' are a packet: always together.
        _write(tmp_path, "a.py",
               "def f1(root, a, b): pass\n"
               "def f2(root, a, b): pass\n"
               "def f3(root, a, b): pass\n"
               "def f4(root, x): pass\n"
               "def f5(root, y): pass\n"
               "def f6(root, z): pass\n"
               "def f7(root, q): pass\n")
        packets = _lexicon(tmp_path).packets(
            min_bags=3, min_association=0.8,
        )
        # 'a' and 'b' should appear together in a packet
        ab_packet = next((p for p in packets if "a" in p and "b" in p), None)
        assert ab_packet is not None
        # 'root' should NOT be in that packet (assoc(root, a) = 3/7 < 0.8)
        assert "root" not in ab_packet


class TestFileTokenBags:
    def test_one_bag_per_file_union_of_callable_vocab(self, tmp_path: Path):
        _write(tmp_path, "a.py",
               "def parse_pdf(data): pass\n"
               "def render_pdf(target): pass\n")
        _write(tmp_path, "b.py", "def loader(): pass\n")
        bags = list(_lexicon(tmp_path).file_token_bags())
        assert {"parse", "pdf", "data", "render", "target"} in bags
        assert {"loader"} in bags

    def test_file_scope_packets_surface_module_extraction_candidate(
        self, tmp_path: Path,
    ):
        # "pdf" sprawled across 4 files alongside "format" — module
        # candidate. "stray" appears in 4 files but with no consistent
        # partner — not a packet.
        for i, (verb, partner) in enumerate([
            ("parse", "format"), ("render", "format"),
            ("export", "format"), ("validate", "format"),
        ]):
            _write(tmp_path, f"f{i}.py", f"def {verb}_pdf_{partner}(): pass\n")
        for i, partner in enumerate(["alpha", "beta", "gamma", "delta"]):
            _write(tmp_path, f"g{i}.py", f"def loader_stray_{partner}(): pass\n")
        packets = _lexicon(tmp_path).packets(
            scope="file", min_bags=4, min_association=0.9,
        )
        pdf_packet = next((p for p in packets if "pdf" in p), None)
        assert pdf_packet is not None
        assert {"pdf", "format"} <= pdf_packet
        # 'stray' has freq=4 but its partners alpha/beta/gamma/delta only
        # appear in one file each — no tight packet contains stray.
        assert not any({"stray", "alpha"} <= p for p in packets)


class TestBodyTokenLocations:
    def test_body_identifiers_surface_in_locations(self, tmp_path: Path):
        # `pdf` appears only inside function bodies, not in any
        # function name or parameter. token_locations should miss it;
        # body_token_locations should catch it.
        _write(tmp_path, "a.py",
               "def render(target):\n"
               "    pdf = target.bytes\n"
               "    return pdf\n")
        _write(tmp_path, "b.py",
               "def export(target):\n"
               "    pdf = target.serialise()\n"
               "    return pdf\n")
        lex = _lexicon(tmp_path)
        sig_locs = lex.token_locations()
        body_locs = lex.body_token_locations()
        assert "pdf" not in sig_locs
        assert "pdf" in body_locs
        assert len(body_locs["pdf"]) == 2

    def test_underscore_prefix_skipped(self, tmp_path: Path):
        _write(tmp_path, "a.py",
               "def f():\n"
               "    _private = 1\n"
               "    return _private\n")
        body_locs = _lexicon(tmp_path).body_token_locations()
        # The token would be 'private' if not skipped, but `_private`
        # starts with single underscore.
        assert "private" not in body_locs

    def test_dunder_kept(self, tmp_path: Path):
        _write(tmp_path, "a.py",
               "def f(target):\n"
               "    return target.__class__\n")
        body_locs = _lexicon(tmp_path).body_token_locations()
        # `target` appears as a body identifier (and `class` from __class__)
        assert "target" in body_locs

    def test_exclude_filter(self, tmp_path: Path):
        _write(tmp_path, "a.py",
               "def f(target):\n"
               "    id = target.id\n"
               "    return id\n")
        body_locs = _lexicon(tmp_path).body_token_locations(
            exclude=frozenset({"id"}),
        )
        assert "id" not in body_locs


class TestComposition:
    def test_under_then_frequencies_scopes_correctly(self, tmp_path: Path):
        _write(tmp_path, "pkg_a/x.py", "def render(): pass\n")
        _write(tmp_path, "pkg_b/y.py", "def parse(): pass\n")
        lex = _lexicon(tmp_path)
        a_freq = lex.under(path=str(tmp_path / "pkg_a")).frequencies()
        assert a_freq == {"render": 1}

    def test_package_overlap_research_pattern(self, tmp_path: Path):
        _write(tmp_path, "render/x.py", "def render_pdf(item): pass\n")
        _write(tmp_path, "export/y.py", "def export_pdf(item): pass\n")
        per_pkg = dict(_lexicon(tmp_path).by_package())
        a = per_pkg[tmp_path / "render"]
        b = per_pkg[tmp_path / "export"]
        # Both packages share `pdf` and `item`; render/export are unique.
        # alphabet(a) = {render, pdf, item}; alphabet(b) = {export, pdf, item}
        # Jaccard = |{pdf, item}| / |{render, pdf, item, export}| = 2/4
        assert a.overlap(b) == 0.5
