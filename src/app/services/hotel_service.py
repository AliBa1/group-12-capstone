from amadeus import Client, ResponseError
from django.conf import settings
import openai
import json
from .base import SearchStrategy
from ..models import Hotel

class HotelSearchStrategy(SearchStrategy):
    KEYWORDS = ['hotels', 'place to stay', 'accommodation', 'resort', 'motel']

    def __init__(self):
        self.amadeus = Client(
            client_id=settings.AMADEUS_API_KEY,
            client_secret=settings.AMADEUS_API_SECRET
        )
        self.google_api_key = settings.GOOGLE_PLACES_API_KEY

    def should_handle(self, prompt):
        return any(keyword in prompt.lower() for keyword in self.KEYWORDS)

    def process_query(self, prompt, city=None, reason=None):

        if city:
            location_info = self._get_city_code(city)
        else:
            location_info = self._query_location_info(prompt)
            
        if not location_info or 'city' not in location_info:
            return None

        hotels_data = self._search_hotels(location_info['city'])
        if not hotels_data:
            return None

        self._store_hotels(hotels_data)
        formatted_data = self._format_hotel_response(hotels_data)
        

        return {
            'text': f"I found {len(hotels_data)} hotels in {location_info['city']}. Here they are:",
            'data': formatted_data
        }

    def _get_city_code(self, city):
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": f"Return the IATA airport code for this city: '{city}'. "
                              f"Return ONLY a JSON object in this EXACT format: {{\"city\": \"MIA\"}} "
                              f"(replace MIA with the appropriate IATA code)"
                }]
            )
            content = response.choices[0].message.content
            return json.loads(content.strip())
        except Exception as e:
            print(f"Error in get_city_code: {e}")
            return None
    
    def _query_location_info(self, query):
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": f"Extract the city from this query: '{query}' and return its IATA airport code. "
                              f"Return ONLY a JSON object in this EXACT format: {{\"city\": \"MIA\"}} "
                              f"(replace MIA with the appropriate IATA code)"
                }]
            )
            content = response.choices[0].message.content
            return json.loads(content.strip())
        except Exception as e:
            print(f"Error in query_location_info: {e}")
            return None

    def _search_hotels(self, city_code, limit=5):
        try:
            hotel_response = self.amadeus.reference_data.locations.hotels.by_city.get(
                cityCode=city_code
            )
            return hotel_response.data[:limit]
        except Exception as e:
            print(f"Error in search_hotels: {e}")
            return []

    def _store_hotels(self, hotels_data):
        for hotel_data in hotels_data:
            try:
                Hotel.objects.update_or_create(
                      hotel_id=hotel_data['hotelId'],  # Use as unique identifier
                    defaults={
                        'name': hotel_data['name'],
                        'chain_code': hotel_data['chainCode'],
                        'iata_code': hotel_data['iataCode'],
                        'dupe_id': hotel_data['dupeId'],
                        'latitude': float(hotel_data['geoCode']['latitude']),
                        'longitude': float(hotel_data['geoCode']['longitude']),
                        'country_code': hotel_data['address']['countryCode']
                    }
                )
            except Exception as e:
                print(f"Error creating hotel record: {str(e)}")
                continue

    def _format_hotel_response(self, hotels_data):
        """
        Format hotel data for card display
        """
        formatted_hotels = []
        
        for hotel in hotels_data:
            # Format the hotel data for display
            formatted_hotel = {
                'title': hotel['name'],
                'description': f"Located in {hotel['iataCode']}, {hotel['address']['countryCode']}",
                'location': f"{hotel['iataCode']}, {hotel['address']['countryCode']}",
                'image': 'https://unsplash.com/photos/white-concrete-high-rise-buildings-near-body-of-water-during-daytime-k1OlQaEK2qI',
                'details': {
                    'name': hotel['name'],
                    'id': hotel['hotelId'],
                    'chain_code': hotel['chainCode'],
                    'iata_code': hotel['iataCode'],
                    'dupe_id': hotel['dupeId'],
                    'location': {
                        'lat': hotel['geoCode']['latitude'],
                        'lng': hotel['geoCode']['longitude']
                    }
                }
            }
            formatted_hotels.append(formatted_hotel)

        return {
            'hotels': formatted_hotels,
            'total_results': len(formatted_hotels),
            'type': 'hotel_search'
        }
        
