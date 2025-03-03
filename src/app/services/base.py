from abc import ABC, abstractmethod

class SearchStrategy(ABC):
    @abstractmethod
    def process_query(self, prompt, city=None, reason=None, user=None):
        pass

    @abstractmethod
    def should_handle(self, prompt):
        pass
