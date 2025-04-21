import requests
from urllib.parse import urlencode
from django.conf import settings

class AerialViewClient:
    BASE_URL = "https://aerialview.googleapis.com/v1/videos"
    API_KEY = settings.GOOGLE_PLACES_API_KEY

    def lookup_metadata(self, address: str = None, video_id: str = None):
        """
        Returns metadata dict on 200, or None on 404.
        Raises on other errors.
        """
        params = {"key": self.API_KEY}
        if address:
            params["address"] = address
        elif video_id:
            params["videoId"] = video_id
        else:
            raise ValueError("Must supply address or video_id")

        url = f"{self.BASE_URL}:lookupVideoMetadata?{urlencode(params)}"
        resp = requests.get(url)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def lookup_video(self, address: str = None, video_id: str = None):
        """
        Returns dict containing 'uris' + 'state' + 'metadata'; or None on 404.
        Raises on other errors.
        """
        params = {"key": self.API_KEY}
        if address:
            params["address"] = address
        elif video_id:
            params["videoId"] = video_id
        else:
            raise ValueError("Must supply address or video_id")

        url = f"{self.BASE_URL}:lookupVideo?{urlencode(params)}"
        resp = requests.get(url)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def render_video(self, address: str):
        """
        Kicks off a render request if no video exists yet.
        Returns metadata including a videoId in 'metadata'.
        """
        params = {"key": self.API_KEY}
        body = {"address": address}
        url = f"{self.BASE_URL}:renderVideo?{urlencode(params)}"
        resp = requests.post(url, json=body)
        resp.raise_for_status()
        return resp.json()
