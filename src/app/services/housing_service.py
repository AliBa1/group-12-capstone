from .base import SearchStrategy
from django.conf import settings
import requests
import json
import openai
from ..models import Property

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

        houses_data = self._search_houses(location_info['city'], location_info['state'])
        print(houses_data.text)
        print('test')

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
                    "content": f"Extract the city and state from this query, and if the city name or state name is misspelled, correct it and use the proper city name or state name: '{query}'. "
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
        # ex city: Detroit, MI   
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
            #print(response)
            return response
        except Exception as e:
            print(f"Error in search_houses: {e}")
            return None
        
    def _store_houses(self, houses_data):
        print("In _store_houses")
        for house in houses_data:
            try:
                Property.objects.update_or_create(
                    formatted_address=house['formattedAddress'],
                    defaults={
                        "propertyType": house['propertyType'],
                        "bedrooms": house['bedrooms'],
                        "bathrooms": house['bathrooms'],
                        "squareFootage": house['squareFootage'],
                        "lotSize": house['lotSize'],
                        "yearBuilt": house['yearBuilt'],
                        "price": house['price'],
                        "listingType": house['listingType'],
                        "daysOnMarket": house['daysOnMarket'],
                        "mlsName": house['mlsName'],
                        "mlsNumber": house['mlsNumber'],
                        "listingAgent": house['listingAgent'],
                        "listingOffice": house['listingOffice']
                    }
                )
                print("Stored house")
            except Exception as e:
                print(f"Error in store_houses: {e}")
                continue
        """
            exaplme response (json):
        [
        {
            "id": "3821-Hargis-St,-Austin,-TX-78723",
            "formattedAddress": "3821 Hargis St, Austin, TX 78723",
            "addressLine1": "3821 Hargis St",
            "addressLine2": null,
            "city": "Austin",
            "state": "TX",
            "zipCode": "78723",
            "county": "Travis",
            "latitude": 30.290643,
            "longitude": -97.701547,
            "propertyType": "Single Family",
            "bedrooms": 4,
            "bathrooms": 2.5,
            "squareFootage": 2345,
            "lotSize": 3284,
            "yearBuilt": 2008,
            "hoa": {
            "fee": 65
            },
            "status": "Active",
            "price": 899000,
            "listingType": "Standard",
            "listedDate": "2024-06-24T00:00:00.000Z",
            "removedDate": ,
            "createdDate": "2021-06-25T00:00:00.000Z",
            "lastSeenDate": "2024-09-30T13:11:47.157Z",
            "daysOnMarket": 99,
            "mlsName": "UnlockMLS",
            "mlsNumber": "5519228",
            "listingAgent": {
            "name": "Jennifer Welch",
            "phone": "5124313110",
            "email": "jennifer@gottesmanresidential.com",
            "website": "https://www.gottesmanresidential.com"
            },
            "listingOffice": {
            "name": "Gottesman Residential R.E.",
            "phone": "5124512422",
            "email": "nataliem@gottesmanresidential.com",
            "website": "https://www.gottesmanresidential.com"
            },
            "history": {
            "2024-06-24": {
                "event": "Sale Listing",
                "price": 899000,
                "listingType": "Standard",
                "listedDate": "2024-06-24T00:00:00.000Z",
                "removedDate": null,
                "daysOnMarket": 99
            }
            }
        },
        {
            "id": "6808-Windrift-Way,-Austin,-TX-78745",
            ...
        """
    def _format_house_response(self, houses_data):
        print("In _format_house_response")
        formatted_data = []
        for house in houses_data:
            formatted_house = {
                'formattedAddress': house['formattedAddress'],
                'propertyType': house['propertyType'],
                'bedrooms': house['bedrooms'],
                'bathrooms': house['bathrooms'],
                'squareFootage': house['squareFootage'],
                'lotSize': house['lotSize'],
                'yearBuilt': house['yearBuilt'],
                'price': house['price'],
                'listingType': house['listingType'],
                'daysOnMarket': house['daysOnMarket'],
                'mlsName': house['mlsName'],
                'mlsNumber': house['mlsNumber'],
                'listingAgent': house['listingAgent'],
                'listingOffice': house['listingOffice']
            }
            formatted_data.append(formatted_house)
        print("formatted_data")
        return {
            'houses':formatted_data,
            'total_results': len(formatted_data),
            'type': 'house_search'
        }
