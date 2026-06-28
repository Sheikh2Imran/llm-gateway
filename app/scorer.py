"""
Complexity levels:
  LOW    → short, simple, factual prompts → route to cheapest model
  MEDIUM → moderate reasoning needed → mid-tier model
  HIGH   → code generation, long reasoning chains, multi-step tasks → best model
"""

import re
from enum import Enum


class Complexity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Keywords that signal high complexity
HIGH_COMPLEXITY_PATTERNS = [
    r"\bwrite\s+(a\s+)?(full|complete|production|complex)\b",
    r"\barchitect\b",
    r"\brefactor\b",
    r"\bdebug\b",
    r"\boptimize\b",
    r"\banalyze\b.*\bcode\b",
    r"\bstep[- ]by[- ]step\b",
    r"\bcompare\s+and\s+contrast\b",
    r"\bpros\s+and\s+cons\b",
    r"\bwrite\s+a\s+(function|class|module|api|service|script)\b",
    r"\bsql\s+query\b",
    r"\balgorithm\b",
    r"\bunit\s+test\b",
    r"\bsystem\s+design\b",
    r"\bdiagram\b",
]

# Keywords that suggest low complexity
LOW_COMPLEXITY_PATTERNS = [
    r"\bwhat\s+is\b",
    r"\bwho\s+is\b",
    r"\bwhen\s+did\b",
    r"\bdefine\b",
    r"\btranslate\b",
    r"\bsummariz(e|ing)\b",
    r"\blist\s+(the\s+)?\d+\b",
    r"\byes\s+or\s+no\b",
    r"\bspell\b",
    r"\bcount\b",
]

# Token thresholds
LOW_TOKEN_THRESHOLD = 100
HIGH_TOKEN_THRESHOLD = 500


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return max(1, len(text) // 4)


def score_complexity(prompt: str, system_prompt: str = "") -> tuple[Complexity, str]:
    """
    Returns (Complexity, reason_string).
    """
    combined = f"{system_prompt} {prompt}".lower().strip()
    token_estimate = estimate_tokens(combined)

    # Check high complexity patterns first
    for pattern in HIGH_COMPLEXITY_PATTERNS:
        if re.search(pattern, combined, re.IGNORECASE):
            return Complexity.HIGH, f"High-complexity keyword matched: '{pattern}'"

    # Token-based rules
    if token_estimate >= HIGH_TOKEN_THRESHOLD:
        return Complexity.HIGH, f"Long prompt ({token_estimate} est. tokens)"

    # Check low complexity patterns
    for pattern in LOW_COMPLEXITY_PATTERNS:
        if re.search(pattern, combined, re.IGNORECASE):
            return Complexity.LOW, f"Simple query keyword matched: '{pattern}'"

    if token_estimate <= LOW_TOKEN_THRESHOLD:
        return Complexity.LOW, f"Short prompt ({token_estimate} est. tokens)"

    return Complexity.MEDIUM, f"Moderate complexity ({token_estimate} est. tokens)"
