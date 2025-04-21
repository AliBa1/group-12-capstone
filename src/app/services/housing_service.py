from .base import SearchStrategy
from django.conf import settings
from .aerial_view import AerialViewClient
import requests
import json
import pandas as pd
import os 
import openai
from ..models import Property, ListingAgent, ListingOffice, Preferences
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
    KEYWORDS = ['houses', 'housing', 'house', 'home', 'homes', 'apartment', 'apartments', 'townhouse', 'townhomes', 'condo', 'condos', 'property', 'properties']

    def __init__(self):
        self.api_key = settings.RENTCAST_API_KEY
        self.base_url = "https://api.rentcast.io/v1/listings"
        self.places_key = settings.GOOGLE_PLACES_API_KEY

    def should_handle(self, prompt):
        return any(keyword in prompt.lower() for keyword in self.KEYWORDS)
    
    # @staticmethod
    # def get_cache_key(prefix, identifier):
    #     safe_identifier = str(identifier).replace(' ', '_').lower()
    #     return f'property_search_{prefix}_{safe_identifier}'

    @staticmethod
    def get_cache_key(prefix, city, property_type):
        safe_city = str(city).replace(' ', '_').lower()
        safe_property_type = str(property_type).replace(' ', '_').lower()
        
        return f'property_search_{prefix}_{safe_city}_{safe_property_type}'

    def process_query(self, prompt, city=None, state=None, reason=None, user=None):
        prompt_location_info = self._query_location_info(prompt)
        aerial = AerialViewClient()
        property_type = Preferences.objects.filter(user=user).first().house_property_type or None

        if prompt_location_info and 'city' in prompt_location_info and 'state' in prompt_location_info and 'property_type' in prompt_location_info:
            location_info = prompt_location_info
            original_city = prompt
            property_type = prompt_location_info['property_type']
        elif city and state:
            location_info = {'city': city, 'state': state}
            original_city = city
        else:
            location_info = None
            original_city = None

        if not location_info or 'city' not in location_info or 'state' not in location_info:
            return None

        
        response = self._search_houses(location_info['city'], location_info['state'], property_type)
        if not response:
            return None
        houses_data = response.json()
        if not houses_data:
            return None
            
        heat_index = self._house_rating(location_info['city'], location_info['state'])

        extra_data = []
        for house in houses_data:
            house['heatIndex'] = heat_index 
            address = house['formattedAddress']

            photos = []
            photos.append(self._get_satellite_url(house['latitude'], house['longitude']))
            photos.append(self._get_street_view_url(house['latitude'], house['longitude']))
            try:
                meta = aerial.lookup_metadata(address=address)
            except requests.HTTPError as e:
                if e.response.status_code == 404:
                    aerial.render_video(address=address)
                else:
                    print(f"Aerial metadata error for {address}: {e}")
                meta = None
            if meta and meta.get("state") == "ACTIVE":
                try:
                    uris = aerial.lookup_video(address=address)
                    img_uri = uris["uris"]["IMAGE"]["landscapeUri"]
                    photos = [img_uri]
                except Exception as e:
                    print(f"Aerial lookup_video error for {address}: {e}")
            house['photos'] = photos
            extra_data.append(house)

        
        self._store_houses(extra_data)
        formatted_data = self._format_house_response(extra_data)

        response_text = f"I found {len(formatted_data['houses'])} properties in the {location_info['city']}, {location_info['state']} area"
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
                    "content": f"Extract the city, state, and property type from this query, and if the city name, state name is misspelled, correct it and use the proper city name or state name: '{query}'. "
                              f"Potential values for property type: Single%20Family, Townhouse, Multi-Family, Apartment, or default to None if none specified"
                              f"Return ONLY a JSON object in this EXACT format: {{\"city\": \"Austin\", \"state\": \"TX\", \"property_type\": \"Single%20Family\"}} "
                              f"(replace Austin and TX with the appropriate city and state)"
                }]
            )
            content = response.choices[0].message.content
            #print(content)
            return json.loads(content.strip())
        except Exception as e:
            print(f"Error in query_location_info: {e}")
            return None

    def _search_houses(self, city, state, property_type, limit=5):
        # cache_key = self.get_cache_key('properties', city)
        cache_key = self.get_cache_key('properties', city, property_type)
        cached_data = cache.get(cache_key)

        #if cached_data:
            #return cached_data
        try:
            if property_type is None or property_type == 'None':
                url = f"{self.base_url}/sale?city={city}&state={state}&status=Active&limit={limit}"
            elif property_type.lower() == 'apartment':
                url = f"{self.base_url}/rental/long-term?city={city}&state={state}&propertyType={property_type}&status=Active&limit={limit}"
            else:
                url = f"{self.base_url}/sale?city={city}&state={state}&propertyType={property_type}&status=Active&limit={limit}"
            headers = {
                "accept": "application/json",
                "X-API-KEY": self.api_key
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            cache.set(cache_key, response, timeout=86400)

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
                        'listing_office': office,           
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
                    'listingOffice': house.get('listingOffice', {}),
                    'heatIndex': house.get('heatIndex', 0),
                    'photos': house.get('photos', []),
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
    
    def _house_rating(self, city, state):
        try:
            from app.views import load_model_and_data
            location = f"{city}, {state}"
            dataset = pd.read_csv(os.path.join(settings.ML_MODELS_DIR, "processed_metro_heat_index.csv"))
            location_data = dataset[dataset["RegionName"] == location]

            location_last_heat_index = location_data.iloc[:, -1].values[0]

            location_last_heat_index = float(location_last_heat_index)

            model, data, label_encoder = load_model_and_data()
            state_encoded = label_encoder.transform([state])[0]
            location_data = data[(data["RegionName"] == location) & (data["StateName"] == state_encoded)]
            features = location_data[["RegionID", "SizeRank", "StateName"]]
            prediction = model.predict(features)[0]
            prediction = float(prediction)

            confidance_score = prediction - location_last_heat_index
        
            if(prediction > location_last_heat_index):
                rating = "Good"
                confidance = "Low"
            if(confidance_score > 15):
                confidance = "High"
            
            elif(prediction < location_last_heat_index):
                rating = "Bad"
                confidance = "Low"
            if(confidance_score > 15):
                confidance = "High"
            return rating, confidance
        except Exception as e:
            print(f"Error in _house_rating: {e}")
    
    def _get_place_photos(self, address, max_photos=5, max_width_px=800):
        try:
            search_url = "https://places.googleapis.com/v1/places:searchText"
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.places_key,
                "X-Goog-FieldMask": "places.name,places.photos"
            }
            body = {"textQuery": address}
            response = requests.post(search_url, headers=headers, json=body)
            response.raise_for_status()
            places = response.json().get("places", [])
            if not places:
                print(f"No photos found for {address}")
                return []
            
            photos = places[0].get('photos', [])
            urls = []
            for photo in photos[:max_photos]:
                name = photo.get('name')
                if not name:
                    continue
                urls.append(
                    f"https://places.googleapis.com/v1/{name}/media"
                    f"?key={self.places_key}"
                    f"&maxWidthPx={max_width_px}"
                )
            return urls
        except Exception as e:
            print(f"Error in _get_place_photos: {e}")
            return []

    def _get_street_view_url(self, lat, lng, size="600x400"):
        return (
            f"https://maps.googleapis.com/maps/api/streetview"
            f"?size={size}&location={lat},{lng}&key={self.places_key}"
        )
    
    def _get_satellite_url(self, lat, lng, size="600x400", zoom=18):
        return (
            f"https://maps.googleapis.com/maps/api/staticmap"
            f"?center={lat},{lng}"
            f"&zoom={zoom}"
            f"&size={size}"
            f"&maptype=satellite"
            f"&key={self.places_key}"
        )
