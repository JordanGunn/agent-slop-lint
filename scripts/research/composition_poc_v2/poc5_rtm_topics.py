"""PoC v2.5 — Latent topic modeling (Bavota et al. Methodbook style).

Treat each function as a "document" — its bag-of-tokens drawn from
identifier names (function name + body identifiers, snake/Camel
split + lowercase + stop-word filter). Run Latent Dirichlet
Allocation to discover topics. Functions sharing dominant topics
are candidate Extract Class members.

This is a simplification of the full Methodbook algorithm, which
uses Relational Topic Models (RTM) — explicitly modeling the
function-call graph as document-document links. Plain LDA captures
the latent-semantic part without the relational signal.

Dependencies
------------
- ``scikit-learn`` (CountVectorizer, LatentDirichletAllocation).
  Install via: ``uv pip install scikit-learn``.

Theoretical grounding
---------------------
- Bavota, Oliveto, De Lucia, Antoniol, Guéhéneuc (2014)
  "Methodbook: Recommending Move Method Refactorings via
  Relational Topic Models." IEEE TSE 40(7).
- Chang & Blei (2010) "Hierarchical Relational Models for
  Document Networks" — RTM original.
- Blei, Ng & Jordan (2003) "Latent Dirichlet Allocation."

Usage
-----
    cd src
    uv pip install scikit-learn
    uv run python ../scripts/research/composition_poc_v2/poc5_rtm_topics.py cli/slop
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from slop._lexical._naming import enumerate_functions
from slop._lexical.identifier_tokens import split_identifier


_STOPWORDS = frozenset({
    "self", "cls", "args", "kwargs", "name", "value", "data",
    "true", "false", "none", "return", "if", "else", "for", "while",
    "in", "is", "not", "and", "or", "the", "a", "an",
})


def _function_tokens(ctx) -> list[str]:
    """Bag-of-tokens for one function: name + body identifiers."""
    tokens: list[str] = []
    # Name tokens
    for t in split_identifier(ctx.name):
        tl = t.lower()
        if len(tl) >= 3 and tl not in _STOPWORDS:
            tokens.append(tl)
    # Body identifiers
    if ctx.body_node is not None:
        def walk(node):
            if node.type == "identifier" and node.child_count == 0:
                text = ctx.content[node.start_byte:node.end_byte].decode(
                    "utf-8", errors="replace",
                )
                for t in split_identifier(text):
                    tl = t.lower()
                    if len(tl) >= 3 and tl not in _STOPWORDS:
                        tokens.append(tl)
            for child in node.children:
                walk(child)
        walk(ctx.body_node)
    return tokens


def main(root: str, n_topics: int = 10) -> None:
    try:
        from sklearn.decomposition import LatentDirichletAllocation
        from sklearn.feature_extraction.text import CountVectorizer
    except ImportError:
        print("ERROR: sklearn required. Install with: uv pip install scikit-learn",
              file=sys.stderr)
        sys.exit(2)

    print("# PoC v2.5 — Latent topic modeling (RTM-style via LDA)")
    print()
    rp = Path(root)
    docs: list[str] = []
    labels: list[tuple[str, str]] = []  # (name, file)
    for ctx in enumerate_functions(rp, languages=["python"]):
        if ctx.name.startswith("<") or ctx.body_node is None:
            continue
        tokens = _function_tokens(ctx)
        if len(tokens) < 5:
            continue
        docs.append(" ".join(tokens))
        labels.append((ctx.name, ctx.file))

    print(f"Root: `{root}`  |  Documents (functions): {len(docs)}  |  Topics: {n_topics}")
    print()

    # Vectorize
    vectorizer = CountVectorizer(min_df=2, max_df=0.5)
    X = vectorizer.fit_transform(docs)
    vocab = vectorizer.get_feature_names_out()

    # Fit LDA
    lda = LatentDirichletAllocation(
        n_components=n_topics, max_iter=50, learning_method="batch",
        random_state=42,
    )
    doc_topic = lda.fit_transform(X)

    print(f"Vocabulary size: {len(vocab)}")
    print()
    print("## Discovered topics")
    print()
    for topic_idx, topic_dist in enumerate(lda.components_):
        top_words_idx = topic_dist.argsort()[-8:][::-1]
        top_words = [vocab[i] for i in top_words_idx]
        print(f"- **Topic {topic_idx}**: {', '.join(top_words)}")
    print()

    # Top docs per topic
    print("## Functions assigned to each topic")
    print()
    for topic_idx in range(n_topics):
        # Functions where this topic is dominant
        members = [
            (labels[i], doc_topic[i][topic_idx])
            for i in range(len(labels))
            if doc_topic[i].argmax() == topic_idx
        ]
        members.sort(key=lambda x: -x[1])
        if not members:
            continue
        print(f"### Topic {topic_idx} ({len(members)} functions)")
        # Top-N functions
        for (name, file), weight in members[:8]:
            print(f"- `{name}` ({file})  —  weight {weight:.2f}")
        if len(members) > 8:
            print(f"- _...and {len(members) - 8} more_")
        # File concentration
        file_counts = Counter(file for (_, file), _ in members)
        if len(file_counts) <= 3:
            print(f"- File concentration: {dict(file_counts)}")
        print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    n_topics = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    main(sys.argv[1], n_topics)
