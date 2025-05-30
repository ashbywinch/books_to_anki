from line_profiler import profile
from spacy.tokens import Token

from book_complexity.ComplexityCalculators import ComplexityCalculator

class VocabLevels:
    def __init__(self, frequencies, levels):
        self.frequencies = frequencies
        self.levels = levels
        self.default_level = next(iter(self.levels.keys()))

    @profile
    def get_level(self, token: Token) -> str:
        """Return the correct vocabulary level that reflects the frequency of this token"""

        token_frequency = self.frequencies.get(token.text.lower(), 0)
        return next(
            (key for key, level_range in self.levels.items() if token_frequency in level_range),
            self.default_level,
        )


class VocabLevelCalculator(ComplexityCalculator):
    name = "Vocabulary Level"

    def __init__(self, levels:VocabLevels, small_sample_size_cutoff: int):
        self.levels = levels
        # if we don't have enough datapoints, we don't guess
        self.small_sample_size_cutoff = small_sample_size_cutoff

    # A "bar chart" is a dictionary telling us how many datapoints there are with each value
    # We want to know the value of the Nth percentile item
    def percentile(self, bar_chart: dict[str, int], percent) -> str:
        total_datapoints = sum(bar_chart.values())
        datapoints_at_percentile = total_datapoints * (percent / 100)
        running_total = 0
        sorted_keys = sorted(bar_chart.keys())
        assert len(sorted_keys) > 0
        for key in sorted_keys:
            running_total = running_total + bar_chart[key]
            if running_total > datapoints_at_percentile:
                return key

        assert False

    def process_token(self, token: Token):
        return {self.levels.get_level(token): 1}

    # Combine dicts to give total number of words at each level
    def combine_values(self, dict1, dict2):
        return {
            key: dict1.get(key, 0) + dict2.get(key, 0)
            for key in set(dict1) | set(dict2)
        }

    def and_finally(self, dict):
        # If there's not many words, we can't made a good estimate of the vocabulary level
        if sum(dict.values()) < self.small_sample_size_cutoff:
            return ""
        return self.percentile(dict, 95)

    def null_value(self):
        return {}
