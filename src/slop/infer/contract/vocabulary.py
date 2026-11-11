"""The closed terms of the contract. Constants only the contract needs live here."""
from __future__ import annotations

from enum import StrEnum

#: Version of every document. A document with another version is rejected, so a skill built
#: against one version never silently reads another.
SCHEMA_VERSION = "1"

#: Longest ``reason`` a verdict may carry. It is the only free text in the exchange.
REASON_MAX_LENGTH = 280


class Outcome(StrEnum):
    """What a verdict decides about one finding."""

    CLEAR = "clear"        # not a problem here: an idiom or an intent the rule cannot see
    CONFIRM = "confirm"    # a real problem: the finding becomes a violation and fails the run
    DEFER = "defer"        # not decidable from what was shown: the finding stays a warning
