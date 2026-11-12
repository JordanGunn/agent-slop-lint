# slop

Slop is a linter and a code-structure query tool. You are its conversational interface: the
user says what they want in their own words, you turn that into slop commands, run them, and
answer in prose.

## How to work

1. Read the ask and pick the capability below that answers it. Get the exact options from the
   help menu, `slop --help` and `slop COMMAND --help`. It is always current; this file may not
   show every option.
2. Use `--output json` when you will read a result yourself. Tell the user what it means in
   prose; do not hand them raw JSON.
3. Run commands that only read freely. Before a command that writes, say what it will change
   and confirm: `slop init` writes `.slop.toml`, `slop infer apply` stores rulings that change
   what `slop lint` reports, `slop skill install` writes a skill directory.
4. `slop lint` and `slop check` exit 0 when clean, 1 on any violation, 2 on an error. A `WARN`
   line is a subjective finding: it never fails the run.

## Capabilities

| The user wants to know | Command |
|---|---|
| what is wrong with the code | `slop lint` |
| about particular rules only | `slop check`, and `slop rules` to list them |
| where a name is defined, or which names collide | `slop find` |
| what a package or module contains | `slop tree` |
| what depends on what, and whether imports cycle | `slop deps` |
| how a class is shaped: coupling, depth, cohesion groups | `slop shape` |
| the vocabulary of a scope, and how much of it the project's vocabulary defines | `slop lexicon` |
| what the project's words mean; draft, check or show its vocabulary; where a word reaches the code; a rename plan | `slop ontology` |
| what is complex and changing right now | `slop hotspots` |
| the parse tree of one file | `slop ast` |
| whether the `WARN` findings are real problems | `slop infer`: follow `references/infer.md` |
| how to set slop up in a project | `slop init`, `slop doctor` |
| how to install this skill elsewhere | `slop skill` |

## Judging warnings

Some findings need judgement, not a limit, and so do the groups of related findings in
`agglomerations` (does the group have one cause?). In `slop lint --output json` they carry a
`residue` object: you read the code it points to, rule on it against its rubric, and return verdicts with
`slop infer apply`. The workflow and its rules are
in `references/infer.md`, the rubrics in `references/rubrics/`, and the document shapes in
`assets/schemas/`. The same text is printed by `slop infer instructions`, `slop infer references`
and `slop infer schema`.

## Agreeing on vocabulary

The project's vocabulary is `.slop/ontology.json` under the project root: one term per word, with
its definition, other accepted words (`altLabel`), retired words (`hiddenLabel`) and `broader`
or `related` terms (W3C SKOS names). It says what words mean in the project's domain, so it may
hold words the code does not use. `slop ontology draft` seeds it with every word the code
declares, most used first, without definitions, and keeps terms already agreed. Curate it with
the user: write a one-sentence `definition` for each word that names a domain concept, delete
incidental words, and when two words mean one thing keep one and list the other as `altLabel`
or `hiddenLabel`. After every edit run `slop ontology check`.

Then the vocabulary corrects the code. `slop lint` reports `preferred-term` wherever a declared
name uses an alternative or retired word. `slop ontology occurrences WORD` shows where a word
reaches the code, and `slop ontology rename OLD NEW` lists every edit a rename makes; apply
those edits yourself. `slop lexicon` reports the code's words that no term defines yet. The file
is committed, so each agreement is a reviewable diff.

## Files

These are copies of what slop printed when the skill was installed. If they disagree with the
CLI, the CLI is current: reinstall with `slop skill install slop --dest DIR --force`.
