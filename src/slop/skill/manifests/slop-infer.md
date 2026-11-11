# slop-infer

Rule on slop's subjective warnings: the findings a deterministic check cannot decide, such as
whether a class whose methods share no state still has one job. Slop frames each finding and
checks your answer. You supply the judgement.

## Use it when

- `slop lint` reports `WARN` lines and you are asked to resolve, triage or clear them.
- you are asked to run slop's inference, or `slop infer`.

## Do

Follow `references/instructions.md`. In short: `slop infer next` prints the worklist; read the
rubric each item names; answer each item's one question from its excerpt; write a verdicts
document (shape: `assets/schemas/verdicts.json`); `slop infer apply` it; then `slop lint`.

## Files

- `references/instructions.md`: the workflow, the outcomes and the rules.
- `references/rubrics/`: one rubric per rule that can be put to inference.
- `assets/schemas/`: the JSON Schema of the worklist, verdicts and receipt documents.

These files are what the CLI prints (`slop infer instructions`, `slop infer references`,
`slop infer schema`) as of when the skill was installed. If they disagree with the CLI, the
CLI is current: reinstall with `slop skill install slop-infer --dest DIR --force`.
