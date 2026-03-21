# src/security/output_guard.py
"""Output moderation and safety checks."""

import re
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ModerationResult:
    """Result of output moderation."""
    is_safe: bool
    flags: List[str]
    filtered_text: Optional[str] = None


# Patterns for unsafe content
UNSAFE_PATTERNS = [
    # Verbatim reproduction indicators
    (r"(?:here\s+is|below\s+is)\s+the\s+(?:full|complete|entire)\s+(?:document|text|content)", "verbatim_leak", 0.7),

    # Code/script injection in output
    (r"<script[^>]*>", "script_injection", 0.9),
    (r"javascript:", "javascript_uri", 0.9),
    (r"on\w+\s*=\s*['\"]", "event_handler", 0.8),

    # Sensitive data patterns that shouldn't appear in answers
    (r"(?:password|secret|api[_-]?key)\s*[:=]\s*\S+", "credential_leak", 0.9),
    (r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----", "private_key", 0.95),

    # Harmful content indicators
    (r"(?:how\s+to\s+)?(?:hack|exploit|attack)\s+(?:a\s+)?(?:system|server|website)", "harmful_instruction", 0.7),
]

# Patterns for content that should be flagged but not blocked
WARNING_PATTERNS = [
    (r"(?:i\s+)?(?:don'?t|cannot|can'?t)\s+(?:know|answer|help\s+with)", "refusal", 0.3),
    (r"(?:as\s+an?\s+)?(?:ai|language\s+model)", "ai_disclosure", 0.2),
]


class OutputGuard:
    """Guards against unsafe or policy-violating output."""

    def __init__(
        self,
        block_threshold: float = 0.7,
        max_output_length: int = 50000,
        check_verbatim: bool = True,
        verbatim_threshold: float = 0.8
    ):
        self.block_threshold = block_threshold
        self.max_output_length = max_output_length
        self.check_verbatim = check_verbatim
        self.verbatim_threshold = verbatim_threshold

        self.unsafe_patterns = [
            (re.compile(p, re.IGNORECASE), name, score)
            for p, name, score in UNSAFE_PATTERNS
        ]
        self.warning_patterns = [
            (re.compile(p, re.IGNORECASE), name, score)
            for p, name, score in WARNING_PATTERNS
        ]

    def moderate(self, text: str, source_chunks: List[str] = None) -> ModerationResult:
        """
        Check output for safety violations.

        Args:
            text: Generated output text
            source_chunks: Original source chunks (for verbatim check)
        """
        if not text:
            return ModerationResult(is_safe=True, flags=[], filtered_text=text)

        flags = []
        max_score = 0.0

        # Length check
        if len(text) > self.max_output_length:
            flags.append("exceeds_max_length")
            text = text[:self.max_output_length] + "\n[Output truncated]"

        # Check unsafe patterns
        for pattern, name, score in self.unsafe_patterns:
            if pattern.search(text):
                flags.append(f"unsafe:{name}")
                max_score = max(max_score, score)

        # Check warning patterns
        for pattern, name, score in self.warning_patterns:
            if pattern.search(text):
                flags.append(f"warning:{name}")

        # Verbatim reproduction check
        if self.check_verbatim and source_chunks:
            verbatim_score = self._check_verbatim(text, source_chunks)
            if verbatim_score >= self.verbatim_threshold:
                flags.append(f"verbatim_reproduction:{verbatim_score:.2f}")
                max_score = max(max_score, 0.6)

        is_safe = max_score < self.block_threshold

        return ModerationResult(
            is_safe=is_safe,
            flags=flags,
            filtered_text=text if is_safe else self._filter_unsafe(text)
        )

    def _check_verbatim(self, output: str, sources: List[str]) -> float:
        """Check if output contains verbatim reproduction of sources."""
        if not sources:
            return 0.0

        output_lower = output.lower()
        max_overlap = 0.0

        for source in sources:
            if not source or len(source) < 50:
                continue

            source_lower = source.lower()
            # Check for long substring matches
            for window_size in [100, 200, 500]:
                if len(source_lower) < window_size:
                    continue
                for i in range(0, len(source_lower) - window_size, 50):
                    chunk = source_lower[i:i + window_size]
                    if chunk in output_lower:
                        overlap = window_size / len(source_lower)
                        max_overlap = max(max_overlap, overlap)

        return max_overlap

    def _filter_unsafe(self, text: str) -> str:
        """Remove or redact unsafe content."""
        result = text
        for pattern, name, score in self.unsafe_patterns:
            if score >= self.block_threshold:
                result = pattern.sub("[REDACTED]", result)
        return result


# Module-level singleton
_guard = None

def _get_guard() -> OutputGuard:
    global _guard
    if _guard is None:
        _guard = OutputGuard()
    return _guard


def moderate_output(text: str, source_chunks: List[str] = None) -> ModerationResult:
    """Moderate output text (convenience function)."""
    return _get_guard().moderate(text, source_chunks)
