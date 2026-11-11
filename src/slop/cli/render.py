"""Output formatting shared by the commands: ``--output``, the view header, locations."""
from __future__ import annotations

import argparse

from ..identity import relative_path


def add_output(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output", choices=["human", "json"], default="human")


def header(command: str, target: str, summary: str) -> str:
    """One scannable header line shared by the views: ``<command>  <target>  · <summary>``,
    command left-aligned to a common column."""
    return f"{command:<8} {target}  · {summary}"


def where(match) -> str:
    """``path:line`` of a definition, or as much of it as is known."""
    return f"{match.path}:{match.line}" if match.path and match.line else (match.path or "-")


def label(target, corpus) -> str:
    """How a view names the scope it reports on: its path, else its qualname, else the corpus."""
    return relative_path(target.id, str(corpus.root)) or target.qualname or corpus.name
