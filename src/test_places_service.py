from app.services.other_service import OtherSearchStrategy
strategy = OtherSearchStrategy()
print(strategy.process_query("Find me attractions in Los Angeles, CA", "Los Angeles, CA"))
# strategy.process_query("Find me attractions in Los Angeles, CA", "Los Angeles, CA")