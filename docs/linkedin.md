# LinkedIn post plan

## What the research says (April 2026)

Synthesized from Sprout Social, Postiv, Gromming, and LinkedIn Pulse
analyses current as of April 2026:

- **Saves are roughly 5x more valuable than likes** as an engagement
  signal. Content that feels reference-worthy (save-and-return) beats
  content that feels consumable-once.
- **Hook is the first 140-210 characters** before "see more" truncation.
  Specific numbers and bold claims outperform questions and vague
  openings. Avoid "Comment YES if you agree" style bait, which LinkedIn
  now detects and penalises.
- **Text post sweet spot is 1,300-1,600 characters** for full-engagement
  long-form. Shorter (300-500 chars) also performs, but loses depth.
- **External links in post body trigger a 25-40% reach reduction**.
  Workaround: put the link in the first comment (approx. -5 to -10%
  penalty). LinkedIn Articles and native document posts get zero link
  penalty.
- **Document posts (PDF carousels) hit ~6.6% engagement**, the highest of
  any format. Worth considering as a follow-up once the text post lands.
- **First 60 minutes decide reach**. Early interactions gate the
  initial distribution window. Pick a time when the intended audience is
  online (Tuesday-Thursday mornings in the author's main timezone is the
  common sweet spot).

## Strategy for this piece

Technical content with code snippets and a delta table. Three reasonable
formats, in ascending cost:

1. **Feed post + first-comment link** (~1,300 chars). Cheap, easy, reuses
   the existing before.md and after.md as the linked artifact.
2. **LinkedIn Article** native long-form. Can include code, tables,
   primary-source citations inline. No link penalty. Archive that a feed
   post could link back to later.
3. **PDF carousel**. Highest engagement ceiling. Needs design work to
   turn the delta table and code diffs into slides. Not a first move.

Recommendation: ship (1) first. Monitor for 48 hours. If it lands well,
repurpose into (3). Treat (2) as optional, only if people ask for a
longer form or want a canonical URL on LinkedIn itself rather than
GitHub.

## Primary draft: feed post

```
"Something feels wrong, but you can't say what." Every developer has had this moment. Tests pass, the PR reads fine, something is still off. Articulating it used to take a decade of developing a nose.

A body of research from 1976 to 2002 had already reduced most of "feels wrong" to arithmetic. McCabe gave us cyclomatic complexity in 1976. Halstead followed with operator/operand density in 1977. Nejmeh added NPath in 1988. Martin applied the same approach to package architecture in 1994. Most of us memorized a few for an exam and promptly forgot them, because intuition was cheaper to apply than the math.

Then agents started writing the code. Agents have no intuition. "This feels off" does not land with a model that only hears words. The fix is to replace the feeling with a number. "NPath 1024 because this is a 10-branch dispatch pretending to be procedural code" is something a human and an agent can both act on. Shared vocabulary, not shared taste.

I ran a metric suite against its own source last week. Ten violations, exit code 1. Three metrics converged on the same function. The CLI entry point had NPath 1024 (ten sequential if-blocks, 2^10). Refactored to a dict lookup. NPath dropped to 8. None of the fixes were clever. The code had been written and reviewed by agents, and nobody human had read it closely.

A reviewer on their fourth PR of the afternoon is more likely to wave through incoherent code, not less. Without shared vocabulary, the slop compounds commit by commit.

The metrics are forty years old, precise, computable, and largely unread. That is fixable. The linter is called slop (on PyPI as agent-slop-lint). Walkthrough in the first comment.
```

Character count: ~1,575. Upper edge of the full-engagement band.

The shape is idea-first, not incident-first. The thesis (shared vocabulary
from forgotten textbook metrics) leads. The slop before/after sits in the
middle as the concrete case that proves it. The stake (compounding slop
under overloaded reviewers) closes. The tool name appears in the final
sentence, preserving war-story framing.

## First comment (link placement)

Post as the first comment within 1-2 minutes of the main post, so it
shows up at the top for early readers.

```
Full walkthrough with before/after code diffs and the delta table:
https://github.com/JordanGunn/agent-slop-lint/blob/main/docs/after.md

Original incident report (the raw terminal output and which functions got flagged):
https://github.com/JordanGunn/agent-slop-lint/blob/main/docs/before.md

Primary sources (McCabe 1976, Halstead 1977, Nejmeh 1988, Campbell 2018, Martin 1994, Lakos 1996, Martin 2002, Tornhill 2015):
https://github.com/JordanGunn/agent-slop-lint/blob/main/docs/philosophy/references.md
```

## Notes on the hook

First 210 characters (what appears before "see more"):

> Ran a code-quality linter against its own source last week. Ten violations, one advisory, exit code 1. The interesting part wasn't the count. Three different metrics (cyclomatic complexity per McCabe 197

The hook does three things:

1. Concrete incident in the opening sentence (war story, not product
   launch). The tool is not named.
2. Specific numbers in the first visible line (ten, one, exit code 1)
   that anchor credibility before the claim.
3. Sets up a curiosity gap with "the interesting part wasn't the count"
   that pulls the reader past the truncation point to see what the
   interesting part actually was.

The tool name ("slop") does not appear until the last paragraph, after
the reader has been given a reason to care.

## What not to do

- Do not include the GitHub link in the post body (reach penalty).
- Do not close with "Agree?" or "What do you think?" (engagement bait
  detection). If you want comments, pose a specific question about the
  technical content that only someone who read it can answer.
- Do not tag the audience into controversy (AI slop shaming, "stop
  vibe-coding", etc.). Let the numbers and the walkthrough speak.
- Do not cross-post verbatim from Reddit. Different audience conventions;
  LinkedIn readers skew more credentialed and less tolerant of irony.

## Follow-up options

Depending on how the first post performs:

- **If it lands (>10k impressions, meaningful comment thread):** consider
  turning the before/after into a 8-10 slide PDF carousel. LinkedIn
  document posts are the highest-engagement format in 2026.
- **If a canonical URL on LinkedIn itself would help discoverability:**
  port the before/after content into a LinkedIn Article. Code blocks and
  tables render properly there, no link penalty, and the article gets
  indexed by LinkedIn search in a way feed posts do not.
- **If people ask about specific rules:** follow-up posts each covering
  one metric family (Halstead, NPath, Martin's package metrics) with a
  single concrete example. Each primary source is its own story.
