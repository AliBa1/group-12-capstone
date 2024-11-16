from .base import SearchStrategy

class HousingSearchStrategy(SearchStrategy):
    KEYWORDS = ['houses', 'housing', 'house']

    def should_handle(self, prompt):
        return any(keyword in prompt.lower() for keyword in self.KEYWORDS)

    def process_query(self, prompt, city=None, reason=None):
        return "\nHousing search functionality coming soon"