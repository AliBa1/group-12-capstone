from .base import SearchStrategy
from django.conf import settings
from ..models import Flight
import openai
import json
import re
import requests
from django.core.cache import cache
from datetime import datetime, timedelta
from copy import deepcopy


class FlightSearchStrategy(SearchStrategy):
    KEYWORDS = ['flight', 'airplane', 'fly', 'airport']
    BASE_URL = "https://booking-com18.p.rapidapi.com/flights"

    def __init__(self):
        self.api_key = settings.FLIGHTS_API_KEY
    

    def should_handle(self, prompt):
        return any(keyword in prompt.lower() for keyword in self.KEYWORDS)
    
    @staticmethod
    def getcache_key(prefix, identifier):
        safe_identifier = str(identifier).replace(' ', '').lower()
        return f'flightsearch{prefix}_{safe_identifier}'

    def process_query(self, prompt, city=None, reason=None, user=None):
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
            
            flights_data = self._search_flights(origin, destination, date, stops)
            if not flights_data:
                return None
            
            json_payload, flights = self._format_flight_response(flights_data)
            # print("Flight data: ", formatted_data)
            
            self._store_flights(flights)
            dt = datetime.strptime(date, "%Y-%m-%d")
            pretty_date = dt.strftime("%B %d, %Y")
            if stops == 'nonstop_flights':
                response_text = f"I found {len(flights)} nonstop flights between {origin} and {destination} departing on {pretty_date}."
                if len(flights) == 0:
                    response_text += "By default, I search for nonstop flights. Please specify the number of stops you are willing to take in your query."

            else:
                response_text = f"I found {len(flights)} flights including flights with stops between {origin} and {destination} departing on {pretty_date}."
            return {
                'text': response_text,
                'data': json_payload
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
                               f"the proper nearest airport's IATA code. Default to all unless user specifies nonstop flights "
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
        
    def _search_flights(self, origin, dest, date, stops):
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
                "numberOfStops": stops,
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
        
    def _summarise_bound(self, bound):
        segments = bound['segments']
        legs = [s for s in segments if s["__typename"] == "TripSegment"]
        first, last = legs[0], legs[-1]

        dep = datetime.fromisoformat(first["departuredAt"])
        arr = datetime.fromisoformat(last["arrivedAt"])
        total_duration = arr - dep

        layovers = []
        for i in range(1, len(legs)):
            prev = legs[i - 1]           # leg we just finished
            curr = legs[i]               # leg we’re about to start

            start = datetime.fromisoformat(prev["arrivedAt"])
            end   = datetime.fromisoformat(curr["departuredAt"])
            gap   = end - start
            hrs, mins = divmod(gap.seconds // 60, 60)

            layovers.append({
                "airport_iata": prev["destination"]["code"],    # stop *between* legs
                "city":         prev["destination"]["cityName"],
                "duration":     f"{hrs} h {mins} m",
                "arrive": start.strftime("%I:%M %p"),
                "depart": end.strftime("%I:%M %p"),
            })
        return {
            "departure": {
                "airport_iata": first["origin"]["code"],
                "city": first["origin"]["cityName"],
                "time": dep.time(),
            },
            "arrival": {
                "airport_iata": last["destination"]["code"],
                "city": last["destination"]["cityName"],
                "time": arr.time(),
            },
            "stops": len(legs) - 1,
            "layovers": layovers,
            "duration": f"{total_duration.total_seconds()//3600:.0f} h " +
                        f"{(total_duration.total_seconds()%3600)//60:.0f} m",
        }
    
    def _format_flight_response(self, flights_data):
        try:
            flights_list = flights_data.get("flights", []) \
                           if isinstance(flights_data, dict) else flights_data
            formatted_flights = []
            for trip in flights_list:
                bound0 = trip['bounds'][0]
                summary = self._summarise_bound(bound0)
                formatted_flights.append({
                    'flight_date': datetime.fromisoformat(bound0['segments'][0]['departuredAt']).date(),
                    'iata': bound0['segments'][0]['flightNumber'],
                    'duration': summary['duration'],
                    'stops': summary['stops'],
                    'layovers': summary['layovers'],
                    'airline': {
                        'name': bound0['segments'][0]['marketingCarrier']['name'],
                        'iata_code': bound0['segments'][0]['marketingCarrier']['code'],
                    },
                    'departure': {
                        **summary['departure'],
                    },
                    'arrival': {
                        **summary['arrival'],
                    },
                    'booking_url': trip["shareableUrl"],
                    'flight_price': trip['travelerPrices'][0]['price']['price']['value'] / 100,
                })
            json_safe = deepcopy(formatted_flights)
            for curr in json_safe:
                curr['departure']['time'] = curr['departure']['time'].strftime("%I:%M %p")
                curr['arrival']['time'] = curr['arrival']['time'].strftime("%I:%M %p")
                curr['flight_date'] = curr['flight_date'].isoformat()
            return {
                'flights': json_safe,
                'type': 'flight_search'
            }, formatted_flights
        except Exception as e:
            print(f"Error in format_flight_response: {e}")
            return None, None

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

