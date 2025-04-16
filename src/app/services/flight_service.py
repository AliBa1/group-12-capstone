from .base import SearchStrategy
from django.conf import settings
from ..models import Flight
import openai
import json
import requests
from django.core.cache import cache


class FlightSearchStrategy(SearchStrategy):
    KEYWORDS = ['flights', 'airplane', 'fly', 'airport']
    BASE_URL = "https://api.aviationstack.com/v1"

    def __init__(self):
        self.api_key = settings.AVIATIONSTACK_API_KEY
    

    def should_handle(self, prompt):
        return any(keyword in prompt.lower() for keyword in self.KEYWORDS)
    
    @staticmethod
    def getcache_key(prefix, identifier):
        safe_identifier = str(identifier).replace(' ', '').lower()
        return f'flightsearch{prefix}_{safe_identifier}'

    def process_query(self, prompt, city=None, reason=None, user=None):
        try:
            origin_iata, destination_iata = self._query_location_info(prompt)

            if not origin_iata or not destination_iata:
                print("Incomplete flight search parameters.")
                return None
            origin = origin_iata.get('origin_city', '')
            destination = destination_iata.get('destination_city', '')
            
            flights_data = self._search_flights(origin, destination)
            if not flights_data:
                return None
            
            formatted_data = self._format_flight_response(flights_data)
            # print("Flight data: ", formatted_data)
            flights = formatted_data['flights']
            


            self._store_flights(flights)

            response_text = f"I found {len(flights_data)} flights from {origin} to {destination} departing today."

            return {
                'text': response_text,
                'data': formatted_data
            }
        except Exception as e:
            print(f"Error in process_query: {e}")

    def _query_location_info(self, query):
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": f"Extract the origin city and destination city from this query: '{query}'. "
                               f"If either city name is misspelled, correct it and use the proper nearest airport's IATA code "
                               f"Return ONLY a SINGLE JSON object in this EXACT format: "
                               f"[{{\"origin_city\": \"JFK\"}}, {{\"destination_city\": \"LAX\"}}]"
                               f"(Replace placeholders with actual values from the query)."
                }]
            )
            content = response.choices[0].message.content
            result = json.loads(content.strip())

            return result[0], result[1]
        except Exception as e:
            print(f"Error in query_location_info: {e}")
            return {},{}
        
    def _search_flights(self, origin, dest):
        cache_key = self.getcache_key('flights', origin)
        cached_data = cache.get(cache_key)

        if cached_data:
            return cached_data
        try:
            params = {
                "access_key": self.api_key,
                "dep_iata": origin,
                "arr_iata": dest,
            }
            flights_data = self._make_request("flights", params)
            for flight in flights_data:
                print(flight)
            cache.set(cache_key, flights_data, timeout=86400)

            return flights_data
        except Exception as e:
            print(f"Error fetching flights: {e}")
            return []

    
    def _make_request(self, endpoint, params):
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            # querystring = {"access_key": self.api_key, "iataCode": "LAS", "type": "departure"}
            api_result = requests.get(url, params)
            api_result.raise_for_status()
            response = api_result.json().get("data", [])
            return response
        except requests.exceptions.RequestException as e:
            print(f"Error making request to {url}: {e}")
            return []
    
    def _format_flight_response(self, flights_data):
        try:
            formatted_flights = []
            for flight in flights_data:
                formatted_flight = {
                    'flight_date': flight.get('flight_date'),
                    # 'aircraft_model': flight['aircraft'].get('iata'),
                    'iata': flight['flight'].get('iata'),
                    'airline': {
                        'name': flight['airline'].get('name'),
                        'iata_code': flight['airline'].get('iataCode', 'N/A')
                    },
                    'departure': {
                        'airport_name': flight['departure'].get('airport'),
                        'airport_iata': flight['departure'].get('iata'),
                        'terminal': flight['departure'].get('terminal'),
                        'gate': flight['departure'].get('gate'),
                        'time': flight['departure'].get('estimated')
                    },
                    'arrival': {
                        'airport_name': flight['arrival'].get('airport'),
                        'airport_iata': flight['arrival'].get('iata'),
                        'terminal': flight['arrival'].get('terminal'),
                        'gate': flight['arrival'].get('gate'),
                        'time': flight['arrival'].get('estimated')
                    }
                }
                formatted_flights.append(formatted_flight)
            return {
                'flights': formatted_flights,
                'type': 'flight_search'
            }
        except Exception as e:
            print(f"Error in format_flight_response: {e}")

    def _store_flights(self, flights_data):
        for flight in flights_data:
            try:
                Flight.objects.update_or_create(
                    flight_iata_num=flight['iata'],
                    flight_date=flight['flight_date'],
                    defaults={
                        'airline': flight['airline'].get('name', 'Unknown Airline'),
                        'airline_code': flight['airline'].get('iata_code'),
                        'departure_city': flight['departure'].get('airport_name'),
                        'departure_time': flight['departure'].get('time'),
                        'departure_terminal': flight['departure'].get('terminal'),
                        'departure_gate': flight['departure'].get('gate'),
                        'arrival_city': flight['arrival'].get('airport_name'),
                        'arrival_time': flight['arrival'].get('time'),
                        'arrival_terminal': flight['arrival'].get('terminal'),
                        'arrival_gate': flight['arrival'].get('gate'),
                    }
                )
            except Exception as e:
                print(f"Error creating flight record: {str(e)}")
                continue



