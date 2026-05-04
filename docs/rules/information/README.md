# Information rules

Information rules measure information density and readability proxies — the artifact-derived signals that capture how much a reader has to absorb to understand a function. The Halstead-derived rules live here (not under `structural`) because their concept is information density, not code shape.

| Rule | Default | Citation / signal |
|---|---|---|
| [`information.volume`](volume.md) | V > 1500 | Halstead 1977 |
| [`information.difficulty`](difficulty.md) | D > 30 | Halstead 1977 |
| [`information.magic_literals`](magic_literals.md) | > 3 | distinct non-trivial numeric literals per function |
| [`information.section_comments`](section_comments.md) | > 2 | divider comments inside function bodies |

## Category properties

- **Substrate:** operator/operand counts, comment positions, literal frequencies.
- **Compute profile:** fast. Same speed as the structural suite.
- **Determinism:** full.
- **Interpretation burden:** medium. The Halstead numbers require a sentence of explanation; magic-literal and section-comment violations are immediately obvious.

A file can have clean control flow (low CCX) and still be information-dense. The information suite catches that.
