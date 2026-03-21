# src/security/pii_handler.py
"""PII detection and scrubbing using Microsoft Presidio."""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Lazy load Presidio to avoid import overhead when not needed
_analyzer = None
_anonymizer = None

def _get_analyzer():
    global _analyzer
    if _analyzer is None:
        from presidio_analyzer import AnalyzerEngine
        _analyzer = AnalyzerEngine()
    return _analyzer

def _get_anonymizer():
    global _anonymizer
    if _anonymizer is None:
        from presidio_anonymizer import AnonymizerEngine
        _anonymizer = AnonymizerEngine()
    return _anonymizer


@dataclass
class PIIResult:
    """Result of PII detection."""
    has_pii: bool
    entities: List[Dict[str, Any]]
    scrubbed_text: Optional[str] = None


# Default entities to detect
DEFAULT_ENTITIES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "US_SSN",
    "US_PASSPORT",
    "US_DRIVER_LICENSE",
    "IP_ADDRESS",
    "IBAN_CODE",
    "US_BANK_NUMBER",
    "LOCATION",
    "DATE_TIME",
]


class PIIHandler:
    """Handles PII detection and anonymization."""

    def __init__(
        self,
        entities: List[str] = None,
        score_threshold: float = 0.7,
        anonymize_char: str = "*"
    ):
        self.entities = entities or DEFAULT_ENTITIES
        self.score_threshold = score_threshold
        self.anonymize_char = anonymize_char

    def detect(self, text: str) -> PIIResult:
        """Detect PII in text without modifying it."""
        if not text or not text.strip():
            return PIIResult(has_pii=False, entities=[])

        try:
            analyzer = _get_analyzer()
            results = analyzer.analyze(
                text=text,
                entities=self.entities,
                language="en"
            )

            entities = [
                {
                    "type": r.entity_type,
                    "start": r.start,
                    "end": r.end,
                    "score": r.score,
                    "text": text[r.start:r.end] if r.score >= self.score_threshold else "[REDACTED]"
                }
                for r in results
                if r.score >= self.score_threshold
            ]

            return PIIResult(
                has_pii=len(entities) > 0,
                entities=entities
            )
        except Exception as e:
            logger.error(f"PII detection failed: {e}")
            return PIIResult(has_pii=False, entities=[])

    def scrub(self, text: str) -> PIIResult:
        """Detect and anonymize PII in text."""
        if not text or not text.strip():
            return PIIResult(has_pii=False, entities=[], scrubbed_text=text)

        try:
            analyzer = _get_analyzer()
            anonymizer = _get_anonymizer()

            results = analyzer.analyze(
                text=text,
                entities=self.entities,
                language="en"
            )

            # Filter by threshold
            filtered = [r for r in results if r.score >= self.score_threshold]

            if not filtered:
                return PIIResult(has_pii=False, entities=[], scrubbed_text=text)

            # Anonymize
            anonymized = anonymizer.anonymize(
                text=text,
                analyzer_results=filtered
            )

            entities = [
                {
                    "type": r.entity_type,
                    "start": r.start,
                    "end": r.end,
                    "score": r.score
                }
                for r in filtered
            ]

            return PIIResult(
                has_pii=True,
                entities=entities,
                scrubbed_text=anonymized.text
            )
        except Exception as e:
            logger.error(f"PII scrubbing failed: {e}")
            return PIIResult(has_pii=False, entities=[], scrubbed_text=text)


# Module-level singleton for convenience
_handler = None

def _get_handler() -> PIIHandler:
    global _handler
    if _handler is None:
        _handler = PIIHandler()
    return _handler


def detect_pii(text: str) -> PIIResult:
    """Detect PII in text (convenience function)."""
    return _get_handler().detect(text)


def scrub_pii(text: str) -> str:
    """Scrub PII from text, returning anonymized version."""
    result = _get_handler().scrub(text)
    return result.scrubbed_text or text
