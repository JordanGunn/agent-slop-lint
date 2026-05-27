"""Lexicon view — the substrate lexical rules consume.

A ``Lexicon`` is a windowed view over the identifier-token bag
extracted from the parsed corpus. Lexical rules (sprawl, slackers,
imposters, confusion, hammers, stutter, cowards, tautology, verbosity)
depend on this surface; they do not see the AST tree shape.

The view owns metric computations. Rules call methods like
``first_param_clusters()``; AST walking happens inside the view,
hidden behind the compute API. Records remain pure-data identifiers.

Slicing methods (``under``, ``where``, ``walk``) return NEW ``Lexicon``
instances over the same underlying parse data. Cost is O(1); the view
is a filter, not a copy.

Per-scope analysis composes slicing with the distribution methods
(``frequencies`` / ``modal_tokens`` / ``alphabet`` / ``coverage`` /
``overlap`` / ``token_locations``). The ``by_file`` and ``by_package``
enumerators yield sub-Lexicons restricted to each scope, so research
can iterate distributions per module → package → root cheaply.

See ``docs/planning/codebase.md`` for the locked design.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import (
    AbstractSet,
    Any,
    Callable as TypingCallable,
    Iterable,
    Iterator,
    Mapping,
    Sequence,
)

from slop.lexicon.affix import scope_label
from slop.tree.records import Callable, Occurrence, ParseResult, ScopeKind

import re

_CAMEL_LOWER_UPPER = re.compile(r"([a-z])([A-Z])")
_CAMEL_UPPER_TITLE = re.compile(r"([A-Z]+)([A-Z][a-z])")

_CLASS_LIKE_SCOPE_KINDS: frozenset[ScopeKind] = frozenset({
    ScopeKind.CLASS, ScopeKind.INTERFACE, ScopeKind.STRUCT, ScopeKind.TRAIT,
})


class Lexicon:
    """View over the corpus's identifier-token bag + callable signals.

    Constructed once by ``Tree.scan()``; consumed by lexical rules.
    Immutable by contract: stat queries return new structures; slicing
    returns new ``Lexicon`` instances.
    """

    def __init__(
        self,
        parses: Sequence[ParseResult],
        *,
        filters: Sequence[TypingCallable[[Any], bool]] = (),
    ) -> None:
        self._parses = tuple(parses)
        self._filters = tuple(filters)

        # Per-callable indexes keyed by (path, qualname) — a bare qualname
        # like ``a.f`` collides across same-file-stem corpora; pairing it
        # with the absolute path scopes the lookup to its source file.
        # Records stay pure-data; AST state lives in the view per the
        # views-own-compute principle.
        self._language_by_path: dict[str, str] = {}
        self._callable_by_key: dict[tuple[str, str], Callable] = {}
        self._node_by_key: dict[tuple[str, str], Any] = {}
        self._content_by_path: dict[str, bytes] = {}
        self._parts_by_key: dict[tuple[str, str], tuple[str, ...]] = {}

        for p in parses:
            self._language_by_path[str(p.path)] = p.language
            self._content_by_path[str(p.path)] = p.content
            for c in p.callables:
                key = (str(c.path), c.qualname)
                self._callable_by_key[key] = c
                if c.qualname in p.callable_nodes:
                    self._node_by_key[key] = p.callable_nodes[c.qualname]
                self._parts_by_key[key] = c.path.parts

    # ---- statistical queries -----------------------------------------------
    #
    # All distribution methods delegate to ``_iter_token_locations`` so the
    # token-source contract stays in one place. Tokens come from callable +
    # class-like scope names (snake/Camel-split via ``split_tokens``, lower-
    # cased), plus parameter names if ``include_parameters`` is left True.
    # ``self`` / ``cls`` parameters are always dropped — they're idiomatic
    # receivers, not vocabulary signal. Body-identifier tokens are NOT in
    # the bag by default; bring them in via a separate explicit walk if
    # research demands it.

    def _iter_token_locations(
        self,
        *,
        exclude: frozenset[str] = frozenset(),
        include_parameters: bool = True,
        include_body_identifiers: bool = False,
    ) -> Iterator[tuple[str, Path]]:
        """Yield ``(token, path)`` pairs honouring this view's filters.

        ``include_body_identifiers`` walks each callable's body AST and
        emits tokens from every identifier reference inside (skipping
        single-underscore-prefixed names but keeping dunders). One
        ``(token, path)`` per body occurrence — token-spread analyses
        thus weight body references the same as signature references.
        """
        for entity in self.named_entities():
            entity_path = Path(entity.file)
            for t in entity.tokens:
                tl = t.lower()
                if tl in exclude:
                    continue
                yield tl, entity_path
        if include_parameters:
            for c in self.callables():
                for p in c.parameters:
                    if p.name in ("self", "cls"):
                        continue
                    for t in Lexicon.split_tokens(p.name):
                        tl = t.lower()
                        if tl in exclude:
                            continue
                        yield tl, c.path
        if include_body_identifiers:
            for parse in self._parses:
                content = parse.content
                for c in parse.callables:
                    if not all(f(c) for f in self._filters):
                        continue
                    node = parse.callable_nodes.get(c.qualname)
                    if node is None:
                        continue
                    body = node.child_by_field_name("body") or node
                    for ident in _walk_identifier_nodes(body):
                        name = content[ident.start_byte:ident.end_byte].decode(
                            "utf-8", errors="replace",
                        )
                        if name.startswith("_") and not name.startswith("__"):
                            continue
                        for t in Lexicon.split_tokens(name):
                            tl = t.lower()
                            if tl in exclude:
                                continue
                            yield tl, c.path

    def tokens(
        self,
        *,
        exclude: frozenset[str] = frozenset(),
        include_parameters: bool = True,
    ) -> Iterator[str]:
        """Yield every identifier token in this view, lowercased.

        Pre-tokenisation source: callable names + class-like scope names
        + parameter names. Use ``exclude=UNIVERSAL_NOISE`` (from
        ``slop.lexicon.affix``) to strip Newman 14 + English glue before
        downstream analysis.
        """
        for t, _ in self._iter_token_locations(
            exclude=exclude, include_parameters=include_parameters,
        ):
            yield t

    def frequencies(
        self,
        *,
        exclude: frozenset[str] = frozenset(),
        include_parameters: bool = True,
    ) -> Counter[str]:
        """Token → occurrence-count Counter over this view."""
        return Counter(
            self.tokens(exclude=exclude, include_parameters=include_parameters),
        )

    def modal_tokens(
        self,
        *,
        top: int = 10,
        exclude: frozenset[str] = frozenset(),
        include_parameters: bool = True,
    ) -> list[tuple[str, int]]:
        """Top-``top`` tokens by frequency, descending."""
        return self.frequencies(
            exclude=exclude, include_parameters=include_parameters,
        ).most_common(top)

    def alphabet(
        self,
        *,
        exclude: frozenset[str] = frozenset(),
        include_parameters: bool = True,
    ) -> set[str]:
        """The distinct tokens observed in this view."""
        return set(
            self.tokens(exclude=exclude, include_parameters=include_parameters),
        )

    def coverage(
        self,
        vocabulary: AbstractSet[str],
        *,
        exclude: frozenset[str] = frozenset(),
        include_parameters: bool = True,
    ) -> float:
        """Fraction of this view's distinct tokens that appear in
        ``vocabulary``. Returns ``0.0`` for an empty view."""
        alpha = self.alphabet(
            exclude=exclude, include_parameters=include_parameters,
        )
        if not alpha:
            return 0.0
        return len(alpha & set(vocabulary)) / len(alpha)

    def overlap(
        self,
        other: Lexicon,
        *,
        exclude: frozenset[str] = frozenset(),
        include_parameters: bool = True,
    ) -> float:
        """Jaccard-style overlap between this view's alphabet and
        ``other``'s. Both-empty returns ``1.0``; one-empty returns
        ``0.0``."""
        a = self.alphabet(
            exclude=exclude, include_parameters=include_parameters,
        )
        b = other.alphabet(
            exclude=exclude, include_parameters=include_parameters,
        )
        if not a and not b:
            return 1.0
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    def token_locations(
        self,
        *,
        exclude: frozenset[str] = frozenset(),
        include_parameters: bool = True,
    ) -> dict[str, set[Path]]:
        """Token → set of file paths where the token appears.

        The headline research primitive for sprawl-as-missing-module
        analysis: a token whose ``len(locations) >= N`` but where no
        module by that name exists is a missing-module candidate.

        Source: entity names + parameter names. For body-identifier
        spread (token appears inside function bodies), see
        ``body_token_locations``.
        """
        out: dict[str, set[Path]] = {}
        for t, p in self._iter_token_locations(
            exclude=exclude, include_parameters=include_parameters,
        ):
            out.setdefault(t, set()).add(p)
        return out

    def body_token_locations(
        self,
        *,
        exclude: frozenset[str] = frozenset(),
    ) -> dict[str, set[Path]]:
        """Token → file paths where the token appears as a body identifier.

        Walks each callable's body AST and collects every leaf
        ``identifier`` reference, snake/Camel-split and lowercased.
        Single-underscore-prefixed names are skipped (Python privacy
        convention); dunders kept. Companion to ``token_locations``:
        merge both for full token-spread analysis including in-body
        references.

        Surfaces the "token X is used inside many functions even
        though no function declares it" sprawl shape — the original
        ``pdf`` use case from observation 01.
        """
        out: dict[str, set[Path]] = {}
        for parse in self._parses:
            content = parse.content
            for c in parse.callables:
                if not all(f(c) for f in self._filters):
                    continue
                node = parse.callable_nodes.get(c.qualname)
                if node is None:
                    continue
                body = node.child_by_field_name("body") or node
                for ident in _walk_identifier_nodes(body):
                    name = content[ident.start_byte:ident.end_byte].decode(
                        "utf-8", errors="replace",
                    )
                    if name.startswith("_") and not name.startswith("__"):
                        continue
                    for t in Lexicon.split_tokens(name):
                        tl = t.lower()
                        if tl in exclude:
                            continue
                        out.setdefault(tl, set()).add(c.path)
        return out

    # ---- three planes of evaluation (instrumentation-only; do not collapse) -
    #
    # Per docs/research/observations/07-* (forthcoming), three orthogonal
    # axes are exposed independently so observations can tabulate their
    # overlap matrix empirically rather than presupposing which combinations
    # are load-bearing:
    #
    #   - Plane A (association density) — ``packets``, already exists.
    #   - Plane B (distribution position) — ``frequency_head``.
    #   - Plane C (spread) — ``spread_dominant``.
    #
    # Each method has its OWN threshold parameter. None of them claim a
    # "hub" interpretation on their own — that's a downstream judgment
    # applied to the intersection of planes. ``hapax_ratio`` is the
    # complementary tail summary (the long-tail noise floor as a single
    # scalar).

    def hapax_ratio(
        self,
        *,
        exclude: frozenset[str] = frozenset(),
        include_parameters: bool = True,
    ) -> float:
        """Fraction of distinct tokens that appear exactly once.

        Single-scalar diagnostic of the long-tail noise floor (hapax
        legomena = "said once"). High values (≥ 0.5) indicate a corpus
        dominated by one-off identifiers — vocabulary-rich but possibly
        thinly-reused. Low values indicate a corpus where vocabulary is
        consistently reused. Returns ``0.0`` for empty input.

        Per ``docs/research/identifier-vocabulary.md`` (Zipf 1949
        section): the long tail is structurally expected; this scalar
        quantifies how much of the corpus lives in it.
        """
        freq = self.frequencies(
            exclude=exclude, include_parameters=include_parameters,
        )
        if not freq:
            return 0.0
        hapax = sum(1 for n in freq.values() if n == 1)
        return hapax / len(freq)

    def frequency_head(
        self,
        *,
        threshold: int | None = None,
        exclude: frozenset[str] = frozenset(),
        include_parameters: bool = True,
    ) -> list[tuple[str, int]]:
        """Tokens with occurrence count ≥ ``threshold``, descending by count.

        Plane B (distribution position) primitive. Returns the head
        cohort of the frequency distribution above a *data-derived*
        threshold (caller supplies the threshold value; for fully
        adaptive behaviour see future Zipf-elbow work).

        Distinct from ``modal_tokens(top=K)``, which returns a fixed
        caller top-K regardless of distribution shape. Use
        ``frequency_head`` when "everything above a frequency floor"
        matters; use ``modal_tokens`` when "the top N regardless of
        count" matters. No wrapper relationship — different contracts.

        ``threshold=None`` defaults to the 90th percentile of the
        frequency distribution, a reasonable head-cohort default for
        Zipf-shaped corpora.
        """
        freq = self.frequencies(
            exclude=exclude, include_parameters=include_parameters,
        )
        if not freq:
            return []
        if threshold is None:
            sorted_counts = sorted(freq.values())
            p90_idx = max(0, int(0.9 * (len(sorted_counts) - 1)))
            threshold = sorted_counts[p90_idx]
        head = [(t, n) for t, n in freq.items() if n >= threshold]
        head.sort(key=lambda kv: (-kv[1], kv[0]))
        return head

    def spread_dominant(
        self,
        *,
        min_spread: int,
        exclude: frozenset[str] = frozenset(),
        include_parameters: bool = True,
    ) -> list[tuple[str, int]]:
        """Tokens whose file-spread ≥ ``min_spread``, descending by spread.

        Plane C (spread) primitive. Token-spread is the number of
        distinct files the token appears in (via ``token_locations``).
        High spread implies the token crosses many module boundaries
        — either domain vocabulary recurring across structural units
        (potential refactor candidate) or infrastructure plumbing
        threaded everywhere (potential hub).

        The intersection of high spread + low packet-association is
        the empirical hub signature; the intersection of high spread +
        high packet-association is the refactor candidate. Neither
        interpretation is baked in here — that's obs 07's job.
        """
        locs = self.token_locations(
            exclude=exclude, include_parameters=include_parameters,
        )
        dominant = [(t, len(files)) for t, files in locs.items()
                    if len(files) >= min_spread]
        dominant.sort(key=lambda kv: (-kv[1], kv[0]))
        return dominant

    # ---- second-wave primitives (named intersections of the three planes) --
    #
    # ``middle_spread`` and ``packet_isolates`` name specific cells of the
    # 2×2×2 overlap matrix established in obs 07. They are not new
    # measurements — they are composed from the first-wave methods + packets()
    # — but the named cell is observably load-bearing enough to warrant a
    # direct surface. See docs/research/observations/07-* for the empirical
    # justification (cell occupancy on snapshot + dev).

    def middle_spread(
        self,
        *,
        min_spread: int,
        max_frequency: int | None = None,
        exclude: frozenset[str] = frozenset(),
        include_parameters: bool = True,
    ) -> list[tuple[str, int, int]]:
        """Tokens with file-spread ≥ ``min_spread`` AND frequency < ``max_frequency``.

        The ``(--C)`` cell of the obs-07 matrix: diffuse-domain
        vocabulary that crosses structural boundaries without
        cresting the frequency head. Often the most actionable
        refactor candidates — spread enough to matter but not so
        frequent they're plumbing.

        ``max_frequency=None`` defaults to the data-derived head
        threshold (90th percentile of the frequency distribution),
        matching ``frequency_head``'s default so the cell boundary
        is consistent.

        Returns ``(token, freq, spread)`` triples ordered by
        ``(-spread, -freq, token)``.
        """
        freq = self.frequencies(
            exclude=exclude, include_parameters=include_parameters,
        )
        if not freq:
            return []
        if max_frequency is None:
            sorted_counts = sorted(freq.values())
            p90_idx = max(0, int(0.9 * (len(sorted_counts) - 1)))
            max_frequency = sorted_counts[p90_idx]
        locs = self.token_locations(
            exclude=exclude, include_parameters=include_parameters,
        )
        out = [
            (t, freq[t], len(files))
            for t, files in locs.items()
            if len(files) >= min_spread and freq.get(t, 0) < max_frequency
        ]
        out.sort(key=lambda x: (-x[2], -x[1], x[0]))
        return out

    def packet_isolates(
        self,
        *,
        min_bags: int = 3,
        min_association: float = 0.7,
        min_frequency: int = 1,
        exclude: frozenset[str] = frozenset(),
        include_parameters: bool = True,
    ) -> list[tuple[str, int]]:
        """Tokens with frequency ≥ ``min_frequency`` that appear in zero
        packets at the given ``(min_bags, min_association)``.

        The empirical hub diagnostic per obs 07: the ``(-B-)`` and
        ``(-BC)`` cells of the matrix are dominated by these tokens —
        frequent and often spread, but fail to bond with any specific
        partner. Infrastructure plumbing (``root``, ``node``,
        ``content``, ``config``) lands here.

        Takes the same ``(min_bags, min_association)`` parameters as
        ``packets()`` so "isolate" semantics match the packet
        primitive's definition. Returns ``(token, freq)`` ordered by
        ``(-freq, token)``.
        """
        freq = self.frequencies(
            exclude=exclude, include_parameters=include_parameters,
        )
        if not freq:
            return []
        packets = self.packets(
            min_bags=min_bags, min_association=min_association,
            exclude=exclude, include_parameters=include_parameters,
        )
        packet_members: set[str] = set()
        for p in packets:
            packet_members |= p
        isolates = [
            (t, n) for t, n in freq.items()
            if n >= min_frequency and t not in packet_members
        ]
        isolates.sort(key=lambda kv: (-kv[1], kv[0]))
        return isolates

    # ---- co-occurrence: which tokens travel together ----------------------
    #
    # The per-callable token bag is the unit of co-occurrence. Two tokens
    # co-occur once for every callable in which they both appear. Pair counts
    # are canonical-form keyed: ``(a, b)`` where ``a < b``. The ``packets``
    # method composes co-occurrence with per-callable frequencies to surface
    # token clusters that travel together strongly — undeclared dataclasses
    # and parameter packets the codebase has not extracted.

    def callable_token_bags(
        self,
        *,
        exclude: frozenset[str] = frozenset(),
        include_parameters: bool = True,
    ) -> Iterator[set[str]]:
        """Yield one token-set per emittable callable in this view.

        Tokens come from the callable's simple name + parameter names
        (snake/Camel-split, lowercased, ``self``/``cls`` dropped). Each
        bag is the unit a single function contributes to the co-occurrence
        index when ``scope='callable'`` (the default). Co-occurrence at
        this scope surfaces *parameter packets* and dataclass candidates.
        """
        for c in self.callables():
            bag: set[str] = set()
            name = c.qualname.rsplit(".", 1)[-1]
            if name and not name.startswith("<"):
                for t in Lexicon.split_tokens(name):
                    tl = t.lower()
                    if tl not in exclude:
                        bag.add(tl)
            if include_parameters:
                for p in c.parameters:
                    if p.name in ("self", "cls"):
                        continue
                    for t in Lexicon.split_tokens(p.name):
                        tl = t.lower()
                        if tl not in exclude:
                            bag.add(tl)
            if bag:
                yield bag

    def file_token_bags(
        self,
        *,
        exclude: frozenset[str] = frozenset(),
        include_parameters: bool = True,
    ) -> Iterator[set[str]]:
        """Yield one token-set per parsed file in this view.

        Each bag is the union of vocabulary used in that file: all
        callable names + class-like scope names + (optionally) parameter
        names, snake/Camel-split and lowercased. Co-occurrence at this
        scope surfaces *module-extraction* candidates — tokens that
        recur across files together implicate a missing module by their
        shared concept.
        """
        by_file: dict[Path, set[str]] = {}
        for entity in self.named_entities():
            path = Path(entity.file)
            bag = by_file.setdefault(path, set())
            for t in entity.tokens:
                tl = t.lower()
                if tl not in exclude:
                    bag.add(tl)
        if include_parameters:
            for c in self.callables():
                bag = by_file.setdefault(c.path, set())
                for p in c.parameters:
                    if p.name in ("self", "cls"):
                        continue
                    for t in Lexicon.split_tokens(p.name):
                        tl = t.lower()
                        if tl not in exclude:
                            bag.add(tl)
        for bag in by_file.values():
            if bag:
                yield bag

    def _bags_for_scope(
        self,
        scope: str,
        *,
        exclude: frozenset[str] = frozenset(),
        include_parameters: bool = True,
    ) -> Iterator[set[str]]:
        """Dispatch ``scope='callable'|'file'`` to the right bag source."""
        if scope == "callable":
            return self.callable_token_bags(
                exclude=exclude, include_parameters=include_parameters,
            )
        if scope == "file":
            return self.file_token_bags(
                exclude=exclude, include_parameters=include_parameters,
            )
        raise ValueError(f"unknown scope {scope!r}; expected 'callable' or 'file'")

    def cooccurrences(
        self,
        *,
        scope: str = "callable",
        exclude: frozenset[str] = frozenset(),
        include_parameters: bool = True,
    ) -> Counter[tuple[str, str]]:
        """``(token_a, token_b) → count`` over the chosen scope's token bags.

        Pairs are canonical (``a < b``); each bag contributes one count
        per distinct pair in it. A bag ``{x, y, z}`` contributes
        ``(x,y), (x,z), (y,z)`` once each.

        ``scope='callable'`` (default) counts pairs per function — surfaces
        parameter packets. ``scope='file'`` counts pairs per file —
        surfaces module-extraction packets.
        """
        out: Counter[tuple[str, str]] = Counter()
        for bag in self._bags_for_scope(
            scope, exclude=exclude, include_parameters=include_parameters,
        ):
            toks = sorted(bag)
            for i, a in enumerate(toks):
                for b in toks[i + 1:]:
                    out[(a, b)] += 1
        return out

    def packets(
        self,
        *,
        scope: str = "callable",
        min_bags: int = 3,
        min_association: float = 0.7,
        exclude: frozenset[str] = frozenset(),
        include_parameters: bool = True,
    ) -> list[set[str]]:
        """Token sets that travel together across the chosen scope's bags.

        A packet is a set of tokens where every pair has association
        ``cooc(a,b) / max(freq(a), freq(b)) >= min_association`` and
        each token appears in ``>= min_bags`` bags (callables or files).

        Max-normalised association distinguishes mutual packets (the
        ``FindOptions`` cluster: excludes/hidden/ignore/globs/languages
        each appear ~once together for every time any of them appears)
        from hubs (``root`` co-occurs with everything but at low ratio
        relative to its own frequency).

        Returned packets are deduplicated by membership but may overlap.
        Each token's neighborhood is emitted once as a packet — research
        wants to see all the candidate clusters, not just maximal cliques.
        """
        bags = list(self._bags_for_scope(
            scope, exclude=exclude, include_parameters=include_parameters,
        ))

        token_freq: Counter[str] = Counter()
        for bag in bags:
            token_freq.update(bag)  # each token counted once per bag

        cooc: Counter[tuple[str, str]] = Counter()
        for bag in bags:
            toks = sorted(bag)
            for i, a in enumerate(toks):
                for b in toks[i + 1:]:
                    cooc[(a, b)] += 1

        neighbours: dict[str, set[str]] = {}
        for (a, b), n in cooc.items():
            if token_freq[a] < min_bags or token_freq[b] < min_bags:
                continue
            assoc = n / max(token_freq[a], token_freq[b])
            if assoc >= min_association:
                neighbours.setdefault(a, set()).add(b)
                neighbours.setdefault(b, set()).add(a)

        seen: set[frozenset[str]] = set()
        out: list[set[str]] = []
        for tok in sorted(neighbours):
            candidate = frozenset(neighbours[tok] | {tok})
            if candidate in seen or len(candidate) < 2:
                continue
            seen.add(candidate)
            out.append(set(candidate))
        return sorted(out, key=lambda s: (-len(s), sorted(s)))

    # ---- scope enumeration -------------------------------------------------

    def by_file(self) -> Iterator[tuple[Path, Lexicon]]:
        """Yield ``(path, Lexicon-restricted-to-that-file)`` per parsed file.

        Cheapest scope axis. The emitted Lexicon shares parse data with
        this one; only a filter is added. Distribution methods on the
        sub-Lexicon return per-file numbers.
        """
        seen: set[str] = set()
        for parse in self._parses:
            key = str(parse.path)
            if key in seen:
                continue
            seen.add(key)
            yield parse.path, self._restricted(
                lambda rec, k=key: str(rec.path) == k,
            )

    def by_package(
        self,
        *,
        recursive: bool = False,
    ) -> Iterator[tuple[Path, Lexicon]]:
        """Yield ``(directory, Lexicon)`` per directory containing parsed files.

        With ``recursive=False`` (default), each emitted Lexicon contains
        only the files directly in that directory. With ``recursive=True``,
        files in subdirectories are included too — the package-as-tree
        view, matching how sprawl / imposters do hierarchical claiming.

        "Package" here is the parent directory, not a language-specific
        package marker (no ``__init__.py`` check). For Python-style
        package detection use ``Language.resolve_packages``.
        """
        seen: set[Path] = set()
        for parse in self._parses:
            pkg = parse.path.parent
            if pkg in seen:
                continue
            seen.add(pkg)
            if recursive:
                prefix = str(pkg) + "/"
                pred = lambda rec, pr=prefix: str(rec.path).startswith(pr)
            else:
                pkg_str = str(pkg)
                pred = lambda rec, pk=pkg_str: str(rec.path.parent) == pk
            yield pkg, self._restricted(pred)

    def _restricted(self, predicate: TypingCallable[[Any], bool]) -> Lexicon:
        """Return a new Lexicon with ``predicate`` appended to the filter
        chain. Internal helper for ``by_file`` / ``by_package``."""
        return Lexicon(self._parses, filters=tuple(self._filters) + (predicate,))

    # ---- identifier-level compute methods ----------------------------------

    @staticmethod
    def split_tokens(name: str) -> tuple[str, ...]:
        """Split an identifier into word tokens (snake_case + CamelCase aware).

        ``my_func`` → ``("my", "func")``; ``processData`` → ``("process", "Data")``;
        ``HTTPClient`` → ``("HTTP", "Client")``; ``__init__`` → ``("init",)``.

        Static — operates on the name string alone. Exposed on Lexicon
        so rules don't need to reach into ``slop.lexicon.affix``.
        """
        import re
        cleaned = name.strip("_")
        cleaned = _CAMEL_LOWER_UPPER.sub(r"\1_\2", cleaned)
        cleaned = _CAMEL_UPPER_TITLE.sub(r"\1_\2", cleaned)
        return tuple(p for p in re.split(r"[_\d]+", cleaned) if p)

    def files(self) -> Iterable[Any]:
        """Yield each unique parsed file's path (as ``pathlib.Path``).

        Used by rules that operate at the file/module level (hammers'
        module-name check, future per-file lexical signals).
        """
        for p in self._parses:
            yield p.path

    def callables(self) -> Iterable[Callable]:
        """Yield every callable record in this view (filtered if sliced).

        Used by rules that need parameter / annotation access — the
        Lexicon's view of callables, with the same where/under filters
        applied that ``walk``/``named_entities`` honour.
        """
        for c in self._callable_by_key.values():
            if all(f(c) for f in self._filters):
                yield c

    def named_entities(self):
        """Iterate token-split named entities (callables + class-like scopes).

        Yields one ``NamedEntity`` per emitted callable (excluding
        anonymous lambdas) and per class-like scope (``CLASS``,
        ``INTERFACE``, ``STRUCT``, ``TRAIT``). The ``kind`` field is
        ``"function"`` for callables, ``"class"`` for scopes.

        Consumed by entity-name rules (verbosity, stutter, cowards,
        hammers, tautology). Filters declared via ``where`` /
        ``under`` apply.
        """
        from slop.lexicon.records import NamedEntity
        from slop.tree.records import CallableKind, ScopeKind

        for p in self._parses:
            content = p.content
            for c in p.callables:
                if not all(f(c) for f in self._filters):
                    continue
                if c.kind == CallableKind.LAMBDA:
                    continue
                name = c.qualname.rsplit(".", 1)[-1]
                if name.startswith("<"):
                    continue
                tokens = Lexicon.split_tokens(name)
                if not tokens:
                    continue
                yield NamedEntity(
                    name=name,
                    kind="function",
                    file=str(c.path),
                    line=c.line,
                    language=p.language,
                    tokens=tokens,
                )
            for s in p.scopes:
                if not all(f(s) for f in self._filters):
                    continue
                if s.kind not in _CLASS_LIKE_SCOPE_KINDS:
                    continue
                name = s.qualname.rsplit(".", 1)[-1]
                if not name or name.startswith("<"):
                    continue
                tokens = Lexicon.split_tokens(name)
                if not tokens:
                    continue
                yield NamedEntity(
                    name=name,
                    kind="class",
                    file=str(s.path),
                    line=s.line,
                    language=p.language,
                    tokens=tokens,
                )

    # ---- per-callable compute methods --------------------------------------

    def first_param_clusters(
        self,
        *,
        min_cluster: int = 3,
        exempt_names: frozenset[str] = frozenset({"self", "cls"}),
        root: Any = None,
    ) -> list[Any]:
        """Group callables by their first parameter; emit clusters at
        the narrowest scope where they cohere.

        Returns ``FirstParameterCluster`` instances (imported from the
        legacy kernel during the migration window — the dataclass is
        pure-data and is renamed in the deletion sweep). Hierarchical
        traversal: a callable appears in at most one cluster, claimed
        at the deepest scope where the cluster reaches ``min_cluster``.

        ``root`` is the codebase root used to derive relative paths for
        the path-parts decomposition that drives scope claiming. If
        None, falls back to the longest common prefix across observed
        callable paths.
        """
        from slop.lexicon._profile import classify_cluster, profile_cluster
        from slop.lexicon.records import FirstParameterCluster

        # Build _FuncEntry-equivalent records for the clustering walk.
        # We use lightweight tuples instead of dedicated record types.
        from pathlib import Path

        if root is None:
            # Best-effort: derive from common prefix.
            paths = [c.path for c in self._callable_by_key.values()]
            if paths:
                try:
                    root = Path(_common_prefix(paths))
                except Exception:
                    root = paths[0].parent
            else:
                return []
        root_path = Path(root)

        # entries: list of (name, file_rel, line, parts, param_name, param_type)
        from slop.tree.records import CallableKind  # local import to avoid cycle
        entries: list[tuple[str, str, int, tuple[str, ...], str | None, str | None]] = []
        for c in self._callable_by_key.values():
            if not all(f(c) for f in self._filters):
                continue
            # Lambdas are excluded from first-parameter clustering. Their
            # first parameter is typically a closure variable, not a
            # receiver candidate; the legacy ``enumerate_functions``
            # walker excluded lambdas for the same reason.
            if c.kind == CallableKind.LAMBDA:
                continue
            # Skip "self"/"cls" first parameters for methods
            first_param = None
            first_type: str | None = None
            for p in c.parameters:
                if p.name in exempt_names:
                    continue
                first_param = p.name
                first_type = p.annotation
                break
            try:
                rel = c.path.relative_to(root_path)
                parts = rel.parts
                file_rel = str(rel)
            except ValueError:
                parts = c.path.parts
                file_rel = str(c.path)
            # Use simple base-name (without qualname prefix) for member naming —
            # matches the legacy ``ctx.name`` convention.
            simple_name = c.qualname.split(".")[-1]
            entries.append((simple_name, file_rel, c.line, parts, first_param, first_type))

        # Hierarchical clustering: mirror the legacy
        # ``_recursive_first_param_findings`` algorithm.
        by_prefix: dict[tuple[str, ...], list[tuple]] = {(): list(entries)}
        for e in entries:
            parts = e[3]
            for depth in range(1, len(parts) + 1):
                by_prefix.setdefault(parts[:depth], []).append(e)

        prefixes = sorted(by_prefix.keys(), key=lambda p: -len(p))
        findings: list[Any] = []
        claimed: set[tuple[str, str]] = set()

        for prefix in prefixes:
            scope_funcs = [
                e for e in by_prefix[prefix] if (e[1], e[0]) not in claimed
            ]
            if len(scope_funcs) < min_cluster:
                continue

            is_root = not prefix
            is_file = bool(prefix) and "." in prefix[-1]

            by_param: dict[str, list[tuple]] = {}
            for e in scope_funcs:
                pname = e[4]
                if pname is None or len(pname) < 2:
                    continue
                by_param.setdefault(pname, []).append(e)

            for pname, members in by_param.items():
                if len(members) < min_cluster:
                    continue

                if not is_file:
                    child_keys = {
                        m[3][len(prefix)] for m in members if len(m[3]) > len(prefix)
                    }
                    if len(child_keys) < 2:
                        continue
                    if is_root and len(child_keys) >= 4:
                        continue

                types = {m[5] for m in members if m[5]}
                verdict, advisory = classify_cluster(pname, types, exempt_names)
                scope_str, scope_kind = scope_label(prefix)
                findings.append(
                    FirstParameterCluster(
                        parameter_name=pname,
                        parameter_types=types,
                        members=[(m[0], m[1], m[2]) for m in members],
                        verdict=verdict,
                        advisory=advisory,
                        scope=scope_str,
                        scope_kind=scope_kind,
                    )
                )
                for m in members:
                    claimed.add((m[1], m[0]))

        findings.sort(key=lambda c: (-c.scope.count("/"), -len(c.members)))

        # Enrich each cluster with multi-signal profile (body Jaccard,
        # receiver-call density, modal-token overlap). The signals
        # power the rule's profile_label-aware advisories.
        for cluster in findings:
            bodies = self.bodies_for_cluster(cluster)
            profile_cluster(cluster, bodies)

        return findings

    def bodies_for_cluster(self, cluster: Any) -> dict[tuple[str, str], tuple[Any, bytes]]:
        """Return the (file, name) -> (body_node, content) map needed by
        the legacy ``_profile_cluster`` helper.

        During the migration window the rule wrapper passes this map
        back into the legacy signal computer; once the body-Jaccard /
        receiver-call density compute methods land here directly
        (follow-up intent), this helper retires.
        """
        out: dict[tuple[str, str], tuple[Any, bytes]] = {}
        for name, file, _line in cluster.members:
            # Find the callable matching (file, simple_name). The qualname
            # ends with simple_name; multiple callables may share the
            # simple name across files — disambiguate by file match.
            for k, c in self._callable_by_key.items():
                if k[1].split(".")[-1] != name:
                    continue
                # Match by relative-file suffix (members carry the relative
                # path from the codebase root; callable.path is absolute).
                if not str(c.path).endswith(file):
                    continue
                node = self._node_by_key.get(k)
                if node is None:
                    continue
                body = node.child_by_field_name("body")
                if body is None:
                    continue
                content = self._content_by_path.get(str(c.path), b"")
                out[(file, name)] = (body, content)
                break
        return out

    # ---- slicing -----------------------------------------------------

    def under(
        self,
        *,
        path: str | None = None,
        qualname: str | None = None,
    ) -> Lexicon:
        """Return a new Lexicon restricted to occurrences under ``path``
        and/or under the qualname-rooted scope ``qualname``."""
        new_filters = list(self._filters)
        if path is not None:
            path_prefix = path
            new_filters.append(lambda rec: str(rec.path).startswith(path_prefix))
        if qualname is not None:
            qn = qualname
            new_filters.append(
                lambda rec: getattr(rec, "qualname", "").startswith(qn)
            )
        return Lexicon(self._parses, filters=tuple(new_filters))

    def where(
        self,
        *,
        language: str | None = None,
        kind: str | None = None,
    ) -> Lexicon:
        """Return a new Lexicon restricted by language and/or occurrence kind.

        Language filter uses the view's internal ``path → language`` map
        since records dropped the denormalised ``language`` field.
        """
        new_filters = list(self._filters)
        if language is not None:
            lang = language
            lang_map = self._language_by_path
            new_filters.append(lambda rec: lang_map.get(str(rec.path)) == lang)
        if kind is not None:
            k = kind
            new_filters.append(lambda rec: getattr(rec, "kind", None) == k)
        return Lexicon(self._parses, filters=tuple(new_filters))

    def walk(self) -> Iterable[Occurrence]:
        """Yield every Occurrence in this view (filtered if sliced)."""
        for p in self._parses:
            for o in p.occurrences:
                if all(f(o) for f in self._filters):
                    yield o


def _common_prefix(paths: list) -> str:
    """Return the longest common directory prefix across paths."""
    import os
    return os.path.commonpath([str(p) for p in paths])


def _walk_identifier_nodes(node) -> Iterator[Any]:
    """Yield every leaf ``identifier`` node in the subtree rooted at ``node``."""
    stack = [node]
    while stack:
        n = stack.pop()
        if n.type == "identifier" and n.child_count == 0:
            yield n
        else:
            for child in n.children:
                stack.append(child)
