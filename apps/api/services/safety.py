"""
Safety wrapper for all model and LLM outputs.

Exports:
  DISCLAIMER: str
  class SafetyEnvelope(BaseModel)
  def wrap_with_uncertainty(...) -> SafetyEnvelope
  def scan_for_forbidden(text: str) -> bool  # returns True if a forbidden phrase is found
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

DISCLAIMER: str = (
    "Goldeneye is a research and decision-support terminal. It does not provide personalized "
    "financial advice, does not execute trades against real brokers, and does not guarantee "
    "any forecast or scenario. Paper trading is simulated. For research, education, and "
    "decision-quality practice only."
)

# Forbidden phrases (case-insensitive, word-bounded)
_FORBIDDEN_PHRASES: list[str] = [
    "guaranteed",
    "guarantee",
    "will profit",
    "sure thing",
    "risk-free",
    "no risk",
    "buy now",
    "sell now",
    "go long",
    "go short",
    "you should buy",
    "you should sell",
    "i recommend",
    "my recommendation",
    "this is a buy",
    "this is a sell",
    "hot tip",
    "moonshot",
    "to the moon",
]

# Compile phrase patterns (word-bounded where applicable; phrases with spaces use lookaround)
_PHRASE_PATTERNS: list[re.Pattern[str]] = []
for _phrase in _FORBIDDEN_PHRASES:
    # Escape the phrase and wrap in word boundaries
    _escaped = re.escape(_phrase)
    # For multi-word phrases the leading/trailing \b may not work on non-word chars like spaces;
    # use (?<!\w) and (?!\w) around the whole phrase for robust boundary detection.
    _PHRASE_PATTERNS.append(
        re.compile(r"(?<!\w)" + _escaped + r"(?!\w)", re.IGNORECASE)
    )

# Certainty-about-future-price regex
_CERTAINTY_REGEX: re.Pattern[str] = re.compile(
    r"\b(will|going to)\s+(hit|reach|break)\s+\$?\d",
    re.IGNORECASE,
)


class SafetyEnvelope(BaseModel):
    confidence: Literal["low", "medium", "high"]
    caveats: list[str]
    as_of: datetime
    disclaimer: str = DISCLAIMER


class SafetyViolation(Exception):
    """Raised when LLM output contains a forbidden phrase after retry."""


def scan_for_forbidden(text: str) -> bool:
    """
    Returns True if the text contains any forbidden phrase or certainty-about-price assertion.
    True means a violation is present.
    """
    for pattern in _PHRASE_PATTERNS:
        if pattern.search(text):
            return True
    if _CERTAINTY_REGEX.search(text):
        return True
    return False


def wrap_with_uncertainty(
    payload: object,
    *,
    confidence: str,
    caveats: list[str],
    as_of: datetime,
) -> SafetyEnvelope:
    """
    Wraps a model or LLM output payload in a SafetyEnvelope.

    Args:
        payload: The underlying output (not stored in the envelope; callers handle separately).
        confidence: One of "low", "medium", "high".
        caveats: Non-empty list of caveat strings.
        as_of: Timestamp of the freshest input data.

    Returns:
        SafetyEnvelope with the provided metadata and the standard DISCLAIMER.
    """
    return SafetyEnvelope(
        confidence=confidence,  # type: ignore[arg-type]
        caveats=caveats,
        as_of=as_of,
        disclaimer=DISCLAIMER,
    )
