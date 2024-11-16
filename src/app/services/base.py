from abc import ABC, abstractmethod

class SearchStrategy(ABC):
    @abstractmethod
    def process_query(self, prompt, city=None, reason=None):
        """process query and return  data"""
        pass

    @abstractmethod
    def should_handle(self, prompt):
        """see which strategy to use for current prompt"""
        pass
