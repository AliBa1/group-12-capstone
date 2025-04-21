from django.conf import settings
from .base import SearchStrategy
from ..models import Place
import openai
import time
from google.maps import places_v1
from django.core.cache import cache
import traceback

class OtherSearchStrategy(SearchStrategy):
    # always runs as fallback so keywords don't matter vvvv
    KEYWORDS = ['attractions', 'food']

    def __init__(self):
        self.places = places_v1.PlacesClient(
            client_options = {"api_key": settings.GOOGLE_PLACES_API_KEY}
        )

    @staticmethod
    def get_cache_key(prefix, identifier):
        safe_identifier = str(identifier).replace(' ', '_').lower()
        return f'other_search_{prefix}_{safe_identifier}'

    def should_handle(self, prompt):
        return any(keyword in prompt.lower() for keyword in self.KEYWORDS)

    def process_query(self, prompt, city=None, reason=None, user=None):
        try:
            if not prompt:
                return None
            query = self._create_query(prompt, city)
            other_data = self._search_others(query)
            if not other_data:
                return None
            
            formatted_data = self._format_other_response(other_data)
            response_text = f"I found {formatted_data.get('total_results')} results related to your search in {city}"

            return {
                'text': response_text,
                'data': formatted_data
            }
        except Exception as e:
            print(f"Error in process_query: {str(e)}")
            return None

    def _create_query(self, prompt, city):
      try:
          response = openai.chat.completions.create(
              model="gpt-4o-mini",
              messages=[
                  {"role": "system", "content": "You're a helpful assistant that generates Google Places text search queries. If a location is included in the prompt, use it. Otherwise, use the fallback location."},
                  {"role": "user", "content": f"Prompt: '{prompt}'\nFallback city: '{city}'"}
              ]

          )
          content = response.choices[0].message.content
          return content
      except Exception as e:
          print(f"Error in create_query: {e}")
          return None


    def _search_others(self, prompt):
        cache_key = self.get_cache_key('others', prompt)
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data

        try:
            request = places_v1.SearchTextRequest(
                text_query=prompt,
            )
            field_mask = "places.displayName,places.name,places.primaryType,places.formattedAddress,places.location,places.photos,places.rating,places.priceRange,places.priceLevel"
            metadata = (("x-goog-fieldmask", field_mask),)

            response = self.places.search_text(request=request, metadata=metadata)
            result = self._parse_data(response.places)
            
            cache.set(cache_key, result, timeout=86400)  # 24 hrs 
            time.sleep(0.2)
            return result
        except Exception as e:
            print(f"Error in _search_others: {e}")
            traceback.print_exc()
            return []
        
    def _parse_data(self, places):
      data = []

      for place in places:
        item = {}
        item['google_place_id'] = place.name
        item['google_address'] = place.formatted_address
        item['location'] = {
            'latitude': place.location.latitude,
            'longitude': place.location.longitude
        }
        item['primary_type'] = place.primary_type
        item['name'] = place.display_name.text if place.display_name else None
        item['rating'] = getattr(place, 'rating', None)

        if place.photos:
            item['photo_references'] = [photo.name for photo in place.photos]
        else:
            item['photo_references'] = []
        data.append(item)
      return data


    def _store_others(self, others_data): 
        for other in others_data:
          photo_references = other.get('photo_references', [])
          if not photo_references:
              photo_references = [None, None, None]

          display_name = other.get('display_name', {})
          name_text = display_name.get('text', other.get('name'))

          location = other.get('location', {})
          latitude = location.get('latitude')
          longitude = location.get('longitude')
          try:
              Place.objects.update_or_create(
                  place_id=other.get('google_place_id'),
                  defaults={
                      'name': name_text,
                      'type': other.get('primary_type', ''),
                      'photo_references': [ref for ref in photo_references if ref],
                      'formatted_address': other.get('google_address'),
                      'latitude': latitude,
                      'longitude': longitude,
                      'google_place_id': other.get('google_place_id'),
                      'google_address': other.get('google_address'),
                      'google_rating': other.get('rating'),
                  }
              )
          except Exception as e:
              print(f"Error creating other place record: {str(e)}")
              continue

    def _format_other_response(self, others_data):
      formatted_others = []

      for other in others_data:
          photo_references = other.get('photo_references', [])
          if not photo_references:
              photo_references = [None, None, None]


          display_name = other.get('display_name', {})
          name_text = display_name.get('text', other.get('name'))

          location = other.get('location', {})
          latitude = location.get('latitude')
          longitude = location.get('longitude')

          formatted_other = {
              'name': name_text,
              'type': other.get('primary_type', ''),
              'images': [ref for ref in photo_references if ref],
              'details': {
                  # 'name': name_text,
                  'latitude': latitude,
                  'longitude': longitude,
                  'google_place_id': other.get('google_place_id', ''),
                  'google_address': other.get('google_address'),
                  'google_rating': other.get('rating')
              }
          }

          formatted_others.append(formatted_other)

      return {
          'places': formatted_others,
          'total_results': len(formatted_others),
          'type': 'other_search'
      }