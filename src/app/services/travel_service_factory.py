class TravelServiceFactory:
    def __init__(self):
        self.strategies = []

    def register_strategy(self, strategy):
        self.strategies.append(strategy)

    def get_strategy(self, prompt):
        for strategy in self.strategies:
            if strategy.should_handle(prompt):
                return strategy
        return None