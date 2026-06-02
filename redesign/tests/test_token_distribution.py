"""vocabulary rule — the lexicon's one live consumer.

Pins the Observation's evidence on a fixed corpus so the lexicon kernel
(tokenise -> lowercase -> stop-word strip -> count, unioned with fs names) cannot
silently drift the distribution it reports. This is the proof gate for the lexicon
package standing up: the rule's numbers are a function of the kernel.
"""
from __future__ import annotations

from pathlib import Path

from slop.config import RuleConfig
from slop.finding import Disposition, Severity
from slop.scope import scan_corpus
from slop.rules.token_distribution import TokenDistributionRule

SRC = '''\
def process_data(raw_input):
    parsed_value = parse_payload(raw_input)
    normalized = normalize(parsed_value)
    return normalized

def parse_payload(payload):
    return payload.strip()

def normalize(value):
    return value.lower()

class WidgetRenderer:
    def render_widget(self, widget_state):
        return self.compose_widget(widget_state)
    def compose_widget(self, widget_state):
        return widget_state
'''


def _package(tmp_path: Path):
    (tmp_path / "mod.py").write_text(SRC)
    return scan_corpus(tmp_path, config=None).realms()[0].packages()[0]


def _config(floor: int = 1, top: int = 8) -> RuleConfig:
    return RuleConfig(
        name="vocabulary", severity=Severity.INFO,
        params={"package_min_distinct": floor, "top_tokens": top},
    )


def test_evidence_is_pinned(tmp_path: Path):
    findings = list(TokenDistributionRule().check(_package(tmp_path), _config()))
    assert len(findings) == 1
    ev = findings[0].evidence.data
    # Structural counts — a pure function of the kernel's tokenisation.
    assert ev["n"] == 45
    assert ev["distinct"] == 20
    assert ev["hapax"] == 8 and ev["hapax_ratio"] == 0.4
    assert ev["dis"] == 7 and ev["dis_ratio"] == 0.35
    assert ev["spectrum"]["1"] == 8 and ev["spectrum"]["4"] == 3 and ev["spectrum"]["8"] == 1
    # Zipf fit — deterministic over the fixed count vector.
    assert ev["zipf_r2"] == 0.9109
    assert ev["zipf_alpha"] == 0.7245
    assert ev["head_concentration"] == 0.7333
    # Dominant token, stable head (ties sorted by -count then token).
    assert ev["top"][0] == {"token": "widget", "count": 8}
    assert ev["norms"] == {"zipf_alpha": 0.9, "zipf_r2": 0.93, "hapax_ratio": 0.49}


def test_message_narrates_without_a_verdict(tmp_path: Path):
    finding = next(iter(TokenDistributionRule().check(_package(tmp_path), _config())))
    msg = finding.message
    assert "widget" in msg and "dominant concept" in msg
    assert "20 distinct tokens across 45 uses" in msg


def test_is_a_non_gating_observation(tmp_path: Path):
    finding = next(iter(TokenDistributionRule().check(_package(tmp_path), _config())))
    assert finding.disposition is Disposition.OBSERVATION
    assert finding.severity is Severity.INFO


def test_floor_silences_trivial_packages(tmp_path: Path):
    # 20 distinct tokens; a floor above that must produce no finding.
    findings = list(TokenDistributionRule().check(_package(tmp_path), _config(floor=21)))
    assert findings == []
