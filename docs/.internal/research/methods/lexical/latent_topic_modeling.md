# Latent topic modeling (LDA / RTM)

**Status:** Active in v2 PoC battery; **not** recommended for kernel
promotion (see Modifications). Retained for orientation research.
**PoC:** [`scripts/research/composition_poc_v2/poc5_rtm_topics.py`](../../../scripts/research/composition_poc_v2/poc5_rtm_topics.py)

## Problem

First-parameter clustering and affix detection both group functions
by *surface* signal (one token, one parameter). Cross-cutting
concepts are invisible to those probes — a "discover files via fd"
concern that touches twenty functions across `_fs/`, `_compose/`,
and `_lexical/` will never appear as a single cluster, because
those functions don't share a parameter or a name pattern.

Latent topic modeling treats each function as a *document* and
asks: what concepts cohabit across the codebase, irrespective of
where the surface markers cluster? It surfaces semantic groupings
that none of the other probes can.

## Signal purpose

LDA produces:

- **K topics** (configurable; default 10), each defined by its top
  weighted vocabulary words.
- **Per-function topic distribution** — every function has a
  weight on every topic, summing to 1.
- **Topic-dominant functions** — functions where one topic
  accounts for >50% of the distribution.

Reading the output:

| Pattern | Reading |
|---|---|
| One topic dominates many functions across many files | A latent codebase concern that's spread across files; rarely a refactor target on its own, but corroborates other probes (e.g. v2.3's language-alphabet finding overlaps with LDA's "language/parser/tree" topic) |
| Topics partition cleanly into the existing module structure | Modules are coherent; LDA found what the developer already factored. No action. |
| One topic dominates *one* file | That file is on a single concern; healthy module. |
| One topic dominates *several files in the same package* | The package is doing one thing; healthy package boundary. |

LDA is best read as **orientation** — it doesn't propose actions,
it reveals concept distribution. It's most useful as a sanity check
on findings from sharper probes: if v2.3 says "language is a
missing type" and LDA's Topic 1 is also `lang, tree, file, errors,
root, language, globs, parser`, the two probes corroborate. If
they disagree, one of them is finding noise.

## Algorithm

```
for each function in corpus:
    tokens = []
    tokens += split_identifier(function.name)
    DFS(function.body):
        if node is identifier:
            tokens += split_identifier(text(node))
    tokens = lowercase, length≥3, not in STOPWORDS
    documents.append(" ".join(tokens))

vectorizer = CountVectorizer(min_df=2, max_df=0.5)
X = vectorizer.fit_transform(documents)

lda = LatentDirichletAllocation(n_components=K, max_iter=50)
doc_topic = lda.fit_transform(X)

for each topic in lda.components_:
    top_words = top 8 vocabulary entries by weight
for each function:
    dominant_topic = argmax(doc_topic[function])
```

The CountVectorizer settings (`min_df=2`, `max_df=0.5`) discard
both rare tokens (typo-resistant) and overly common tokens
(scaffolding-resistant — words appearing in >50% of functions are
mostly noise like "self," "return"). The stopword list is small and
hand-curated: scaffolding tokens that don't carry concept signal
(`self, cls, args, kwargs, name, value, data`).

`scikit-learn` is required at runtime for this method (its
`LatentDirichletAllocation` is the implementation). Other methods
in the battery use no external dependencies.

## Citations

- **Bavota, G., Oliveto, R., De Lucia, A., Antoniol, G. &
  Guéhéneuc, Y-G. (2014).** "Methodbook: Recommending Move Method
  Refactorings via Relational Topic Models." *IEEE Transactions on
  Software Engineering* 40(7), 671-694.
  The canonical paper for using topic modeling for Extract Class /
  Move Method detection. Methodbook uses *Relational* Topic Models,
  which model the function-call graph as document-document links.
  Our PoC uses plain LDA without the relational signal — a
  simplification with explicit cost (see Modifications).

- **Blei, D., Ng, A. & Jordan, M. (2003).** "Latent Dirichlet
  Allocation." *Journal of Machine Learning Research* 3, 993-1022.
  Foundational LDA paper. Our PoC uses sklearn's standard LDA
  implementation.

- **Chang, J. & Blei, D. (2010).** "Hierarchical Relational Models
  for Document Networks." *Annals of Applied Statistics* 4(1),
  124-150.
  RTM original. Mentioned for the Methodbook lineage; we don't
  implement RTM in the PoC.

## Modifications

This method is the **most heavily simplified** from its published
form, and we flag that as the reason it's not recommended for
kernel promotion.

- **LDA, not RTM.** Bavota et al.'s Methodbook uses Relational
  Topic Models, which incorporate the function-call graph as
  edges between documents. Topics that span called/calling
  functions get reinforced. We use plain LDA (semantic only),
  which captures the topic structure but loses the relational
  reinforcement. This is the *primary* reason our LDA topics are
  coarse — without the call-graph edges, the topic model has no
  way to distinguish "these functions form a sub-system" from
  "these functions happen to use similar vocabulary."
- **No coherence-score thresholds.** Production topic models tune
  K (number of topics) by coherence-score sweeps. We use K=10 as
  a fixed default; a real evaluation would search K systematically.
- **External dependency.** sklearn is not currently a slop
  dependency. Promoting this method would require either pinning
  sklearn or implementing LDA from scratch (~200 LOC of variational
  inference; non-trivial).
- **Output is descriptive, not prescriptive.** Bavota's full
  pipeline produces ranked Move Method recommendations; we only
  expose the topics and topic-dominant functions, not refactoring
  candidates.

## Why we don't promote this to the kernel

Three reasons, in priority order:

1. **Topics are coarse.** On slop's 447-document corpus, the most
   populous topic captured 79 functions — about 17% of the corpus.
   That's not a useful unit of action.
2. **Without RTM's relational signal, the topics drift.** Several
   slop topics overlap or contradict each other (`node, child,
   type` vs `node, config, body, child` — both are AST-walker
   topics, separated by a vocabulary detail).
3. **The other probes already cover the actionable cases.** v2.3
   alphabet-entity recognition finds the language case more
   precisely. v2.7 Lanza/Marinescu finds Extract Class candidates
   more directly.

LDA's value is **orientation** — at a glance, what concept
distribution exists across the codebase? — not detection. We keep
the PoC for that orientation use, document it here, and decline to
build a rule on top of it for now.

## ELI5

Pretend each function is a tiny document. Its words are the
identifiers in its name and body, lowercased and split.

```
def split_identifier(name):
    name = name.strip("_")
    return [t for t in re.split(r"[_]+", name) if t]

# Words: split, identifier, name, name, name, strip, return, split, name
```

Run topic modeling — a statistical method that assumes documents
are mixtures of latent topics, each topic being a probability
distribution over words. The algorithm finds the topics that best
explain how words co-occur across documents.

What you get out is something like:

- **Topic 5:** node, child, type, byte, content, declarator, start, inner

That's the "I'm walking an AST" topic. Functions where this topic
dominates are the codebase's AST-walking functions. They didn't
declare themselves as a family; the topic model inferred it from
their vocabulary.

The catch: topic modeling, especially without modeling the
function-call graph (which is what the published Methodbook
algorithm does), produces topics that are coarse. You get the
*flavor* of what concepts are in the codebase, but you don't get a
list of "here are the concrete refactoring candidates."

So this method is useful as a sanity check — if the AST-walking
topic exists and several other probes also flag AST-walking
functions, that's two independent signals agreeing. But you don't
build a rule on it directly; the actionable resolution comes from
the sharper probes.
