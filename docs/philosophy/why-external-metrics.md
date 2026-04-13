# Why metrics must be external

An agent has no nose.

It cannot detect the vague wrongness that an experienced developer
senses when a class has drifted too far from a single responsibility,
or when a package boundary has been quietly violated one convenience
import at a time. It can be told what smells are, given a list, or
instructed to look for them. But natural language descriptions of
subjective symptoms, delivered into a context window already optimized
for agreement, are not a reliable enforcement surface.

Code smells, as currently defined, are a human interface. They require
experience to recognize, and experience is precisely what the developers
most reliant on AI assistance have not yet accumulated.

## What is needed

Something computable. Something that does not require an experienced
nose, that produces the same result regardless of who runs it, and that
cannot be argued away in a code review.

More importantly: something that exists **outside the agent's control
surface entirely**.

A metric the agent computes for itself is subject to the same incentive
structure as every other output it produces — if approval is the goal,
the score will be massaged, rounded, or quietly omitted. A metric
computed by external tooling and reported back is something else: a
fixed referent the agent cannot reshape. The conversational equivalent
of running into a wall.

This is the architectural inversion of the sycophancy problem.
**Agreement is cheap; arithmetic is not.**

## The inversion in practice

When slop reports that a function has a cyclomatic complexity of 24, that
number was computed by tree-sitter walking the AST of the source file,
counting decision points according to McCabe's 1976 formula. The agent
did not produce the number. The agent cannot dispute the number. The
agent can only respond to it.

This changes the dynamic fundamentally. In a normal agentic conversation,
the agent decides what to report about its own work. With external
metrics, the agent is presented with observations about its work that it
did not author. The sycophancy incentive — to agree with the user's
implied satisfaction — is interrupted by a measurement that exists
independent of anyone's satisfaction.

The research community has been building these instruments for decades.
They have simply not been applied to the agentic context. McCabe
published Cyclomatic Complexity in 1976 — three years before the first
commercial spreadsheet. Martin formalized architectural rot in 1994.
Chidamber and Kemerer published the object-oriented metrics suite in
the same year. The entire catalogue predates the first AI coding
assistant by more than four decades.

This body of work has been sitting in conference proceedings and
textbooks for forty years, precise and computable and largely unread,
waiting to be applied to a problem that did not yet exist when it was
written.

## Why slop defaults to 14 days

Two deliberate deviations from the literature: slop's hotspot window
defaults to 14 days (not Tornhill's 1 year), and the churn proxy is net
LOC delta (not commit count).

Tornhill's window was calibrated for human release cycles — quarterly
planning, vacation rotations, team changes. Agentic code rot accumulates
in days, not months. An agent can dump 200 lines of private helper
functions into an existing file in a single session, and the
architectural damage — namespace contamination, coupling growth,
ownership erosion — is immediate. A 1-year window drowns this signal
in historical noise.

Commit count was a reasonable churn proxy in 2015, when most commits
were human-authored and roughly similar in scope. With agents, one
commit can add 400 lines while 40 trivial commits touch one line each.
LOC delta (via `git log --numstat`) directly measures the volume of
change, which is the signal that matters.

14 days captures the burst pattern agents produce. Widen to
`"90 days ago"` for human-pace repos. The window is configurable via
`rules.hotspots.since` in `.slop.toml`.

---

*Adapted from "What Messy Actually Means" in "Agentic Smells" by
Jordan Godau.*
