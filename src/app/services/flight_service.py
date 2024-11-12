from .base import SearchStrategy

class FlightSearchStrategy(SearchStrategy):
    KEYWORDS = ['flights', 'airplane', 'fly', 'airport']

    def should_handle(self, prompt):
        return any(keyword in prompt.lower() for keyword in self.KEYWORDS)

    def process_query(self, prompt, city=None, reason=None):
        return "\nFlight search functionality coming soon"