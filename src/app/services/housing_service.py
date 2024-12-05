from .base import SearchStrategy
from django.conf import settings
import requests
import json
import openai
from ..models import Property, ListingAgent, ListingOffice
from django.core.cache import cache


"""
example request:
url = "https://api.rentcast.io/v1/listings/sale?city=austin&state=tx&status=Active&limit=5"
        https://api.rentcast.io/v1/listings/sale?city=Detroit,MI&status=Active&limit=5
headers = {
    "accept": "application/json",
    "X-Api-Key": "8f2586c8082e4bb285f4f190aaf6f724"
}

response = requests.get(url, headers=headers)
"""


class HousingSearchStrategy(SearchStrategy):
    KEYWORDS = ['houses', 'housing', 'house']

    def __init__(self):
        self.api_key = settings.RENTCAST_API_KEY
        self.base_url = "https://api.rentcast.io/v1/listings/sale"

    def should_handle(self, prompt):
        return any(keyword in prompt.lower() for keyword in self.KEYWORDS)
    
    @staticmethod
    def get_cache_key(prefix, identifier):
        safe_identifier = str(identifier).replace(' ', '_').lower()
        return f'property_search_{prefix}_{safe_identifier}'

    def process_query(self, prompt, city=None, state=None, reason=None):
        prompt_location_info = self._query_location_info(prompt)

        if prompt_location_info and 'city' in prompt_location_info and 'state' in prompt_location_info:
            location_info = prompt_location_info
            original_city = prompt
        elif city and state:
            location_info = {'city': city, 'state': state}
            original_city = city
        else:
            location_info = None
            original_city = None

        if not location_info or 'city' not in location_info or 'state' not in location_info:
            return None

        response = houses_data = self._search_houses(location_info['city'], location_info['state'])
        print(houses_data.text)
        print('test')

        if not response:
            return None
            
        houses_data = response.json()
        
        if not houses_data:
            return None

        self._store_houses(houses_data)
        formatted_data = self._format_house_response(houses_data)

        print("Before accessing 'houses'")
        print(formatted_data)  
        print(formatted_data.get('houses'))
        print("After accessing 'houses'")
        response_text = f"I found {len(houses_data)} houses in the {location_info['city']}, {location_info['state']} area"
        print(f"Found {len(houses_data)} houses in the {location_info['city']}, {location_info['state']} area")
        return {
            'text': response_text,
            'data': formatted_data
        }

    def _query_location_info(self, query):
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": f"Extract the city and state from this query, and if the city name, state name is misspelled, correct it and use the proper city name or state name: '{query}'. "
                              f"Return ONLY a JSON object in this EXACT format: {{\"city\": \"Austin\", \"state\": \"TX\"}} "
                              f"(replace Austin and TX with the appropriate city and state)"
                }]
            )
            content = response.choices[0].message.content
            #print(content)
            return json.loads(content.strip())
        except Exception as e:
            print(f"Error in query_location_info: {e}")
            return None

    def _search_houses(self, city, state, limit=5):
        cache_key = self.get_cache_key('properties', city)
        cached_data = cache.get(cache_key)

        if cached_data:
            return cached_data
        try:
            url = f"{self.base_url}?city={city}&state={state}&status=Active&limit={limit}"
            headers = {
                "accept": "application/json",
                "X-API-KEY": self.api_key
            }
            # print(url)
            #print(headers)
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            cache.set(cache_key, response, timeout=86400)

            #print(response)
            return response
        except Exception as e:
            print(f"Error in search_houses: {e}")
            return None
        
    def _store_houses(self, houses_data):
        for house in houses_data:
            try:
                agent_data = house.get('listingAgent', {})
                agent, _ = ListingAgent.objects.update_or_create(
                    name=agent_data.get('name', ''),
                    defaults={
                        'phone': agent_data.get('phone', ''),
                        'email': agent_data.get('email', ''),
                        'website': agent_data.get('website', '')
                    }
                )

                office_data = house.get('listingOffice', {})
                office, _ = ListingOffice.objects.update_or_create(
                    name=office_data.get('name', ''),
                    defaults={
                        'phone': office_data.get('phone', ''),
                        'email': office_data.get('email', ''),
                        'website': office_data.get('website', '')
                    }
                )

                Property.objects.update_or_create(
                    formatted_address=house['formattedAddress'],
                    defaults={
                        'property_type': house.get('propertyType', ''),
                        'latitude': house.get('latitude', 0),
                        'longitude': house.get('longitude', 0),
                        'bedrooms': house.get('bedrooms', 0),
                        'bathrooms': house.get('bathrooms', 0),
                        'square_footage': house.get('squareFootage', 0),
                        'lot_size': house.get('lotSize', 0),
                        'year_built': house.get('yearBuilt', 0),
                        'price': house.get('price', 0),
                        'listing_type': house.get('listingType', ''),
                        'days_on_market': house.get('daysOnMarket', 0),
                        'mls_name': house.get('mlsName', ''),
                        'mls_number': house.get('mlsNumber', ''),
                        'listing_agent': agent,
                        'listing_office': office
                    }
                )

            except Exception as e:
                print(f"Error storing house: {str(e)}")
                continue

    def _format_house_response(self, houses_data):
        formatted_data = []
        for house in houses_data:
            try:
                formatted_house = {
                    'formattedAddress': house.get('formattedAddress', ''),
                    'propertyType': house.get('propertyType', ''),
                    'latitude': house.get('latitude', 0),
                    'longitude': house.get('longitude', 0),
                    'bedrooms': house.get('bedrooms', 0),
                    'bathrooms': house.get('bathrooms', 0),
                    'squareFootage': house.get('squareFootage', 0),
                    'lotSize': house.get('lotSize', 0),
                    'yearBuilt': house.get('yearBuilt', 0),
                    'price': house.get('price', 0),
                    'listingType': house.get('listingType', ''),
                    'daysOnMarket': house.get('daysOnMarket', 0),
                    'mlsName': house.get('mlsName', ''),
                    'mlsNumber': house.get('mlsNumber', ''),
                    'listingAgent': house.get('listingAgent', {}),
                    'listingOffice': house.get('listingOffice', {})
                }
                formatted_data.append(formatted_house)
            except Exception as e:
                print(f"Error formatting house: {str(e)}")
                continue

        return {
            'houses': formatted_data,
            'total_results': len(formatted_data),
            'type': 'house_search'
        }