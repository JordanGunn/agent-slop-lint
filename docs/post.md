# LinkedIn post

Paste **Main post** into the LinkedIn composer. Publish, then within 1-2
minutes add **First comment** as a reply to your own post so it surfaces
at the top for early readers and dodges the in-body external-link
penalty.

Rationale and alternative formats (PDF carousel, LinkedIn Article) are
in [linkedin.md](linkedin.md).

---

## Main post

```
"Something feels wrong, but you can't say what." Every developer has had this moment. Tests pass, the PR reads fine, something is still off. Articulating it used to take a decade of developing a nose.

A body of research from 1976 to 2002 had already reduced most of "feels wrong" to arithmetic. McCabe gave us cyclomatic complexity in 1976. Halstead followed with operator/operand density in 1977. Nejmeh added NPath in 1988. Martin applied the same approach to package architecture in 1994. Most of us memorized a few for an exam and promptly forgot them, because intuition was cheaper to apply than the math.

Then agents started writing the code. Agents have no intuition. "This feels off" does not land with a model that only hears words. The fix is to replace the feeling with a number. "NPath 1024 because this is a 10-branch dispatch pretending to be procedural code" is something a human and an agent can both act on. Shared vocabulary, not shared taste.

I ran a metric suite against its own source last week. Ten violations, exit code 1. Three metrics converged on the same function. The CLI entry point had NPath 1024 (ten sequential if-blocks, 2^10). Refactored to a dict lookup. NPath dropped to 8. None of the fixes were clever. The code had been written and reviewed by agents, and nobody human had read it closely.

A reviewer on their fourth PR of the afternoon is more likely to wave through incoherent code, not less. Without shared vocabulary, the slop compounds commit by commit.

The metrics are forty years old, precise, computable, and largely unread. That is fixable. The linter is called slop (on PyPI as agent-slop-lint). Walkthrough in the first comment.
```

Character count: ~1,575. Upper edge of the 1,300-1,600 full-engagement band.
The shape is idea-first (shared vocabulary, old metrics revival), not incident-first.
The slop before/after sits in the middle as a single concrete example that proves
the thesis, not as the headline.

---

## First comment

```
Full walkthrough with before/after code diffs and the delta table:
https://github.com/JordanGunn/agent-slop-lint/blob/main/docs/after.md

Original incident report (raw terminal output and which functions got flagged):
https://github.com/JordanGunn/agent-slop-lint/blob/main/docs/before.md

Primary sources (McCabe 1976, Halstead 1977, Nejmeh 1988, Campbell 2018, Martin 1994, Lakos 1996, Martin 2002, Tornhill 2015):
https://github.com/JordanGunn/agent-slop-lint/blob/main/docs/philosophy/references.md
```

---

## Posting checklist

- Tuesday-Thursday morning, your timezone. First 60 minutes decide reach.
- Post the main body first. Wait for it to render, confirm no
  auto-generated link preview appeared.
- Within 1-2 minutes, add the first comment.
- Do not edit the main post after publishing unless necessary; edits can
  suppress distribution.
- If you have 2-3 colleagues who would engage honestly, a nudge to read
  and comment in the first hour materially helps the initial window.
