"""``.slop.toml`` template emission for ``slop init``.

``PROFILES`` is the catalog of named threshold sets (default / lax /
strict). ``generate_default_config(profile)`` interpolates one of
those sets into the ``.slop.toml`` template and returns the rendered
text. This is *scaffold emission*, not config loading — it produces a
TOML string ``slop init`` writes to disk, never a ``Config`` instance.

Lives under ``slop.cli`` (next to its only product consumer
``slop.cli.init``) rather than ``slop.config`` to keep the config
package focused on parsing + loading + validating user-supplied config
files.
"""
from __future__ import annotations


PROFILES: dict[str, dict[str, str | int | float | bool | list[str]]] = {
    "default": {
        "cyclomatic_threshold": 10,
        "class_cyclomatic_threshold": 40,
        "cognitive_threshold": 15,
        "cognitive_class_threshold": 60,
        "combinatorial_threshold": 400,
        "combinatorial_class_threshold": 1600,
        "volume_threshold": 1500,
        "volume_class_threshold": 6000,
        "density_threshold": 30,
        "hotspots_since": "14 days ago",
        "hotspots_min_commits": 2,
        "hotspots_fail_on_quadrant": ["hotspot"],
        "max_distance": 0.7,
        "package_severity": "warning",
        "orphans_enabled": False,
        "coupling_threshold": 8,
        "inheritance_depth_threshold": 4,
        "inheritance_children_threshold": 10,
    },
    "lax": {
        "cyclomatic_threshold": 20,
        "class_cyclomatic_threshold": 80,
        "cognitive_threshold": 25,
        "cognitive_class_threshold": 120,
        "combinatorial_threshold": 1000,
        "combinatorial_class_threshold": 4000,
        "volume_threshold": 3000,
        "volume_class_threshold": 12000,
        "density_threshold": 50,
        "hotspots_since": "90 days ago",
        "hotspots_min_commits": 3,
        "hotspots_fail_on_quadrant": ["hotspot"],
        "max_distance": 0.85,
        "package_severity": "warning",
        "orphans_enabled": False,
        "coupling_threshold": 15,
        "inheritance_depth_threshold": 6,
        "inheritance_children_threshold": 20,
    },
    "strict": {
        "cyclomatic_threshold": 6,
        "class_cyclomatic_threshold": 30,
        "cognitive_threshold": 10,
        "cognitive_class_threshold": 40,
        "combinatorial_threshold": 100,
        "combinatorial_class_threshold": 400,
        "volume_threshold": 500,
        "volume_class_threshold": 2000,
        "density_threshold": 20,
        "hotspots_since": "7 days ago",
        "hotspots_min_commits": 1,
        "hotspots_fail_on_quadrant": ["hotspot", "churning_simple"],
        "max_distance": 0.5,
        "package_severity": "error",
        "orphans_enabled": True,
        "coupling_threshold": 5,
        "inheritance_depth_threshold": 3,
        "inheritance_children_threshold": 7,
    },
}


def generate_default_config(profile: str = "default") -> str:
    """Generate a .slop.toml config string for the given profile.

    Valid profiles: ``default``, ``lax``, ``strict``.
    """
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile '{profile}'. Valid: {', '.join(sorted(PROFILES))}")
    profile_cfg = PROFILES[profile]
    quadrants = profile_cfg["hotspots_fail_on_quadrant"]
    assert isinstance(quadrants, list)
    quadrant_list = ", ".join(f'"{quadrant}"' for quadrant in quadrants)
    orphans_enabled = "true" if profile_cfg["orphans_enabled"] else "false"
    return f'''\
# slop — agentic code quality linter
# https://github.com/JordanGunn/agent-slop-lint
# Profile: {profile}

# Root directory (default: ".")
root = "."

# Languages to analyze (default: auto-detect all supported)
# Supported: python, javascript, typescript, go, rust, java, c_sharp
# languages = ["python", "typescript"]

# Global file exclusions (applied to all rules)
# exclude = ["**/test_*", "**/vendor/**"]

# Exemptions are declared names, keyed by scope (functions / classes /
# modules / packages). A finding is suppressed when its symbol is in the
# list for its scope. Global [ignore] applies to every rule; per-rule
# exemptions go under [rules.<rule>.ignore]. Scope-precise — ignoring a
# class never blinds its methods.
# [ignore]
# classes = ["GeneratedModel"]            # suppressed in every rule
#
# [rules.coupling.ignore]
# classes = ["WidgetController"]           # suppressed only for coupling

# Rule names are bare (no scope prefix). Scope is first-class: each rule
# declares the scopes it supports and emits per-scope findings with a
# per-scope threshold in the nested `thresholds` dict. Missing scope key
# in `thresholds` means the rule skips that scope. `slop rules --scope
# function` lists all rules that emit at function scope.

[rules.complexity.cyclomatic]
enabled = true
thresholds = {{ function = {profile_cfg["cyclomatic_threshold"]}, class = {profile_cfg["class_cyclomatic_threshold"]} }}
# function: McCabe CCN per callable (McCabe 1976).
# class: WMC = sum of method CCNs (Chidamber & Kemerer 1994).
severity = "error"

[rules.complexity.cognitive]
enabled = true
thresholds = {{ function = {profile_cfg["cognitive_threshold"]}, class = {profile_cfg["cognitive_class_threshold"]} }}
# function: Cognitive Complexity (Campbell 2018).
# class: sum of method scores. SLOP CALIBRATION — no published threshold.
severity = "error"

[rules.complexity.combinatorial]
enabled = true
thresholds = {{ function = {profile_cfg["combinatorial_threshold"]}, class = {profile_cfg["combinatorial_class_threshold"]} }}
# function: NPath (Nejmeh 1988).
# class: sum of method NPaths. SLOP CALIBRATION — no published threshold.
severity = "error"

[rules.complexity.volume]
enabled = true
thresholds = {{ function = {profile_cfg["volume_threshold"]}, class = {profile_cfg["volume_class_threshold"]} }}
# function: Halstead V = N·log₂η (Halstead 1977).
# class: sum of method V (additive). SLOP CALIBRATION — no published threshold.
severity = "error"

[rules.complexity.density]
enabled = true
thresholds = {{ function = {profile_cfg["density_threshold"]} }}
# Halstead D = (η₁/2)·(N₂/η₂). Function-scope only — D is a density
# ratio, not additive across methods.
severity = "error"

[rules.coupling]
enabled = true
thresholds = {{ class = {profile_cfg["coupling_threshold"]} }}
# CBO at class scope (Chidamber & Kemerer 1994).
severity = "error"

[rules.inheritance.depth]
enabled = true
thresholds = {{ class = {profile_cfg["inheritance_depth_threshold"]} }}
# DIT at class scope (Chidamber & Kemerer 1994).
severity = "error"

[rules.inheritance.children]
enabled = true
thresholds = {{ class = {profile_cfg["inheritance_children_threshold"]} }}
# NOC at class scope (Chidamber & Kemerer 1994).
severity = "error"

[rules.hidden_mutators]
enabled = true
thresholds = {{ function = 1 }}
require_type_annotation = true   # only flag params with explicit collection types
severity = "warning"

[rules.magic_literals]
enabled = true
thresholds = {{ function = 3 }}
severity = "warning"

[rules.god_module]
enabled = true
thresholds = {{ module = 20 }}
severity = "warning"

[rules.escape_hatches]
enabled = true
thresholds = {{ module = 0.30 }}
min_annotations = 5
severity = "warning"

[rules.sentinels]
enabled = true
thresholds = {{ parameter = 8 }}
require_str_annotation = true
severity = "warning"

[rules.rigidity]
enabled = true
thresholds = {{ package = {profile_cfg["max_distance"]} }}
# languages = ["python"]        # optional: restrict to a subset
severity = "{profile_cfg["package_severity"]}"

[rules.uselessness]
enabled = true
thresholds = {{ package = {profile_cfg["max_distance"]} }}
severity = "{profile_cfg["package_severity"]}"

[rules.hotspots]
enabled = true
since = "{profile_cfg["hotspots_since"]}"
min_commits = {profile_cfg["hotspots_min_commits"]}
fail_on_quadrant = [{quadrant_list}]
severity = "error"

[rules.deps]
enabled = true
fail_on_cycles = true
severity = "error"

[rules.orphans]
enabled = {orphans_enabled}
min_confidence = "high"
severity = "warning"

[rules.redundancy]
enabled = true
min_shared = 3      # minimum shared non-trivial callees between two sibling functions
min_score = 0.5     # minimum overlap ratio (shared / max callee count)
severity = "warning"

[rules.duplication]
enabled = true
threshold = 0.05    # flag when > 5% of functions are Type-2 clones
min_leaf_nodes = 10 # ignore trivially short functions
min_cluster_size = 2
severity = "warning"

[rules.lexical.stutter]
enabled = true
min_overlap_tokens = 2     # flag names repeating >= N tokens from any enclosing scope
check_packages = true
check_modules = true
check_classes = true
check_functions = true
severity = "warning"

[rules.lexical.verbosity]
enabled = true
max_tokens = 3             # flag function/class names with more tokens than this
check_classes = true
severity = "warning"

[rules.lexical.hammers]
enabled = true
severity = "warning"
# terms = [...]            # see docs/rules/lexical/hammers.md for per-word config

[rules.lexical.sprawl]
enabled = true
min_alphabet = 3
min_concept_extent = 2
min_concept_intent = 2
severity = "warning"

[rules.lexical.imposters]
enabled = true
min_cluster = 3
exempt_names = ["self", "cls"]
severity = "warning"

[rules.lexical.slackers]
enabled = true
min_cluster = 3
exempt_names = ["self", "cls"]
max_coverage = 0.30        # flag clusters with < this fraction fitting a name template
severity = "warning"

[rules.lexical.confusion]
enabled = true
min_functions = 5
min_islands = 2            # flag files splitting into >= this many disjoint call-islands
min_shared = 3             # redundancy-pair threshold feeding the island clustering
min_score = 0.5            # redundancy-pair overlap threshold
min_island_size = 2
min_cluster_size = 3       # receiver-cluster corroboration size
exempt_names = ["self", "cls"]
severity = "warning"

[rules.runts]
enabled = true
max_init_lines = 5         # flag __init__.py files with more than this many code lines
severity = "warning"

# Instrumentation, not a verdict: emits the identifier token distribution
# (Zipf fit, hapax floor, dominant concepts) as a claim-free observation for
# an agent to investigate. info severity never affects the exit code.
[rules.vocabulary]
enabled = true
top_tokens = 15            # how many leading concepts to name in the narration
package_min_distinct = 40  # per-package hapax listing skips packages below this vocab size
severity = "info"
'''
