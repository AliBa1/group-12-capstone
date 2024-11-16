from .base import SearchStrategy

class ApartmentSearchStrategy(SearchStrategy):
    KEYWORDS = ['apartments', 'rental', 'rentals']

    def should_handle(self, prompt):
        return any(keyword in prompt.lower() for keyword in self.KEYWORDS)

    def process_query(self, prompt, city=None, reason=None):
        return "\napartments search functionality coming soon"