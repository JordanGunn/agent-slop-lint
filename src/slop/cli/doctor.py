"""``slop doctor``: report the tools slop relies on."""
from __future__ import annotations


def register(sub) -> None:
    sub.add_parser("doctor", help="check slop's tooling dependencies").set_defaults(run=lambda a: doctor())


def doctor() -> int:
    """Exit 0 if every required tool is importable, 2 if not."""
    print("slop doctor\n")
    ok = True
    try:
        import tree_sitter  # noqa: F401
        print("  [ok]   tree-sitter (parsing)")
    except Exception as exc:  # noqa: BLE001
        print(f"  [FAIL] tree-sitter not importable: {exc}")
        ok = False
    print("\nready" if ok else "\nmissing required tooling")
    return 0 if ok else 2
