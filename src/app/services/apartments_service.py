from django.conf import settings
import openai
import json
from .base import SearchStrategy
from ..models import Hotel
import requests
import time
import googlemaps

class ApartmentSearchStrategy(SearchStrategy):
    KEYWORDS = ['apartments', 'rental', 'rentals', 'houses', 'house']

    def __init__(self):
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