"""Agent Skills (agentskills.io) that teach an agent to use slop.

A skill is a directory: a ``SKILL.md`` manifest, plus ``references/`` and ``assets/`` that
the manifest points to. Slop builds each skill's files when it installs it, from their single
sources (the prose and schemas other packages own), so an installed skill is never a stale
copy committed beside them. `slop skill list | show | install` serve them.

    model       a Skill: its name, description, manifest body and files; checks the spec
    catalog     every skill slop ships, by name; one function per skill
    install     write a skill's directory

"""
