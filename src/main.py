from app.services.flight_service import FlightSearchStrategy
import json

def main():
    strat = FlightSearchStrategy()
    prompt = 'Las Vegas to Miami from 2024-12-12 to 2024-12-17'
    origin, destination, leave_date, return_date = strat._query_location_info(prompt)
    print(origin, destination, leave_date, return_date)

if __name__ == "__main__":
    main()