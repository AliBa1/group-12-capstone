from .base import SearchStrategy
from django.conf import settings
import requests
import json
import openai
from ..models import Property, ListingAgent, ListingOffice
from django.core.cache import cache


class ApartmentSearchStrategy(SearchStrategy):
    KEYWORDS = ['apartments', 'rental', 'rentals', 'apartment']

    def __init__(self):
        self.api_key = settings.RENTCAST_API_KEY
        self.base_url = "https://api.rentcast.io/v1/listings/rental/long-term"

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

        response = apartments_data = self._search_apartments(location_info['city'], location_info['state'])
        print(apartments_data.text)
        print('test')

        if not response:
            return None
            
        apartments_data = response.json()
        
        if not apartments_data:
            return None

        self._store_apartments(apartments_data)
        formatted_data = self._format_apartment_response(apartments_data)

        print("Before accessing 'apartments'")
        print(formatted_data)  
        print(formatted_data.get('apartments'))
        print("After accessing 'apartments'")
        response_text = f"I found {len(apartments_data)} apartments in the {location_info['city']}, {location_info['state']} area"
        print(f"Found {len(apartments_data)} apartments in the {location_info['city']}, {location_info['state']} area")
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

    def _search_apartments(self, city, state, limit=5, propertyType = "Apartment"):
        cache_key = self.get_cache_key('apartments', city)
        cached_data = cache.get(cache_key)

        if cached_data:
            return cached_data
        try:
            url = f"{self.base_url}?city={city}&state={state}&status=Active&limit={limit}&propertyType={propertyType}"
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
            print(f"Error in search_apartments: {e}")
            return None
        
    def _store_apartments(self, apartments_data):
        for apartment in apartments_data:
            try:
                agent_data = apartment.get('listingAgent', {})
                agent, _ = ListingAgent.objects.update_or_create(
                    name=agent_data.get('name', ''),
                    defaults={
                        'phone': agent_data.get('phone', ''),
                        'email': agent_data.get('email', ''),
                        'website': agent_data.get('website', '')
                    }
                )

                office_data = apartment.get('listingOffice', {})
                office, _ = ListingOffice.objects.update_or_create(
                    name=office_data.get('name', ''),
                    defaults={
                        'phone': office_data.get('phone', ''),
                        'email': office_data.get('email', ''),
                        'website': office_data.get('website', '')
                    }
                )

                Property.objects.update_or_create(
                    formatted_address=apartment['formattedAddress'],
                    defaults={
                        'property_type': apartment.get('propertyType', ''),
                        'latitude': apartment.get('latitude', 0),
                        'longitude': apartment.get('longitude', 0),
                        'bedrooms': apartment.get('bedrooms', 0),
                        'bathrooms': apartment.get('bathrooms', 0),
                        'square_footage': apartment.get('squareFootage', 0),
                        'lot_size': apartment.get('lotSize', 0),
                        'year_built': apartment.get('yearBuilt', 0),
                        'price': apartment.get('price', 0),
                        'listing_type': apartment.get('listingType', ''),
                        'days_on_market': apartment.get('daysOnMarket', 0),
                        'mls_name': apartment.get('mlsName', ''),
                        'mls_number': apartment.get('mlsNumber', ''),
                        'listing_agent': agent,
                        'listing_office': office
                    }
                )

            except Exception as e:
                print(f"Error storing apartment: {str(e)}")
                continue

    def _format_apartment_response(self, apartments_data):
        formatted_data = []
        for apartment in apartments_data:
            try:
                formatted_apartment = {
                    'formattedAddress': apartment.get('formattedAddress', ''),
                    'propertyType': apartment.get('propertyType', ''),
                    'latitude': apartment.get('latitude', 0),
                    'longitude': apartment.get('longitude', 0),
                    'bedrooms': apartment.get('bedrooms', 0),
                    'bathrooms': apartment.get('bathrooms', 0),
                    'squareFootage': apartment.get('squareFootage', 0),
                    'lotSize': apartment.get('lotSize', 0),
                    'yearBuilt': apartment.get('yearBuilt', 0),
                    'price': apartment.get('price', 0),
                    'listingType': apartment.get('listingType', ''),
                    'daysOnMarket': apartment.get('daysOnMarket', 0),
                    'mlsName': apartment.get('mlsName', ''),
                    'mlsNumber': apartment.get('mlsNumber', ''),
                    'listingAgent': apartment.get('listingAgent', {}),
                    'listingOffice': apartment.get('listingOffice', {})
                }
                formatted_data.append(formatted_apartment)
            except Exception as e:
                print(f"Error formatting apartment: {str(e)}")
                continue

        return {
            'apartments': formatted_data,
            'total_results': len(formatted_data),
            'type': 'apartment_search'
        }