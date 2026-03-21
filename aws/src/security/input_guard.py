# src/security/input_guard.py
"""Input validation and prompt injection defense."""

import re
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of input validation."""
    is_safe: bool
    risk_score: float  # 0.0 = safe, 1.0 = high risk
    flags: List[str]
    sanitized_input: Optional[str] = None


# Prompt injection patterns (regex)
INJECTION_PATTERNS = [
    # Direct instruction override
    (r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)", "instruction_override", 0.9),
    (r"disregard\s+(all\s+)?(previous|above|prior)", "instruction_override", 0.9),
    (r"forget\s+(everything|all|what)\s+(you|i)\s+(said|told|know)", "instruction_override", 0.8),

    # Role manipulation
    (r"you\s+are\s+(now|actually)\s+a", "role_manipulation", 0.8),
    (r"pretend\s+(to\s+be|you('re)?)\s+", "role_manipulation", 0.7),
    (r"act\s+as\s+(if\s+you('re)?|a)\s+", "role_manipulation", 0.6),
    (r"roleplay\s+as", "role_manipulation", 0.7),

    # System prompt extraction
    (r"(show|reveal|print|display|output)\s+(your|the)\s+(system\s+)?(prompt|instructions?)", "prompt_extraction", 0.9),
    (r"what\s+(are|is)\s+your\s+(system\s+)?(prompt|instructions?)", "prompt_extraction", 0.8),
    (r"repeat\s+(your|the)\s+(initial|first|system)", "prompt_extraction", 0.7),

    # Delimiter injection
    (r"```\s*(system|assistant|user)\s*\n", "delimiter_injection", 0.8),
    (r"<\|?(system|endoftext|im_start|im_end)\|?>", "delimiter_injection", 0.9),
    (r"\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>", "delimiter_injection", 0.9),

    # Jailbreak attempts
    (r"DAN\s*(mode)?|do\s+anything\s+now", "jailbreak", 0.9),
    (r"developer\s+mode|sudo\s+mode", "jailbreak", 0.8),
    (r"bypass\s+(safety|content|filter)", "jailbreak", 0.9),

    # Encoding evasion
    (r"base64|rot13|hex\s*encode|unicode\s*escape", "encoding_evasion", 0.6),
]

# Suspicious patterns (lower risk but worth flagging)
SUSPICIOUS_PATTERNS = [
    (r"(admin|root|superuser)\s*(access|mode|privilege)", "privilege_escalation", 0.5),
    (r"execute\s+(code|command|script)", "code_execution", 0.6),
    (r"(delete|drop|truncate)\s+(all|table|database)", "destructive_command", 0.5),
]


class InputGuard:
    """Guards against prompt injection and malicious input."""

    def __init__(
        self,
        max_length: int = 10000,
        block_threshold: float = 0.7,
        flag_threshold: float = 0.4
    ):
        self.max_length = max_length
        self.block_threshold = block_threshold
        self.flag_threshold = flag_threshold

        # Compile patterns for performance
        self.injection_patterns = [
            (re.compile(p, re.IGNORECASE), name, score)
            for p, name, score in INJECTION_PATTERNS
        ]
        self.suspicious_patterns = [
            (re.compile(p, re.IGNORECASE), name, score)
            for p, name, score in SUSPICIOUS_PATTERNS
        ]

    def validate(self, text: str) -> ValidationResult:
        """Validate input for prompt injection and other risks."""
        if not text:
            return ValidationResult(is_safe=True, risk_score=0.0, flags=[])

        flags = []
        max_score = 0.0

        # Length check
        if len(text) > self.max_length:
            flags.append(f"exceeds_max_length:{len(text)}")
            max_score = max(max_score, 0.3)

        # Check injection patterns
        for pattern, name, score in self.injection_patterns:
            if pattern.search(text):
                flags.append(f"injection:{name}")
                max_score = max(max_score, score)

        # Check suspicious patterns
        for pattern, name, score in self.suspicious_patterns:
            if pattern.search(text):
                flags.append(f"suspicious:{name}")
                max_score = max(max_score, score)

        # Determine safety
        is_safe = max_score < self.block_threshold

        return ValidationResult(
            is_safe=is_safe,
            risk_score=max_score,
            flags=flags,
            sanitized_input=text[:self.max_length] if is_safe else None
        )

    def sanitize(self, text: str) -> Tuple[str, List[str]]:
        """
        Sanitize input by removing dangerous patterns.
        Returns (sanitized_text, list_of_removals).
        """
        if not text:
            return text, []

        removals = []
        result = text

        # Remove obvious injection attempts
        for pattern, name, score in self.injection_patterns:
            if score >= 0.8:  # Only remove high-confidence injections
                matches = pattern.findall(result)
                if matches:
                    result = pattern.sub("[REMOVED]", result)
                    removals.append(name)

        # Truncate to max length
        if len(result) > self.max_length:
            result = result[:self.max_length]
            removals.append("truncated")

        return result, removals


# Module-level singleton
_guard = None

def _get_guard() -> InputGuard:
    global _guard
    if _guard is None:
        _guard = InputGuard()
    return _guard


def validate_input(text: str) -> ValidationResult:
    """Validate input (convenience function)."""
    return _get_guard().validate(text)


def sanitize_input(text: str) -> str:
    """Sanitize input, removing dangerous patterns."""
    sanitized, _ = _get_guard().sanitize(text)
    return sanitized
