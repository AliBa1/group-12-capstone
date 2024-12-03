from .base import SearchStrategy
from django.conf import settings
import requests
import json
import openai

"""
example request:
url = "https://api.rentcast.io/v1/listings/sale?city=austin&state=tx&status=Active&limit=5"
        https://api.rentcast.io/v1/listings/sale?city=Detroit,MI&status=Active&limit=5
headers = {
    "accept": "application/json",
    "X-Api-Key": "8f2586c8082e4bb285f4f190aaf6f724"
}

response = requests.get(url, headers=headers)
exaplme response:
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
    "removedDate": null,
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


class HousingSearchStrategy(SearchStrategy):
    KEYWORDS = ['houses', 'housing', 'house']

    def __init__(self):
        self.api_key = settings.RENTCAST_API_KEY
        self.base_url = "https://api.rentcast.io/v1/listings/sale"

    def should_handle(self, prompt):
        return any(keyword in prompt.lower() for keyword in self.KEYWORDS)

    def process_query(self, prompt, city=None, reason=None):
        prompt_location_info = self._query_location_info(prompt)

        if prompt_location_info and 'city' in prompt_location_info:
            location_info = prompt_location_info
            original_city = prompt
        elif city:
            location_info = {'city': city}
            original_city = city
        else:
            location_info = None
            original_city = None

        if not location_info or 'city' not in location_info:
            return None

        houses_data = self._search_houses(location_info['city'])
        if not houses_data:
            return None

        formatted_data = self._format_house_response(houses_data)

        response_text = f"I found {len(houses_data)} houses in the {location_info['city']}, {location_info['state']} area"

        return {
            'text': response_text,
            'data': formatted_data
        }

    def _query_location_info(self, query):
        try:
            response = openai.chat.completions.create(
                model="gpt-4.0",
                messages=[{
                    "role": "user",
                    "content": f"Extract the city and state from this query, and if the city name is misspelled, correct it and use the proper city name: '{query}'. "
                              f"Return ONLY a JSON object in this EXACT format: {{\"city\": \"Austin\", \"state\": \"TX\"}} "
                              f"(replace Austin and TX with the appropriate city and state)"
                }]
            )
            content = response.choices[0].message.content
            return json.loads(content.strip())
        except Exception as e:
            print(f"Error in query_location_info: {e}")
            return None

    def _search_houses(self, city, limit=5):
        # ex city: Detroit, MI
        state = city.split(",")[-1].strip() 
        try:
            url = f"{self.base_url}?city={city}&state={state}&status=Active&limit={limit}"
            headers = {
                "accept": "application/json",
                "X-API-KEY": self.api_key
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response
        except Exception as e:
            print(f"Error in search_houses: {e}")
            return []

    def _format_house_response(self, houses_data):
        formatted_data = []
        for house in houses_data:
            formatted_data.append({
                'id': house['id'],
                'formattedAddress': house['formattedAddress'],
                'propertyType': house['propertyType'],
                'bedrooms': house['bedrooms'],
                'bathrooms': house['bathrooms'],
                'squareFootage': house['squareFootage'],
                'price': house['price'],
                'listedDate': house['listedDate'],
                'daysOnMarket': house['daysOnMarket'],
                'listingAgent': house['listingAgent'],
                'listingOffice': house['listingOffice']
            })
        return formatted_data