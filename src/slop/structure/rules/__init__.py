"""Structural rule registry.

Rules that compute per-function, per-class, or per-package metrics from
the ``Structure`` view. The ``information.*`` family (Halstead V/D,
magic literals, section comments) lives here too — they are
function-scoped readability signals that ride on the structural
substrate.

Cross-cutting rules that need git history or whole-tree analysis
(``structural.hotspots``, ``structural.orphans``) live under
``slop.linter.rules`` instead.
"""
from __future__ import annotations

from slop.linter.types import RuleDefinition

from .escape_hatches import run_escape_hatches
from .architecture import run_rigidity, run_uselessness
from .class_metrics import (
    run_coupling,
    run_inheritance_children,
    run_inheritance_depth,
    run_weighted,
)
from .clone_density import run_clone_density
from .combinatorial import run_combinatorial
from .complexity import run_cognitive, run_cyclomatic
from .dependencies import run_cycles
from .god_module import run_god_module
from .halstead import run_density, run_volume
from .magic_literals import run_magic_literals
from .hidden_mutators import run_hidden_mutators
from .redundancy import run_redundancy
from .sentinels import run_sentinels

STRUCTURAL_RULES: list[RuleDefinition] = [
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
        name="structural.complexity.combinatorial",
        category="structural.complexity",
        description="Per-function acyclic execution path count — NPath (Nejmeh 1988)",
        default_severity="error",
        default_enabled=True,
        threshold_label="NPath > 400",
        run=run_combinatorial,
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

    # --- structural.packages.* (Martin 1994 — D' split by failure mode) ---
    RuleDefinition(
        name="structural.packages.rigidity",
        category="structural.packages",
        description="Zone of Pain — stable + concrete packages (Martin 1994)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="pain & D' > 0.7",
        run=run_rigidity,
    ),
    RuleDefinition(
        name="structural.packages.uselessness",
        category="structural.packages",
        description="Zone of Uselessness — unstable + abstract packages (Martin 1994)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="uselessness & D' > 0.7",
        run=run_uselessness,
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

    # --- structural.redundancy (shared callees between sibling fns) ---
    RuleDefinition(
        name="structural.redundancy",
        category="structural.redundancy",
        description="Sibling top-level functions sharing non-trivial callees (refactoring signal)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="≥ 3 shared",
        run=run_redundancy,
    ),

    # --- structural.types.sentinels (sentinel str parameters) ---
    RuleDefinition(
        name="structural.types.sentinels",
        category="structural.types.sentinels",
        description="Function parameters annotated str with sentinel names (status, mode, kind, …)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="≤ 8 values",
        run=run_sentinels,
    ),

    # --- structural.types.hidden_mutators (mutated collection parameter detection) ---
    RuleDefinition(
        name="structural.types.hidden_mutators",
        category="structural.types.hidden_mutators",
        description="Functions that mutate collection-typed parameters in place",
        default_severity="warning",
        default_enabled=True,
        threshold_label="any mutation",
        run=run_hidden_mutators,
    ),

    # --- structural.types.escape_hatches (escape-hatch type annotation density) ---
    RuleDefinition(
        name="structural.types.escape_hatches",
        category="structural.types.escape_hatches",
        description="Fraction of type annotations using escape-hatch types (Any, interface{}, ...)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="> 30%",
        run=run_escape_hatches,
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

    # --- structural.difficulty.* (Halstead vocabulary/density family) ---
    RuleDefinition(
        name="structural.difficulty.volume",
        category="structural.difficulty",
        description="Per-function Halstead Volume — V = N · log₂(η) (Halstead 1977)",
        default_severity="error",
        default_enabled=True,
        threshold_label="V > 1500",
        run=run_volume,
    ),
    RuleDefinition(
        name="structural.difficulty.density",
        category="structural.difficulty",
        description="Per-function Halstead D — (η₁/2)·(N₂/η₂); operand-reuse density (Halstead 1977)",
        default_severity="error",
        default_enabled=True,
        threshold_label="D > 30",
        run=run_density,
    ),
    RuleDefinition(
        name="structural.magic_literals",
        category="structural.magic_literals",
        description="Distinct non-trivial numeric literals per function (magic numbers)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="> 3",
        run=run_magic_literals,
    ),
]
