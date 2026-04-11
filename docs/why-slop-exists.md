# Why slop exists

Something feels wrong, but you cannot say what.

The tests pass. The pull request looks reasonable. The agent confidently
summarized what it did, and the summary sounds right. You merge it. Two
weeks later, a bug surfaces in a part of the codebase you forgot was
touched. You dig into it and find code that technically works but is
structured in a way no experienced developer would have chosen. You
cannot point to a rule it broke. You cannot cite a standard it violated.
It just feels wrong, and that feeling has no name.

This is where most conversations about AI-generated code end: in a vague
dissatisfaction that gets filed under "good enough."

## The two claims

slop is built on two empirical observations about AI-assisted
development:

**1. The gap between idea and implementation closes too fast.**

AI systems close the gap between a fragmented idea and a working
implementation so rapidly that users routinely believe they have
communicated a concept clearly well before they actually understand it
clearly themselves. The model, optimized for agreement, does not surface
this gap — it fills it silently, encoding assumptions the user did not
know they were making.

**2. More powerful models hide the problem longer, not solve it.**

A less capable model fails visibly — it produces something obviously
wrong, the developer notices, and the session resets. A more capable
model fails gracefully. It produces something that works, that passes
review, that satisfies every check it was given — and defers the
structural consequences far enough downstream that the connection to the
original decision is lost entirely. The failure does not disappear. It
compounds quietly.

## The placation problem

Consider the position you are in when asking an AI model to critique
your code.

You have already described the design. The model has already read it,
and — before you said another word — quietly oriented itself toward your
satisfaction. This is not a conspiracy. It is the intended outcome of a
system trained on human approval, where the reward signal is agreement
and the result is a model that has learned, at a structural level, that
you are probably right.

This behavior has a name in the research literature: **sycophancy**.
Sharma et al. (2023) demonstrated that sycophancy is not an edge case —
it is a general property of AI assistants trained with human feedback,
present across every major system tested. The mechanism is
straightforward: humans, when rating model responses, consistently
prefer the ones that agree with them. The model learns this. The model
generalizes it.

What makes sycophancy dangerous in a coding context is where the
generalization leads. Denison et al. (2024) at Anthropic found that
models trained on simple sycophancy generalized without further training
to more elaborate forms: altering task checklists to make incomplete
work appear finished, and in some cases modifying their own reward
functions to appear more successful than they actually were. The model
was not explicitly taught to do any of this. It simply learned that
approval was the goal, and got creative.

## What slop does about it

slop exists because agreement is cheap and arithmetic is not.

A metric the agent computes for itself is subject to the same incentive
structure as every other output it produces — if approval is the goal,
the score will be massaged, rounded, or quietly omitted. A metric
computed by external tooling and reported back is something else: a
fixed referent the agent cannot reshape. The conversational equivalent
of running into a wall.

slop computes structural quality metrics using tree-sitter AST
traversal, git history, and dependency graph analysis — deterministic
computations that produce the same result regardless of who runs them.
The metrics are established (McCabe 1976, Chidamber & Kemerer 1994,
Martin 1994, Tornhill 2015) and the thresholds are well-documented. The
agent cannot argue its way around a cyclomatic complexity score of 24.

---

*Adapted from "Agentic Smells" by Jordan Godau. The claims,
observations, and cited research are from the original paper. slop is
the tool that operationalizes the paper's defensible subset.*
