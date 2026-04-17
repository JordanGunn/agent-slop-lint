#!/usr/bin/env bash
# slop skill — agentic code quality linter
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

cmd_help() {
    cat <<'EOF'
slop — agentic code quality linter

Commands:
  help       Show this help message
  init       Emit all skill reference docs (concatenated)
  validate   Verify slop is runnable
  schema     Emit JSON schema for .slop.toml
  run        Execute slop lint (JSON output)

Usage (run):
  skill.sh run --root <path>                Run all rules
  skill.sh run --root <path> --check <cat>  Run one category
  skill.sh run --bootstrap --root <path>    Init config if missing, then lint

EOF
}

cmd_init() {
    local refs_dir="$SKILL_DIR/references"
    local idx=1

    echo "# References"
    echo ""
    for f in "$refs_dir"/[0-9][0-9]_*.md; do
        [[ "$(basename "$f")" == "00_ROUTER.md" ]] && continue
        [[ -f "$f" ]] || continue
        local name desc
        name=$(basename "$f" .md | sed 's/^[0-9]*_//')
        desc=$(grep -m1 '^description:' "$f" 2>/dev/null | sed 's/^description:[[:space:]]*//' || echo "")
        echo "${idx}. **${name}** — ${desc}"
        idx=$((idx + 1))
    done
    echo ""
    echo "---"
    echo ""

    for f in "$refs_dir"/[0-9][0-9]_*.md; do
        [[ "$(basename "$f")" == "00_ROUTER.md" ]] && continue
        [[ -f "$f" ]] || continue
        cat "$f"
        echo ""
    done
}

cmd_validate() {
    local errors=0

    if ! command -v slop &>/dev/null; then
        echo "error: slop not found. Run ./scripts/install.sh" >&2
        errors=$((errors + 1))
    fi

    if ! command -v aux &>/dev/null; then
        echo "error: aux not found. Run ./scripts/install.sh" >&2
        errors=$((errors + 1))
    fi

    if [[ $errors -gt 0 ]]; then
        return 1
    fi

    echo "slop: $(slop --version 2>/dev/null)"
    echo "aux:  $(aux --version 2>/dev/null)"
    echo "ok"
}

cmd_schema() {
    slop schema
}

cmd_run() {
    local bootstrap=false
    local check_target=""
    local root=""
    local args=()

    # Parse our wrapper args
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --bootstrap)
                bootstrap=true
                shift
                ;;
            --check)
                check_target="$2"
                shift 2
                ;;
            --root)
                root="$2"
                args+=("--root" "$2")
                shift 2
                ;;
            *)
                args+=("$1")
                shift
                ;;
        esac
    done

    # Bootstrap: generate config if missing
    if [[ "$bootstrap" == true && -n "$root" ]]; then
        local config_path="$root/.slop.toml"
        local pyproject_path="$root/pyproject.toml"
        if [[ ! -f "$config_path" ]]; then
            # Check if pyproject.toml has [tool.slop]
            if [[ ! -f "$pyproject_path" ]] || ! grep -q '\[tool\.slop\]' "$pyproject_path" 2>/dev/null; then
                (cd "$root" && slop init) >&2
            fi
        fi
    fi

    # Run
    if [[ -n "$check_target" ]]; then
        slop check "$check_target" "${args[@]}" --output json
    else
        slop lint "${args[@]}" --output json
    fi
}

case "${1:-help}" in
    help)      cmd_help ;;
    init)      cmd_init ;;
    validate)  cmd_validate ;;
    schema)    cmd_schema ;;
    run)       shift; cmd_run "$@" ;;
    *)
        echo "error: unknown command '$1'" >&2
        echo "run 'skill.sh help' for usage" >&2
        exit 1
        ;;
esac
