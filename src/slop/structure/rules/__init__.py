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

from slop.linter._shim import legacy_v2_shim
from slop.linter.types import RuleDefinition

from .any_type_density import run_any_type_density
from .architecture import run_distance
from .class_metrics import run_coupling, run_inheritance_children, run_inheritance_depth
from .clone_density import run_clone_density
from .complexity import run_cognitive_v2, run_cyclomatic_v2, run_weighted
from .dependencies import run_cycles
from .god_module import run_god_module_v2
from .halstead import run_density_v2, run_volume_v2
from .magic_literals import run_magic_literals_v2
from .npath import run_npath
from .out_parameters import run_out_parameters
from .sibling_calls import run_sibling_call_redundancy
from .stringly_typed import run_stringly_typed

STRUCTURAL_RULES: list[RuleDefinition] = [
    # --- structural.complexity (function-level control flow) ---
    RuleDefinition(
        name="structural.complexity.cyclomatic",
        category="structural.complexity",
        description="Per-function Cyclomatic Complexity (McCabe 1976)",
        default_severity="error",
        default_enabled=True,
        threshold_label="CCX > 10",
        run=run_cyclomatic_v2,
    ),
    RuleDefinition(
        name="structural.complexity.cognitive",
        category="structural.complexity",
        description="Per-function Cognitive Complexity (Campbell 2018)",
        default_severity="error",
        default_enabled=True,
        threshold_label="CogC > 15",
        run=run_cognitive_v2,
    ),
    RuleDefinition(
        name="structural.complexity.npath",
        category="structural.complexity",
        description="Per-function acyclic execution path count (Nejmeh 1988)",
        default_severity="error",
        default_enabled=True,
        threshold_label="NPath > 400",
        run=legacy_v2_shim(run_npath),
    ),

    # --- structural.class (class-level CK metrics + WMC) ---
    RuleDefinition(
        name="structural.class.complexity",
        category="structural.class.complexity",
        description="Per-class sum of method CCX (Chidamber & Kemerer 1994)",
        default_severity="error",
        default_enabled=True,
        threshold_label="WMC > 40",
        run=legacy_v2_shim(run_weighted),
    ),
    RuleDefinition(
        name="structural.class.coupling",
        category="structural.class.coupling",
        description="Class coupling count (Chidamber & Kemerer 1994)",
        default_severity="error",
        default_enabled=True,
        threshold_label="CBO > 8",
        run=legacy_v2_shim(run_coupling),
    ),
    RuleDefinition(
        name="structural.class.inheritance.depth",
        category="structural.class.inheritance.depth",
        description="Inheritance tree depth (Chidamber & Kemerer 1994)",
        default_severity="error",
        default_enabled=True,
        threshold_label="DIT > 4",
        run=legacy_v2_shim(run_inheritance_depth),
    ),
    RuleDefinition(
        name="structural.class.inheritance.children",
        category="structural.class.inheritance.children",
        description="Direct subclass count (Chidamber & Kemerer 1994)",
        default_severity="error",
        default_enabled=True,
        threshold_label="NOC > 10",
        run=legacy_v2_shim(run_inheritance_children),
    ),

    # --- structural.packages (Martin Distance) ---
    RuleDefinition(
        name="structural.packages",
        category="structural.packages",
        description="Package design distance (Martin 1994)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="D' > 0.7",
        run=legacy_v2_shim(run_distance),
    ),

    # --- structural.deps (cycle detection) ---
    RuleDefinition(
        name="structural.deps",
        category="structural.deps",
        description="Dependency cycle detection",
        default_severity="error",
        default_enabled=True,
        threshold_label="cycles",
        run=legacy_v2_shim(run_cycles),
    ),

    # --- structural.redundancy (shared callees between sibling fns) ---
    RuleDefinition(
        name="structural.redundancy",
        category="structural.redundancy",
        description="Sibling top-level functions sharing non-trivial callees (refactoring signal)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="≥ 3 shared",
        run=legacy_v2_shim(run_sibling_call_redundancy),
    ),

    # --- structural.types.sentinels (sentinel str parameters) ---
    RuleDefinition(
        name="structural.types.sentinels",
        category="structural.types.sentinels",
        description="Function parameters annotated str with sentinel names (status, mode, kind, …)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="≤ 8 values",
        run=legacy_v2_shim(run_stringly_typed),
    ),

    # --- structural.types.hidden_mutators (mutated collection parameter detection) ---
    RuleDefinition(
        name="structural.types.hidden_mutators",
        category="structural.types.hidden_mutators",
        description="Functions that mutate collection-typed parameters in place",
        default_severity="warning",
        default_enabled=True,
        threshold_label="any mutation",
        run=legacy_v2_shim(run_out_parameters),
    ),

    # --- structural.types.escape_hatches (escape-hatch type annotation density) ---
    RuleDefinition(
        name="structural.types.escape_hatches",
        category="structural.types.escape_hatches",
        description="Fraction of type annotations using escape-hatch types (Any, interface{}, ...)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="> 30%",
        run=legacy_v2_shim(run_any_type_density),
    ),

    # --- structural.duplication (Type-2 clone detection) ---
    RuleDefinition(
        name="structural.duplication",
        category="structural.duplication",
        description="Type-2 clone detection: structurally identical function bodies",
        default_severity="warning",
        default_enabled=True,
        threshold_label="> 5%",
        run=legacy_v2_shim(run_clone_density),
    ),

    # --- structural.god_module (breadth of top-level definitions) ---
    RuleDefinition(
        name="structural.god_module",
        category="structural.god_module",
        description="Files with too many top-level callable definitions",
        default_severity="warning",
        default_enabled=True,
        threshold_label="> 20",
        run=run_god_module_v2,
    ),

    # --- structural.difficulty.* (Halstead vocabulary/density family) ---
    RuleDefinition(
        name="structural.difficulty.volume",
        category="structural.difficulty",
        description="Per-function Halstead Volume — V = N · log₂(η) (Halstead 1977)",
        default_severity="error",
        default_enabled=True,
        threshold_label="V > 1500",
        run=run_volume_v2,
    ),
    RuleDefinition(
        name="structural.difficulty.density",
        category="structural.difficulty",
        description="Per-function Halstead D — (η₁/2)·(N₂/η₂); operand-reuse density (Halstead 1977)",
        default_severity="error",
        default_enabled=True,
        threshold_label="D > 30",
        run=run_density_v2,
    ),
    RuleDefinition(
        name="structural.magic_literals",
        category="structural.magic_literals",
        description="Distinct non-trivial numeric literals per function (magic numbers)",
        default_severity="warning",
        default_enabled=True,
        threshold_label="> 3",
        run=run_magic_literals_v2,
    ),
]
