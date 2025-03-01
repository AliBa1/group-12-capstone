from .base import SearchStrategy

class CarRentalSearchStrategy(SearchStrategy):
    KEYWORDS = ['car rental', 'rent a car', 'rental car']

    def should_handle(self, prompt):
        return any(keyword in prompt.lower() for keyword in self.KEYWORDS)

    def process_query(self, prompt, city=None, reason=None, user=None):
        return "\nCar rental search functionality coming soon"