"""lexical.cohesion — a module foreign to its package's vocabulary (observation).

A foreign-body module (vocabulary disjoint from its package mates) surfaces as a
claim-free observation; cohesive modules and contextless single-module packages stay
silent.
"""
from __future__ import annotations

from pathlib import Path

from slop.finding import Action, Disposition, Severity
from slop.rules import RULE_REGISTRY
from slop.rules.cohesion import CohesionRule
from slop.scope import scan_corpus
from slop.scope.identity import ScopeKind

# Two billing modules sharing a domain vocabulary (customer/invoice/payment/...).
BILLING_A = '''\
def charge_customer_invoice(customer, invoice, payment):
    balance = invoice.balance
    amount = payment.amount
    customer.ledger.append(amount)
    return balance - amount

def refund_customer_invoice(customer, invoice, payment):
    balance = invoice.balance
    amount = payment.amount
    customer.ledger.append(amount)
    return balance + amount
'''

BILLING_B = '''\
def settle_customer_invoice(customer, invoice, payment):
    balance = invoice.balance
    amount = payment.amount
    customer.ledger.append(amount)
    return balance

def void_customer_invoice(customer, invoice, payment):
    balance = invoice.balance
    amount = payment.amount
    customer.ledger.append(amount)
    return balance
'''

# A terminal-colour module whose vocabulary is disjoint from billing — the foreign body.
COLOR_C = '''\
def render_ansi_escape(terminal, palette):
    foreground = palette.foreground
    reset = terminal.reset
    return foreground + reset

def bold_terminal_glyph(terminal, palette):
    glyph = palette.glyph
    weight = terminal.weight
    return glyph + weight
'''


def _modules(scope):
    if scope.KIND == ScopeKind.MODULE:
        yield scope
    for ch in scope.children():
        yield from _modules(ch)


def _by_name(tmp_path: Path) -> dict:
    corpus = scan_corpus(tmp_path, config=None)
    return {m.name: m for m in _modules(corpus)}


def test_default_config():
    rc = CohesionRule.default_config()
    assert CohesionRule.altitudes == frozenset({ScopeKind.MODULE})
    assert rc.param("max_cohesion") == 0.10
    assert rc.param("min_tokens") == 8


def test_registered():
    assert any(isinstance(r, CohesionRule) for r in RULE_REGISTRY)


def test_foreign_body_fires_as_observation(tmp_path: Path):
    (tmp_path / "billing_a.py").write_text(BILLING_A)
    (tmp_path / "billing_b.py").write_text(BILLING_B)
    (tmp_path / "color_c.py").write_text(COLOR_C)
    mods = _by_name(tmp_path)
    cfg = CohesionRule.default_config()

    findings = list(CohesionRule().check(mods["color_c"], cfg))
    assert len(findings) == 1
    f = findings[0]
    assert f.disposition is Disposition.OBSERVATION
    assert f.action is Action.INVESTIGATE
    assert f.severity is Severity.INFO
    assert f.component.kind is ScopeKind.MODULE
    assert f.evidence.kind == "vocabulary-cohesion"
    assert f.metadata["cohesion"] < 0.10


def test_cohesive_modules_stay_silent(tmp_path: Path):
    (tmp_path / "billing_a.py").write_text(BILLING_A)
    (tmp_path / "billing_b.py").write_text(BILLING_B)
    (tmp_path / "color_c.py").write_text(COLOR_C)
    mods = _by_name(tmp_path)
    cfg = CohesionRule.default_config()
    # The billing siblings share vocabulary, so neither is a foreign body.
    assert list(CohesionRule().check(mods["billing_a"], cfg)) == []
    assert list(CohesionRule().check(mods["billing_b"], cfg)) == []


def test_single_module_package_silent(tmp_path: Path):
    # No rest-of-package to compare against — nothing to say.
    (tmp_path / "lonely.py").write_text(BILLING_A)
    mods = _by_name(tmp_path)
    assert list(CohesionRule().check(mods["lonely"], CohesionRule.default_config())) == []


def test_below_min_tokens_skipped(tmp_path: Path):
    (tmp_path / "billing_a.py").write_text(BILLING_A)
    (tmp_path / "billing_b.py").write_text(BILLING_B)
    (tmp_path / "color_c.py").write_text(COLOR_C)
    mods = _by_name(tmp_path)
    cfg = CohesionRule.default_config()
    cfg.params["min_tokens"] = 999  # nothing clears the floor
    assert list(CohesionRule().check(mods["color_c"], cfg)) == []
