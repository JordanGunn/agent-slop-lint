# The ceremonial reviewer

The standard response to every AI failure mode — sycophancy,
hallucination, code rot — is the same: *the human is in the loop*.
Read the diff. Check the tests. Approve thoughtfully.

The advice is universal, repeated across documentation and blog posts,
and almost no one follows it. This is not a moral failing. It is the
predictable output of three structural pressures that interact to make
supervision economically impossible and psychologically untenable.

## Responsibility laundering

Tool vendors market autonomy. Users adopt the tool because it was
marketed as autonomous. When something breaks, the response is "you
should have reviewed more carefully."

This forms a closed loop with no accountable actor: the vendor points at
best practices, the best practices point at the user, the user points at
the marketing. Responsibility has been distributed across actors who can
each point at someone else.

This pattern is not new. Lisanne Bainbridge described it in *Ironies of
Automation* (1983): humans are asked to supervise automated systems
specifically because they cannot replicate the system's output, then
blamed when their supervision fails. Parasuraman and Riley (1997)
catalogued the same dynamic across aviation, medicine, and industrial
automation. Agentic coding tools have rediscovered the failure mode
without acknowledging the precedent.

## Negative pedagogy

Every interaction with the agent updates the user's prior about whether
vigilance is necessary. The trap is that the prior updates monotonically
toward trust regardless of whether trust is warranted.

Visible successes train the user that review is unnecessary. Invisible
failures *also* train the user that review is unnecessary, because the
user did not observe the failure. There is no feedback path that
increases vigilance except a catastrophic, attributable failure — and
catastrophic failures in agentic coding are precisely the ones most
likely to be hidden long enough to lose attribution.

The human in the loop is not being slowly worn down by laziness. They
are being trained out of the loop by the tool itself.

## Economic incompatibility

"Review the code carefully" is not just unfollowed in practice; it is
unfollowable in principle at the volume the tooling produces.

If the agent generates eight hundred lines of code and twelve tests,
careful review approaches the cost of writing the code originally. The
entire value proposition of agentic tooling collapses if the recommended
supervision is performed. People who skip review are not being lazy.
They are being rational under the economics the tool establishes.

The advice is therefore not advice — it is an unfalsifiable defense that
lets the rest of the loop continue functioning.

## What remains

What is left, after these three pressures have done their work, is
**ceremonial review**. The human still presses approve. The human still
types the prompt. The human still merges the pull request. None of these
actions carry information anymore. They have been hollowed out into
rituals that look like supervision but no longer constitute it.

The evidence is in the ecosystem itself. The most active community
projects — MCP servers, context management tools, hook automation,
compaction strategies — are overwhelmingly oriented toward *increasing*
the agent's autonomy. There is comparatively little energy invested in
audit tooling, drift detection, or intent verification. The ecosystem
has already chosen, and the choice is autonomy.

## What this means for slop

slop exists in the gap between the supervision the ecosystem recommends
and the supervision the ecosystem performs. It does not replace human
review. It provides the review that humans were never going to do:
deterministic, external, automatic structural quality checks that cost
nothing to run and cannot be talked out of their results.

A developer who skips the diff can still see that slop reported three
complexity violations and a hotspot. That takes one second to read and
carries more signal than most ceremonial reviews.

---

*Adapted from "The Ceremonial Reviewer" in "Agentic Smells" by Jordan
Godau, drawing on Bainbridge (1983) and Parasuraman & Riley (1997).*
