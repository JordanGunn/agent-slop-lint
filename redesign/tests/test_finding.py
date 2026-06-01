"""Finding ontology — the coherence invariants are enforced by construction.

Disposition (Verdict/Observation) × Severity are orthogonal; the illegal cells
must be impossible to build."""
from __future__ import annotations

import pytest

from slop.component.identity import ComponentId, ComponentKind
from slop.finding import Action, Disposition, Evidence, Observation, Severity, Verdict

CID = ComponentId(ComponentKind.CALLABLE, "m.f", ())


def test_verdict_is_a_verdict():
    v = Verdict(rule="r", component=CID, action=Action.REDUCE_COMPLEXITY,
                prescription="split it", severity=Severity.ERROR, value=20, threshold=10)
    assert v.disposition is Disposition.VERDICT
    assert v.severity is Severity.ERROR


def test_observation_pins_to_info_and_investigate():
    o = Observation(rule="r", component=CID, evidence=Evidence("token-distribution", {"d": 1}),
                    message="look here")
    assert o.disposition is Disposition.OBSERVATION
    assert o.severity is Severity.INFO          # pinned ClassVar — cannot gate
    assert o.action is Action.INVESTIGATE
    assert not hasattr(o, "prescription")        # no field to set


def test_verdict_severity_must_be_warning_or_error():
    for bad in (Severity.INFO, Severity.OFF):
        with pytest.raises(ValueError):
            Verdict(rule="r", component=CID, action=Action.REDUCE_COMPLEXITY,
                    prescription="x", severity=bad)


def test_review_caps_at_warning():
    # WARNING is allowed; ERROR is rejected (a deferred-remedy finding cannot gate).
    Verdict(rule="r", component=CID, action=Action.REVIEW, prescription="split or confirm facade",
            severity=Severity.WARNING)
    with pytest.raises(ValueError):
        Verdict(rule="r", component=CID, action=Action.REVIEW, prescription="x", severity=Severity.ERROR)


def test_verdict_requires_prescription():
    with pytest.raises(ValueError):
        Verdict(rule="r", component=CID, action=Action.REDUCE_COMPLEXITY, prescription="",
                severity=Severity.WARNING)


def test_investigate_is_not_a_verdict_action():
    with pytest.raises(ValueError):
        Verdict(rule="r", component=CID, action=Action.INVESTIGATE, prescription="x",
                severity=Severity.WARNING)


def test_observation_requires_message():
    with pytest.raises(ValueError):
        Observation(rule="r", component=CID, evidence=Evidence("k"), message="")


def test_as_dict_round_trips_disposition():
    v = Verdict(rule="r", component=CID, action=Action.REVIEW, prescription="x", severity=Severity.WARNING)
    o = Observation(rule="r", component=CID, evidence=Evidence("k", {"n": 1}), message="m")
    assert v.as_dict()["disposition"] == "verdict"
    assert v.as_dict()["action"] == "review"
    assert o.as_dict()["disposition"] == "observation"
    assert o.as_dict()["evidence"] == {"kind": "k", "data": {"n": 1}}
