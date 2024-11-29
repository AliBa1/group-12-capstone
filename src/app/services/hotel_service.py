from amadeus import Client
from django.conf import settings
import openai
import json
from .base import SearchStrategy
from ..models import Hotel
import requests
import time
import googlemaps

class HotelSearchStrategy(SearchStrategy):
    KEYWORDS = ['hotels', 'place to stay', 'accommodation', 'resort', 'motel', 'hotel']

    def __init__(self):
        self.amadeus = Client(
            client_id=settings.AMADEUS_API_KEY,
            client_secret=settings.AMADEUS_API_SECRET
        )
        self.gmaps = googlemaps.Client(key=settings.GOOGLE_PLACES_API_KEY)

    def should_handle(self, prompt):
        return any(keyword in prompt.lower() for keyword in self.KEYWORDS)

    def process_query(self, prompt, city=None, reason=None):
        prompt_location_info = self._query_location_info(prompt)
        
        if prompt_location_info and 'city' in prompt_location_info:
            location_info = prompt_location_info
            original_city = prompt
        elif city:
            location_info = self._get_city_code(city)
            original_city = city
        else:
            location_info = None
            original_city = None
                
        if not location_info or 'city' not in location_info:
            return None

        hotels_data = self._search_hotels(location_info['city'])
        if not hotels_data:
            return None

        enhanced_hotels = self.hotel_details(hotels_data)
        
        self._store_hotels(enhanced_hotels)
        formatted_data = self._format_hotel_response(enhanced_hotels)

        response_text = f"I found {len(enhanced_hotels)} hotels in the {location_info['city']} area"

        return {
            'text': response_text,
            'data': formatted_data
        }

#this one passes the pre selected city from the user
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

#if the user switches city during prompt, we use this one
    def _query_location_info(self, query):
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": f"Extract the city from this query, and if the city name is misspelled, correct it and use the proper city name: '{query}' and return its IATA airport code. "
                              f"Return ONLY a JSON object in this EXACT format: {{\"city\": \"MIA\"}} "
                              f"(replace MIA with the appropriate IATA code)"
                }]
            )
            content = response.choices[0].message.content
            return json.loads(content.strip())
        except Exception as e:
            print(f"Error in query_location_info: {e}")
            return None

    def _get_place_details(self, hotel):
        try:
            places_result = self.gmaps.places(
                query=f"{hotel['name']} hotel",
                location=(hotel['geoCode']['latitude'], hotel['geoCode']['longitude'])
            )

            if places_result['status'] != 'OK' or not places_result['results']:
                return hotel

            place = places_result['results'][0]
            hotel['google_place_id'] = place.get('place_id')
            hotel['google_address'] = place.get('formatted_address')

            details_result = self.gmaps.place(
                place_id=hotel['google_place_id'],
                fields=['photo']
            )

            if 'result' in details_result and 'photos' in details_result['result']:
                photos = details_result['result']['photos'][:3]
                photo_references = [photo['photo_reference'] for photo in photos]
                hotel['photo_references'] = photo_references

            time.sleep(0.2)
            return hotel

        except Exception as e:
            print(f"Error getting place details for {hotel.get('name')}: {e}")
            return hotel
        
    def hotel_details(self, hotels_data):
        enhanced_hotels = []
        for hotel in hotels_data:
            enhanced_hotel = self._get_place_details(hotel)
            enhanced_hotels.append(enhanced_hotel)
        return enhanced_hotels

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
                    hotel_id=hotel_data['hotelId'],
                    defaults={
                        'name': hotel_data['name'],
                        'chain_code': hotel_data.get('chainCode'),
                        'iata_code': hotel_data.get('iataCode'),
                        'dupe_id': hotel_data.get('dupeId'),
                        'latitude': float(hotel_data['geoCode']['latitude']),
                        'longitude': float(hotel_data['geoCode']['longitude']),
                        'country_code': hotel_data['address']['countryCode'],
                        'google_place_id': hotel_data.get('google_place_id'),
                        'google_address': hotel_data.get('google_address'),
                        'photo_references': hotel_data.get('photo_references', []) 
                    }
                )
            except Exception as e:
                print(f"Error creating hotel record: {str(e)}")
                continue

    def _format_hotel_response(self, hotels_data):
        formatted_hotels = []
        
        for hotel in hotels_data:
            photo_references = hotel.get('photo_references', [])
            if not photo_references:
                photo_references = [None, None, None]  
                
            formatted_hotel = {
                'title': hotel['name'],
                'description': hotel.get('google_address', f"Located in {hotel['iataCode']}, {hotel['address']['countryCode']}"),
                'location': f"{hotel['iataCode']}, {hotel['address']['countryCode']}",
                'images': [ref for ref in photo_references if ref], 
                'details': {
                    'name': hotel['name'],
                    'id': hotel['hotelId'],
                    'chain_code': hotel.get('chainCode'),
                    'iata_code': hotel.get('iataCode'),
                    'dupe_id': hotel.get('dupeId'),
                    'location': {
                        'lat': hotel['geoCode']['latitude'],
                        'lng': hotel['geoCode']['longitude']
                    },
                    'google_place_id': hotel.get('google_place_id'),
                    'google_address': hotel.get('google_address')
                }
            }
            formatted_hotels.append(formatted_hotel)

        return {
            'hotels': formatted_hotels,
            'total_results': len(formatted_hotels),
            'type': 'hotel_search'
        }