"""Rule registry for slop.

Canonical names are suite-prefixed (``structural.*``, ``information.*``,
``lexical.*``) per ``docs/rules/README.md``. The ``category`` field doubles as the
``[rules.<category>]`` table key used by ``DEFAULT_RULE_CONFIGS`` and
generated config files. Legacy names (``complexity.cyclomatic``,
``halstead.volume``, ``npath``, ...) are still accepted via
``slop._compat`` and translated to these canonical names.
"""

from __future__ import annotations

from slop.models import RuleDefinition
from slop.rules.any_type_density import run_any_type_density
from slop.rules.architecture import run_distance
from slop.rules.boilerplate_docstrings import run_boilerplate_docstrings
from slop.rules.class_metrics import run_coupling, run_inheritance_children, run_inheritance_depth
from slop.rules.clone_density import run_clone_density
from slop.rules.complexity import run_cognitive, run_cyclomatic, run_weighted
from slop.rules.composition import run_affix_polymorphism, run_first_parameter_drift
from slop.rules.dead_code import run_unreferenced
from slop.rules.dependencies import run_cycles
from slop.rules.god_module import run_god_module
from slop.rules.halstead import run_difficulty, run_volume
from slop.rules.hotspots import run_churn_weighted
from slop.rules.identifier_singletons import run_identifier_singletons
from slop.rules.local_imports import run_local_imports
from slop.rules.magic_literals import run_magic_literal_density
from slop.rules.name_verbosity import run_name_verbosity
from slop.rules.npath import run_npath
from slop.rules.numbered_variants import run_numbered_variants
from slop.rules.out_parameters import run_out_parameters
from slop.rules.section_comments import run_section_comment_density
from slop.rules.sibling_calls import run_sibling_call_redundancy
from slop.rules.stringly_typed import run_stringly_typed
from slop.rules.stutter import (
    run_stutter,
    run_stutter_callers,
    run_stutter_identifiers,
    run_stutter_namespaces,
)
from slop.rules.tersity import run_tersity
from slop.rules.type_tag_suffixes import run_type_tag_suffixes
from slop.rules.verbosity import run_verbosity
from slop.rules.weasel_words import run_weasel_words

RULE_REGISTRY: list[RuleDefinition] = [
    # --- structural.complexity (function-level control flow) ---
    RuleDefinition(
        name="structural.complexity.cyclomatic",
        category="structural.complexity",
        description="Per-function Cyclomatic Complexity (McCabe 1976)",
        default_severity="error",
        default_enabled=True,
        threshold_label="CCX > 10",
        run=run_cyclomatic,
    ),
    RuleDefinition(
        name="structural.complexity.cognitive",
        category="structural.complexity",
        description="Per-function Cognitive Complexity (Campbell 2018)",
        default_severity="error",
        default_enabled=True,
        threshold_label="CogC > 15",
        run=run_cognitive,
    ),
    RuleDefinition(
        name="structural.complexity.npath",
        category="structural.complexity",
        description="Per-function acyclic execution path count (Nejmeh 1988)",
        default_severity="error",
        default_enabled=True,
        threshold_label="NPath > 400",
        run=run_npath,
    ),

    # --- structural.class (class-level CK metrics + WMC) ---
    RuleDefinition(
        name="structural.class.complexity",
        category="structural.class.complexity",
        description="Per-class sum of method CCX (Chidamber & Kemerer 1994)",
        default_severity="error",
        default_enabled=True,
        threshold_label="WMC > 40",
        run=run_weighted,
    ),
    RuleDefinition(
        name="structural.class.coupling",
        category="structural.class.coupling",
        description="Class coupling count (Chidamber & Kemerer 1994)",
        default_severity="error",
        default_enabled=True,
        threshold_label="CBO > 8",
        run=run_coupling,
    ),
    RuleDefinition(
        name="structural.class.inheritance.depth",
        category="structural.class.inheritance.depth",
        description="Inheritance tree depth (Chidamber & Kemerer 1994)",
        default_severity="error",
        default_enabled=True,
        threshold_label="DIT > 4",
        run=run_inheritance_depth,
    ),
    RuleDefinition(
        name="structural.class.inheritance.children",
        category="structural.class.inheritance.children",
        description="Direct subclass count (Chidamber & Kemerer 1994)",
        default_severity="error",
        default_enabled=True,
        threshold_label="NOC > 10",
        run=run_inheritance_children,
    ),

    # --- structural.hotspots (churn x complexity) ---
    RuleDefinition(
        name="structural.hotspots",
        category="structural.hotspots",
        description="Churn \u00d7 complexity per file (Tornhill 2015)",
        default_severity="error",
        default_enabled=True,
        threshold_label="14d window",
        run=run_churn_weighted,
    ),

    # --- structural.packages (Martin Distance) ---
    RuleDefinition(
        name="structural.packages",
        category="structural.packages",
        description="Package design distance (Martin 1994)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="D' > 0.7",
        run=run_distance,
    ),

    # --- structural.deps (cycle detection) ---
    RuleDefinition(
        name="structural.deps",
        category="structural.deps",
        description="Dependency cycle detection",
        default_severity="error",
        default_enabled=True,
        threshold_label="cycles",
        run=run_cycles,
    ),

    # --- structural.local_imports (function-scoped imports) ---
    RuleDefinition(
        name="structural.local_imports",
        category="structural.local_imports",
        description="Import statements inside function bodies (Python, Julia, Rust)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="any",
        run=run_local_imports,
    ),

    # --- structural.redundancy (shared callees between sibling fns) ---
    RuleDefinition(
        name="structural.redundancy",
        category="structural.redundancy",
        description="Sibling top-level functions sharing non-trivial callees (refactoring signal)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="≥ 3 shared",
        run=run_sibling_call_redundancy,
    ),

    # --- structural.types.sentinels (sentinel str parameters) ---
    RuleDefinition(
        name="structural.types.sentinels",
        category="structural.types.sentinels",
        description="Function parameters annotated str with sentinel names (status, mode, kind, …)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="≤ 8 values",
        run=run_stringly_typed,
    ),

    # --- structural.types.hidden_mutators (mutated collection parameter detection) ---
    RuleDefinition(
        name="structural.types.hidden_mutators",
        category="structural.types.hidden_mutators",
        description="Functions that mutate collection-typed parameters in place",
        default_severity="warning",
        default_enabled=True,
        threshold_label="any mutation",
        run=run_out_parameters,
    ),

    # --- structural.types.escape_hatches (escape-hatch type annotation density) ---
    RuleDefinition(
        name="structural.types.escape_hatches",
        category="structural.types.escape_hatches",
        description="Fraction of type annotations using escape-hatch types (Any, interface{}, ...)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="> 30%",
        run=run_any_type_density,
    ),

    # --- structural.duplication (Type-2 clone detection) ---
    RuleDefinition(
        name="structural.duplication",
        category="structural.duplication",
        description="Type-2 clone detection: structurally identical function bodies",
        default_severity="warning",
        default_enabled=True,
        threshold_label="> 5%",
        run=run_clone_density,
    ),

    # --- structural.god_module (breadth of top-level definitions) ---
    RuleDefinition(
        name="structural.god_module",
        category="structural.god_module",
        description="Files with too many top-level callable definitions",
        default_severity="warning",
        default_enabled=True,
        threshold_label="> 20",
        run=run_god_module,
    ),

    # --- structural.orphans (advisory dead code) ---
    RuleDefinition(
        name="structural.orphans",
        category="structural.orphans",
        description="Unreferenced symbols (advisory)",
        default_severity="warning",
        default_enabled=False,
        threshold_label="",
        run=run_unreferenced,
    ),

    # --- information.* (Halstead-derived information density + readability signals) ---
    RuleDefinition(
        name="information.volume",
        category="information.volume",
        description="Per-function information volume (Halstead 1977)",
        default_severity="error",
        default_enabled=True,
        threshold_label="V > 1500",
        run=run_volume,
    ),
    RuleDefinition(
        name="information.difficulty",
        category="information.difficulty",
        description="Per-function symbol difficulty (Halstead 1977)",
        default_severity="error",
        default_enabled=True,
        threshold_label="D > 30",
        run=run_difficulty,
    ),
    RuleDefinition(
        name="information.magic_literals",
        category="information.magic_literals",
        description="Distinct non-trivial numeric literals per function (magic numbers)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="> 3",
        run=run_magic_literal_density,
    ),
    RuleDefinition(
        name="information.section_comments",
        category="information.section_comments",
        description="Section-divider comments inside function bodies (function overload signal)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="> 2",
        run=run_section_comment_density,
    ),

    # --- lexical.* (naming vocabulary quality) ---
    RuleDefinition(
        name="lexical.stutter.namespaces",
        category="lexical.stutter.namespaces",
        description="Symbol names repeating tokens from the enclosing module path",
        default_severity="warning",
        default_enabled=True,
        threshold_label="\u2265 2 tokens",
        run=run_stutter_namespaces,
    ),
    RuleDefinition(
        name="lexical.stutter.callers",
        category="lexical.stutter.callers",
        description="Method or attribute names repeating tokens from the enclosing class",
        default_severity="warning",
        default_enabled=True,
        threshold_label="\u2265 2 tokens",
        run=run_stutter_callers,
    ),
    RuleDefinition(
        name="lexical.stutter.identifiers",
        category="lexical.stutter.identifiers",
        description="Local variable names repeating tokens from the enclosing function",
        default_severity="info",
        default_enabled=True,
        threshold_label="\u2265 2 tokens",
        run=run_stutter_identifiers,
    ),
    RuleDefinition(
        name="lexical.verbosity",
        category="lexical.verbosity",
        description="Mean identifier word-tokens per function (excessive verbosity)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="mean > 3.0",
        run=run_verbosity,
    ),
    RuleDefinition(
        name="lexical.tersity",
        category="lexical.tersity",
        description="Fraction of identifiers ≤ 2 chars per function (tersity guardrail)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="> 50%",
        run=run_tersity,
    ),
    RuleDefinition(
        name="lexical.name_verbosity",
        category="lexical.name_verbosity",
        description="Function/class names with too many word-tokens (class-without-class signal)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="> 3 tokens",
        run=run_name_verbosity,
    ),
    RuleDefinition(
        name="lexical.numbered_variants",
        category="lexical.numbered_variants",
        description="Identifiers ending in disambiguator suffixes (_1, _v2, _old, _new, ...)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="any match",
        run=run_numbered_variants,
    ),
    RuleDefinition(
        name="lexical.weasel_words",
        category="lexical.weasel_words",
        description="Catchall identifier vocabulary (Manager, Helper, Util, Spec, ...)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="banlist match",
        run=run_weasel_words,
    ),
    RuleDefinition(
        name="lexical.type_tag_suffixes",
        category="lexical.type_tag_suffixes",
        description="Identifier suffixes that restate type annotations (_dict, _path, _str, ...)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="suffix matches type",
        run=run_type_tag_suffixes,
    ),
    RuleDefinition(
        name="lexical.boilerplate_docstrings",
        category="lexical.boilerplate_docstrings",
        description="Docstrings whose content is a subset of the function-name tokens",
        default_severity="warning",
        default_enabled=True,
        threshold_label="content ⊆ name",
        run=run_boilerplate_docstrings,
    ),
    RuleDefinition(
        name="lexical.identifier_singletons",
        category="lexical.identifier_singletons",
        description="Functions where most named locals are used exactly once after assignment",
        default_severity="info",
        default_enabled=True,
        threshold_label="> 60% singleton",
        run=run_identifier_singletons,
    ),
    # --- composition.* (missing-namespace / missing-receiver detection) ---
    RuleDefinition(
        name="composition.affix_polymorphism",
        category="composition.affix_polymorphism",
        description="Missing namespace candidates from affix polymorphism (Wille 1982 FCA)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="≥ 3 alphabet × ≥ 2 ops",
        run=run_affix_polymorphism,
    ),
    RuleDefinition(
        name="composition.first_parameter_drift",
        category="composition.first_parameter_drift",
        description="Missing receiver candidates from first-parameter clustering",
        default_severity="warning",
        default_enabled=True,
        threshold_label="≥ 3 functions sharing param",
        run=run_first_parameter_drift,
    ),
]

RULES_BY_NAME: dict[str, RuleDefinition] = {r.name: r for r in RULE_REGISTRY}

RULES_BY_CATEGORY: dict[str, list[RuleDefinition]] = {}
for _rule in RULE_REGISTRY:
    RULES_BY_CATEGORY.setdefault(_rule.category, []).append(_rule)

CATEGORIES: list[str] = sorted(RULES_BY_CATEGORY.keys())
