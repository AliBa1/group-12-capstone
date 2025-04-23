from amadeus import Client
from django.conf import settings
import openai
import json
from .base import SearchStrategy
from ..models import Hotel
import time
from google.maps import places_v1
from django.core.cache import cache
import traceback
import requests

class HotelSearchStrategy(SearchStrategy):
    # dont need 'hotels' and 'hotel' for example since it will catch both if only 'hotel'
    KEYWORDS = ['hotel', 'place to stay', 'accommodation', 'resort', 'motel', 'stay overnight', 'a room', 'bnb']

    def __init__(self):
        #self.amadeus = Client(
        #    client_id=settings.AMADEUS_API_KEY,
        #    client_secret=settings.AMADEUS_API_SECRET
        #)
        self.places = places_v1.PlacesClient(
            client_options = {"api_key": settings.GOOGLE_PLACES_API_KEY}
        )

    @staticmethod
    def get_cache_key(prefix, identifier):
        safe_identifier = str(identifier).replace(' ', '_').lower()
        return f'hotel_search_{prefix}_{safe_identifier}'
    
    def get_access_token(self):
        token_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": settings.AMADEUS_API_KEY,
            "client_secret": settings.AMADEUS_API_SECRET
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = requests.post(token_url, data=payload, headers=headers)
        response.raise_for_status()
        token_data = response.json()
        return token_data["access_token"], token_data.get("expires_in", 0)

    def should_handle(self, prompt):
        return any(keyword in prompt.lower() for keyword in self.KEYWORDS)

    def process_query(self, prompt, city=None, reason=None, user=None):
        try:
            access_token, expires_in = self.get_access_token()
            print(f"Access token expires in {expires_in / 60} minutes.")
            prompt_location_info = self._query_location_info(prompt)
            
            if prompt_location_info and 'city' in prompt_location_info:
                location_info = prompt_location_info
    
            elif city:
                location_info = self._get_city_code(city)
           
            else:
                location_info = None
                      
            if not location_info or 'city' not in location_info:
                return None

            hotels_data = self._search_hotels(location_info['city'], access_token)
            if not hotels_data:
                return None
            
            hotels_list = hotels_data.get("data", [])

            enhanced_hotels = self.hotel_details(hotels_list)
            
            self._store_hotels(enhanced_hotels)
            formatted_data = self._format_hotel_response(enhanced_hotels)

            response_text = f"I found {len(enhanced_hotels)} hotels in the {location_info['city']} area"

            return {
                'text': response_text,
                'data': formatted_data
            }
        except Exception as e:
            print(f"Error in process_query: {str(e)}")
            return None
        
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
        if not hotel.get('hotelId'):
            return hotel

        cache_key = self.get_cache_key('place_details', hotel['hotelId'])
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data

        try:
            # Just to initialize request arguments
            request = places_v1.SearchTextRequest(
                text_query=hotel['name'],
            )
            field_mask = "places.displayName,places.name,places.formattedAddress,places.location,places.photos,places.rating,places.priceRange,places.priceLevel"
            metadata = (("x-goog-fieldmask", field_mask),)
            places_result = self.places.search_text(request=request, metadata=metadata)
            # print(f"Places Result: {places_result}")

            if not places_result.places:
                return hotel
            place = places_result.places[0]
            hotel['google_place_id'] = place.name
            hotel['google_address'] = place.formatted_address
            hotel['name'] = place.display_name.text if place.display_name else None
            hotel['location'] = place.location
            if place.photos:
                photo_references = [photo.name for photo in place.photos[:5]]
                hotel['photo_references'] = photo_references
            else:
                hotel['photo_references'] = []


            # details_result = self.gmaps.place(
            #     place_id=hotel['google_place_id'],
            #     fields=['photo', 'rating']
            # )

            # if 'result' in details_result:
            #     if 'photos' in details_result['result']:
            #         photos = details_result['result']['photos'][:3]
            #         photo_references = [photo['photo_reference'] for photo in photos]
            #         hotel['photo_references'] = photo_references

            #     if 'rating' in details_result['result']:
            #         hotel['google_rating'] = details_result['result']['rating']
            
            # else: 
            #     print("No photo found")

            cache.set(cache_key, hotel, timeout=86400)  # 24 hrs
            
            time.sleep(0.2)
            return hotel

        except Exception as e:
            print(f"Error getting place details for {hotel.get('name')}: {e}")
            return hotel


        
    def hotel_details(self, hotels_data):
        enhanced_hotels = []
        for hotel in hotels_data[:5]:
            enhanced_hotel = self._get_place_details(hotel)
            enhanced_hotels.append(enhanced_hotel)
        return enhanced_hotels

    def _search_hotels(self, city_code, access_token, limit=5):
        # cache_key = self.get_cache_key('hotels', city_code)
        # cached_data = cache.get(cache_key)
        
        # if cached_data:
        #     return cached_data

        try:
            endpoint = "https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-city"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            params = {
                "cityCode": city_code
            }
            hotel_response = requests.get(endpoint, headers=headers, params=params)
            hotel_response.raise_for_status()
            result = hotel_response.json()
            #print("Hotel response type: ", type(result))
            #print("Hotel response content: ", result)

            
            #cache.set(cache_key, result, timeout=86400)
            
            return result
        except Exception as e:
            print(f"Error in _search_hotels: {e}")
            traceback.print_exc()
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
                        'google_place_id': hotel_data.get('google_place_id'),
                        'google_address': hotel_data.get('google_address'),
                        'google_rating': hotel_data.get('google_rating'),
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
                'description': hotel.get('google_address', f"Located in {hotel['iataCode']}"),
                'location': f"{hotel['iataCode']}",
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
                    'google_address': hotel.get('google_address'),
                    'google_rating': hotel.get('google_rating')
                }
            }
            formatted_hotels.append(formatted_hotel)

        return {
            'hotels': formatted_hotels,
            'total_results': len(formatted_hotels),
            'type': 'hotel_search'
        }