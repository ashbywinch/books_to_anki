"""Defines classes for determining and calculating vocabulary levels of words.

This module provides:
- `VocabLevels`: A class to store word frequencies and vocabulary level definitions (e.g., A1, A2 based on frequency ranges)
                 and to look up the level of a given token.
- `VocabLevelCalculator`: A `ComplexityCalculator` subclass that processes tokens from a document
                          to determine an overall vocabulary level for the text, typically by finding
                          a specific percentile (e.g., 95th) of word difficulties.
"""
from typing import Dict # Removed Any, Iterator
from line_profiler import profile
from spacy.tokens import Token

from book_complexity.ComplexityCalculators import ComplexityCalculator

class VocabLevels:
    """Stores word frequencies and vocabulary level definitions, and looks up token levels."""
    def __init__(self, frequencies: Dict[str, int], levels: Dict[str, range]):
        """Initialize VocabLevels.

        Args:
            frequencies: A dictionary mapping lowercase word strings to their frequency count (int).
            levels: A dictionary mapping level names (str, e.g., "A1") to a `range` object 
                    representing the frequency thresholds for that level.
        """
        self.frequencies: Dict[str, int] = frequencies
        self.levels: Dict[str, range] = levels
        # Default level is the first key from the levels dictionary, used if a token's frequency doesn't fall into any defined range.
        # This is on the assumption that most unknown words are proper nouns.
        self.default_level: str = next(iter(self.levels.keys()))

    @profile
    def get_level(self, token: Token) -> str:
        """Return the vocabulary level for the token based on its frequency.
        
        The token's text is lowercased before lookup in the frequencies map.
        """
        token_frequency = self.frequencies.get(token.text.lower(), 0)
        return next(
            (key for key, level_range in self.levels.items() if token_frequency in level_range),
            self.default_level,
        )


class VocabLevelCalculator(ComplexityCalculator):
    """Calculates the overall vocabulary level of a text (e.g., 95th percentile)."""
    name: str = "Vocabulary Level"

    def __init__(self, levels: VocabLevels, small_sample_size_cutoff: int):
        """Initialize VocabLevelCalculator.

        Args:
            levels: A `VocabLevels` instance containing frequency and level definitions.
            small_sample_size_cutoff: The minimum number of words required to calculate
                                      the vocabulary level. Below this, an empty string is returned.
        """
        self.levels: VocabLevels = levels
        self.small_sample_size_cutoff: int = small_sample_size_cutoff

    def percentile(self, bar_chart: Dict[str, int], percent: float) -> str:
        """Calculates the key (level) at a given percentile in a frequency map (bar_chart).

        The bar_chart maps vocabulary levels (str) to the frequency in our text of words at that level (int).
        
        Args:
            bar_chart: A dictionary where keys are level strings and values are their counts.
            percent: The desired percentile (0-100).

        Returns:
            The level string at the specified percentile.
        
        Raises:
            ValueError: If bar_chart is empty.
        """
        if not bar_chart:
            raise ValueError("Cannot calculate percentile for an empty bar_chart.")

        total_datapoints = sum(bar_chart.values())
        if total_datapoints == 0: # Should be caught by the empty bar_chart check, but good for safety
             raise ValueError("Cannot calculate percentile with zero total datapoints.")

        datapoints_at_percentile = total_datapoints * (percent / 100.0)
        running_total = 0
        # Ensure consistent ordering for percentile calculation
        sorted_keys = sorted(bar_chart.keys()) 
        
        for key in sorted_keys:
            running_total += bar_chart[key]
            if running_total > datapoints_at_percentile:
                return key
        
        # Should be reached only if all items are exactly at the percentile boundary or rounding issues
        # or if datapoints_at_percentile is > total_datapoints (e.g. percent > 100), 
        # or if datapoints_at_percentile is 0 and first item count is 0 (not possible with current logic)
        # Returning the last key in sorted order is a reasonable fallback.
        return sorted_keys[-1] 

    def process_token(self, token: Token) -> Dict[str, int]:
        """Processes a single token, returning a frequency map of its vocabulary level.
        
        Args:
            token: The spaCy `Token` to process.
            
        Returns:
            A dictionary like {"level_name": 1}.
        """
        return {self.levels.get_level(token): 1}

    def combine_values(self, dict1: Dict[str, int], dict2: Dict[str, int]) -> Dict[str, int]:
        """Merges two vocabulary level frequency maps by summing counts at each level.
        
        Args:
            dict1: The first frequency map (level string to count).
            dict2: The second frequency map (level string to count).
            
        Returns:
            A new dictionary with combined counts for each level.
        """
        return {
            key: dict1.get(key, 0) + dict2.get(key, 0)
            for key in set(dict1) | set(dict2)
        }

    def and_finally(self, accumulated_levels: Dict[str, int]) -> str:
        """Calculates the final representative vocabulary level from the aggregated frequency map.
        
        Returns an empty string if the total word count is below `small_sample_size_cutoff`.
        Otherwise, returns the 95th percentile vocabulary level.
        
        Args:
            accumulated_levels: The aggregated frequency map (level string to count).
            
        Returns:
            The 95th percentile vocabulary level string, or "" if sample size is too small.
        """
        if sum(accumulated_levels.values()) < self.small_sample_size_cutoff:
            return ""
        try:
            return self.percentile(accumulated_levels, 95.0)
        except ValueError: # Handles empty accumulated_levels if it somehow gets here despite cutoff
            return "" 

    def null_value(self) -> Dict[str, int]:
        """Returns the neutral element for vocabulary level aggregation (an empty dict).
        
        Returns:
            An empty dictionary.
        """
        return {}
