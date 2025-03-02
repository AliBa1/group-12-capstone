from .base import SearchStrategy
from django.conf import settings
from ..models import Flight
import openai
import json
import re
import requests
from django.core.cache import cache
from datetime import datetime


class FlightSearchStrategy(SearchStrategy):
    KEYWORDS = ['flights', 'airplane', 'fly', 'airport']
    BASE_URL = "https://booking-com18.p.rapidapi.com/flights"

    def __init__(self):
        self.api_key = settings.FLIGHTS_API_KEY
    

    def should_handle(self, prompt):
        return any(keyword in prompt.lower() for keyword in self.KEYWORDS)
    
    @staticmethod
    def getcache_key(prefix, identifier):
        safe_identifier = str(identifier).replace(' ', '').lower()
        return f'flightsearch{prefix}_{safe_identifier}'

    def process_query(self, prompt, city=None, reason=None):
        try:
            origin_iata, destination_iata, date, stops = self._query_location_info(prompt)

            if not origin_iata:
                print("Missing origin city.")
                return None
            if not destination_iata:
                print("Missing dest_iata")
            if not date:
                print("Missing flight date")
            origin = origin_iata.get('origin_city', '')
            destination = destination_iata.get('destination_city', '')
            date = date.get('date', '')
            stops = stops.get('stops', '')
            
            flights_data = self._search_flights(origin, destination, date)
            if not flights_data:
                return None
            
            formatted_data = self._format_flight_response(flights_data)
            flights = formatted_data['flights']
            


            self._store_flights(flights)
            if stops == 'nonstop_flights':
                response_text = f"I found {len(flights)} nonstop flights between {origin} and {destination} departing on {date}."
                if len(flights) == 0:
                    response_text += "By default, I search for nonstop flights. Please specify the number of stops you are willing to take in your query."

            else:
                response_text = f"I found {len(flights)} flights with {stops} stops between {origin} and {destination} departing on {date}."
            return {
                'text': response_text,
                'data': formatted_data
            }
        except Exception as e:
            print(f"Error in process_query: {e}")

    def _clean_json_response(self, response):
    # Remove leading and trailing whitespace
        response = response.strip()
    # Remove code fences if present
    # Matches either triple backticks or triple single quotes with optional 'json' after opening fence
        pattern = r"^(?:```json|'''json|```|''')\s*|\s*(?:```|''')$"
        cleaned = re.sub(pattern, "", response)
        return cleaned

    def _query_location_info(self, query):
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": f"Extract the origin city, destination city, desired flight date, and whether stops are tolerable "
                               f"from this query: '{query}'. If either city name is misspelled, correct it and use "
                               f"the proper nearest airport's IATA code. Default to all unless user specifies only nonstop flights "
                               f"Options for stops are 'all' or 'nonstop_flights' Return ONLY a SINGLE JSON object in this EXACT format: "
                               f"[{{\"origin_city\": \"JFK\"}}, {{\"destination_city\": \"LAX\"}}, {{\"date\": \"YYYY-MM-DD\"}}, {{\"stops\": \"nonstop_flights\"}}]"
                               f"(Replace placeholders with actual values from the query)."
                }]
            )
            mess = response.choices[0].message.content
            mess.strip()
            print(f"content: {mess}")
            clean = self._clean_json_response(mess)
            result = json.loads(clean)

            return result[0], result[1], result[2], result[3]
        except Exception as e:
            print(f"Error in query_location_info: {e}")
            return {},{},{},{}
        
    def _search_flights(self, origin, dest, date):
#        cache_key = self.getcache_key('flights', origin)
#        cached_data = cache.get(cache_key)

#        if cached_data:
#            return cached_data
        try:
            params = {
                # "access_key": self.api_key,
                "fromId": origin,
                "toId": dest,
                "departureDate": date,
                "cabinClass": "ECONOMY",
                "numberOfStops": 'all'
            }
            flights_data = self._make_request("search-oneway", params)
            print(f"flights found: {len(flights_data['flights'])}")
#            cache.set(cache_key, flights_data, timeout=86400)

            return flights_data
        except Exception as e:
            print(f"Error fetching flights: {e}")
            return []

    
    def _make_request(self, endpoint, querystring):
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            # querystring = {"access_key": self.api_key, "iataCode": "LAS", "type": "departure"}
            headers = {
                "x-rapidapi-key": self.api_key,
                "x-rapidapi-host": "booking-com18.p.rapidapi.com"
            }
            api_result = requests.get(url, headers=headers, params=querystring)
            api_result.raise_for_status()
            response = api_result.json().get("data", [])
            return response
        except requests.exceptions.RequestException as e:
            print(f"Error making request to {url}: {e}")
            return []
    
    def _format_flight_response(self, flights_data):
        try:
            formatted_flights = []
            for flight in flights_data['flights']:
                curr = flight['bounds'][0]['segments'][0]
                formatted_flight = {
                    'flight_date': datetime.fromisoformat(curr['departuredAt']).strftime("%Y-%m-%d"),
                    # 'aircraft_model': flight['aircraft'].get('iata'),
                    'iata': curr['flightNumber'],
                    'flight_price': ((flight['travelerPrices'][0]['price']['price']['value']) / 100),
                    'booking_url': flight['shareableUrl'],
                    'airline': {
                        'name': curr['operatingCarrier']['name'],
                        'iata_code': curr['operatingCarrier']['code']
                    },
                    'departure': {
                        'airport_name': curr['origin']['airportName'],
                        'airport_iata': curr['origin']['code'],
                        'time': datetime.fromisoformat(curr['departuredAt']).strftime("%I:%M %p")
                    },
                    'arrival': {
                        'airport_name': curr['destination']['airportName'],
                        'airport_iata': curr['destination']['code'],
                        'time': datetime.fromisoformat(curr['arrivedAt']).strftime("%I:%M %p")
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
                    flight_price=flight['flight_price'],
                    defaults={
                        'airline': flight['airline'].get('name', 'Unknown Airline'),
                        'airline_code': flight['airline'].get('iata_code'),
                        'departure_city': flight['departure'].get('airport_iata'),
                        'departure_time': flight['departure'].get('time'),
                        'arrival_city': flight['arrival'].get('airport_iata'),
                        'arrival_time': flight['arrival'].get('time'),
                    }
                )
            except Exception as e:
                print(f"Error creating flight record: {str(e)}")
                continue



