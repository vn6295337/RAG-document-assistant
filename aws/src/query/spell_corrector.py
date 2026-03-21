# src/query/spell_corrector.py
"""Spell correction for query preprocessing."""

import re
import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class SpellCheckResult:
    """Result of spell checking."""
    original: str
    corrected: str
    corrections: List[Dict[str, str]]  # [{"original": "teh", "corrected": "the"}]
    was_corrected: bool


# Common misspellings dictionary
COMMON_CORRECTIONS = {
    # Common typos
    "teh": "the",
    "taht": "that",
    "wiht": "with",
    "hte": "the",
    "adn": "and",
    "fo": "of",
    "ot": "to",
    "ti": "it",
    "si": "is",
    "nto": "not",
    "nad": "and",
    "fro": "for",
    "hwo": "who",
    "waht": "what",
    "whta": "what",
    "woudl": "would",
    "couldnt": "couldn't",
    "shouldnt": "shouldn't",
    "wouldnt": "wouldn't",
    "dont": "don't",
    "cant": "can't",
    "wont": "won't",
    "thier": "their",
    "recieve": "receive",
    "beleive": "believe",
    "occured": "occurred",
    "seperate": "separate",
    "definately": "definitely",
    "accomodate": "accommodate",
    "occurence": "occurrence",
    "refered": "referred",
    "untill": "until",
    "accross": "across",
    "begining": "beginning",
    "comming": "coming",
    "diffrent": "different",
    "enviroment": "environment",
    "goverment": "government",
    "immedietly": "immediately",
    "independant": "independent",
    "neccessary": "necessary",
    "occassion": "occasion",
    "publically": "publicly",
    "recomend": "recommend",
    "tommorow": "tomorrow",
    "writting": "writing",
    # Domain-specific
    "documnet": "document",
    "databse": "database",
    "retreive": "retrieve",
    "qeury": "query",
    "serach": "search",
    "indxe": "index",
    "embeding": "embedding",
    "vectore": "vector",
}


class SpellCorrector:
    """
    Simple spell corrector using dictionary lookup and edit distance.

    Uses a combination of:
    1. Common misspelling dictionary
    2. Edit distance for unknown words
    3. Context-aware correction (optional)
    """

    def __init__(
        self,
        custom_dictionary: Dict[str, str] = None,
        vocabulary: List[str] = None,
        max_edit_distance: int = 2
    ):
        self.corrections = {**COMMON_CORRECTIONS}
        if custom_dictionary:
            self.corrections.update(custom_dictionary)

        self.vocabulary = set(vocabulary) if vocabulary else set()
        self.max_edit_distance = max_edit_distance

        # Add correction keys to vocab
        self.vocabulary.update(self.corrections.values())

    def add_vocabulary(self, words: List[str]):
        """Add words to known vocabulary."""
        self.vocabulary.update(w.lower() for w in words)

    def check(self, text: str) -> SpellCheckResult:
        """
        Check and correct spelling in text.

        Args:
            text: Input text to check

        Returns:
            SpellCheckResult with corrections
        """
        if not text:
            return SpellCheckResult(
                original=text,
                corrected=text,
                corrections=[],
                was_corrected=False
            )

        words = self._tokenize(text)
        corrections = []
        corrected_words = []

        for word in words:
            lower_word = word.lower()

            # Check dictionary first
            if lower_word in self.corrections:
                corrected = self.corrections[lower_word]
                # Preserve original case
                corrected = self._preserve_case(word, corrected)
                corrections.append({"original": word, "corrected": corrected})
                corrected_words.append(corrected)

            # Check if word is in vocabulary (skip if known)
            elif lower_word in self.vocabulary or len(lower_word) <= 2:
                corrected_words.append(word)

            # Try edit distance correction
            else:
                suggestion = self._suggest_correction(lower_word)
                if suggestion and suggestion != lower_word:
                    corrected = self._preserve_case(word, suggestion)
                    corrections.append({"original": word, "corrected": corrected})
                    corrected_words.append(corrected)
                else:
                    corrected_words.append(word)

        corrected_text = self._reconstruct(text, words, corrected_words)

        return SpellCheckResult(
            original=text,
            corrected=corrected_text,
            corrections=corrections,
            was_corrected=bool(corrections)
        )

    def _tokenize(self, text: str) -> List[str]:
        """Extract words from text."""
        return re.findall(r'\b[a-zA-Z]+\b', text)

    def _reconstruct(self, original: str, old_words: List[str], new_words: List[str]) -> str:
        """Reconstruct text with corrected words."""
        if len(old_words) != len(new_words):
            return original

        result = original
        for old, new in zip(old_words, new_words):
            if old != new:
                # Replace first occurrence
                result = re.sub(r'\b' + re.escape(old) + r'\b', new, result, count=1)

        return result

    def _preserve_case(self, original: str, corrected: str) -> str:
        """Preserve the case pattern of the original word."""
        if original.isupper():
            return corrected.upper()
        elif original[0].isupper():
            return corrected.capitalize()
        else:
            return corrected.lower()

    def _suggest_correction(self, word: str) -> Optional[str]:
        """
        Suggest correction using edit distance.

        Uses a simplified version of Peter Norvig's spell corrector.
        """
        if not self.vocabulary:
            return None

        # Generate candidates at edit distance 1
        candidates = self._edits1(word)
        known = candidates & self.vocabulary

        if known:
            # Return most common (or first alphabetically)
            return min(known)

        # Try edit distance 2
        if self.max_edit_distance >= 2:
            candidates2 = set()
            for c in candidates:
                candidates2.update(self._edits1(c))
            known2 = candidates2 & self.vocabulary
            if known2:
                return min(known2)

        return None

    def _edits1(self, word: str) -> set:
        """Generate all strings at edit distance 1 from word."""
        letters = 'abcdefghijklmnopqrstuvwxyz'
        splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
        deletes = [L + R[1:] for L, R in splits if R]
        transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
        replaces = [L + c + R[1:] for L, R in splits if R for c in letters]
        inserts = [L + c + R for L, R in splits for c in letters]

        return set(deletes + transposes + replaces + inserts)


# Module-level singleton
_corrector = None


def get_spell_corrector() -> SpellCorrector:
    """Get singleton spell corrector instance."""
    global _corrector
    if _corrector is None:
        _corrector = SpellCorrector()
    return _corrector


def correct_query(query: str) -> SpellCheckResult:
    """
    Correct spelling in a query (convenience function).

    Args:
        query: User query

    Returns:
        SpellCheckResult with corrections
    """
    return get_spell_corrector().check(query)


def correct_query_simple(query: str) -> str:
    """
    Simple correction returning just the corrected text.

    Args:
        query: User query

    Returns:
        Corrected query string
    """
    result = get_spell_corrector().check(query)
    return result.corrected


def build_vocabulary_from_chunks(chunks: List[Dict[str, Any]]) -> List[str]:
    """
    Build vocabulary from document chunks for domain-specific correction.

    Args:
        chunks: List of chunks with 'text' field

    Returns:
        List of unique words
    """
    word_counts = Counter()

    for chunk in chunks:
        text = chunk.get("text", "")
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        word_counts.update(words)

    # Return words that appear more than once (likely not typos)
    return [word for word, count in word_counts.items() if count > 1]
