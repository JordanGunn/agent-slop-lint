"""System dependency checker."""

from __future__ import annotations

import importlib

from slop._aux.util.subprocess import run_tool, which

REQUIRED_TOOLS = {
    "rg": {
        "name": "ripgrep",
        "install": "https://github.com/BurntSushi/ripgrep#installation",
        "commands": ["grep"],
    },
    "fd": {
        "name": "fd-find",
        "install": "https://github.com/sharkdp/fd#installation",
        "commands": ["find"],
        "alternatives": ["fdfind"],  # Debian/Ubuntu
    },
}

OPTIONAL_TOOLS = {
    "git": {
        "name": "git",
        "install": "https://git-scm.com/downloads",
        "commands": ["hotspots"],
        "description": "Git version control (required for the hotspots rule)",
    },
}

REQUIRED_PYTHON_PACKAGES = {
    "tree_sitter": {
        "name": "tree-sitter",
        "install": "pip install agent-slop-lint",
        "commands": ["complexity", "class", "halstead", "npath", "deps", "packages"],
        "description": "AST parsing used by every rule that reads source structure",
    },
}

OPTIONAL_PYTHON_PACKAGES: dict[str, dict] = {}


def check_tool(name: str) -> dict:
    """Check if a tool is available and get its version.

    Args:
        name: Tool name

    Returns:
        Dict with availability and version info
    """
    info = REQUIRED_TOOLS.get(name, {"name": name, "install": "Unknown"})

    # Check main name and alternatives
    names_to_check = [name] + info.get("alternatives", [])
    found_path = None
    found_name = None

    for check_name in names_to_check:
        path = which(check_name)
        if path:
            found_path = path
            found_name = check_name
            break

    if not found_path:
        return {
            "name": name,
            "available": False,
            "path": None,
            "version": None,
            "install": info["install"],
        }

    # Try to get version
    version = None
    try:
        result = run_tool([found_name, "--version"], timeout=5.0)
        if result.ok and result.stdout:
            version = result.stdout.strip().split("\n")[0]
    except Exception:
        pass

    return {
        "name": name,
        "available": True,
        "path": str(found_path),
        "version": version,
        "actual_name": found_name if found_name != name else None,
    }


def check_python_package(name: str) -> dict:
    """Check if a Python package (required or optional) is importable.

    Args:
        name: Import name of the package (e.g. "tree_sitter")

    Returns:
        Dict with availability info
    """
    info = REQUIRED_PYTHON_PACKAGES.get(name) or OPTIONAL_PYTHON_PACKAGES.get(
        name, {"name": name, "install": "pip install " + name}
    )

    try:
        mod = importlib.import_module(name)
        version = getattr(mod, "__version__", None)
        return {
            "name": info["name"],
            "available": True,
            "version": version,
            "description": info.get("description", ""),
        }
    except ImportError:
        return {
            "name": info["name"],
            "available": False,
            "version": None,
            "install": info["install"],
            "description": info.get("description", ""),
        }


def run_doctor() -> dict:
    """Run full system dependency check.

    Returns:
        Dict with check results and overall status
    """
    results = {}
    all_ok = True

    for tool_name in REQUIRED_TOOLS:
        check = check_tool(tool_name)
        results[tool_name] = check
        if not check["available"]:
            all_ok = False

    # Optional system tools (reported but not required)
    for tool_name, info in OPTIONAL_TOOLS.items():
        path = which(tool_name)
        version = None
        if path:
            try:
                r = run_tool([tool_name, "--version"], timeout=5.0)  # type: ignore[arg-type]
                if r.ok and r.stdout:
                    version = r.stdout.strip().split("\n")[0]
            except Exception:
                pass
        results[tool_name] = {
            "name": info["name"],
            "available": path is not None,
            "path": str(path) if path else None,
            "version": version,
            "optional": True,
            "description": info.get("description", ""),
        }

    python_packages = {}
    for pkg_name in REQUIRED_PYTHON_PACKAGES:
        check = check_python_package(pkg_name)
        python_packages[pkg_name] = check
        if not check["available"]:
            all_ok = False

    for pkg_name in OPTIONAL_PYTHON_PACKAGES:
        check = check_python_package(pkg_name)
        check["optional"] = True
        python_packages[pkg_name] = check

    return {
        "ok": all_ok,
        "tools": results,
        "python_packages": python_packages,
        "message": "All dependencies available" if all_ok else "Some dependencies missing",
    }
