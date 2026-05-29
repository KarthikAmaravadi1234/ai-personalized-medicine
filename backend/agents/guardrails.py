"""Post-processing safety checks applied to every agent response.

These are deliberately conservative string-level checks suitable for an educational
project. They soften definitive diagnostic language and ensure a disclaimer is present.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.agents.prompts import DISCLAIMER

# Patterns that assert a diagnosis. Matches are softened, not silently dropped.
_DIAGNOSTIC_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\byou (?:have|are diagnosed with)\b", re.IGNORECASE), "you may have signs associated with"),
    (re.compile(r"\byou (?:are|'re) (?:diabetic|hypertensive)\b", re.IGNORECASE), "your data may be associated with"),
    (re.compile(r"\b(?:you )?definitely have\b", re.IGNORECASE), "you may have"),
    (re.compile(r"\bdiagnos(?:e|is|ed)\b", re.IGNORECASE), "assessment"),
]


@dataclass
class GuardrailResult:
    text: str
    modified: bool = False
    notes: list[str] = field(default_factory=list)


def apply_guardrails(text: str, *, has_citations: bool) -> GuardrailResult:
    result = GuardrailResult(text=text)

    for pattern, replacement in _DIAGNOSTIC_PATTERNS:
        if pattern.search(result.text):
            result.text = pattern.sub(replacement, result.text)
            result.modified = True
            result.notes.append(f"softened diagnostic phrasing: {pattern.pattern}")

    if not has_citations:
        result.notes.append("no knowledge citations were available for this response")

    if DISCLAIMER not in result.text:
        result.text = f"{result.text.rstrip()}\n\n{DISCLAIMER}"
        result.modified = True

    return result
