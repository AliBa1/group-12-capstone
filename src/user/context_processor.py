from django.conf import settings

def google_settings(request):
    return {
        'GOOGLE_CLIENT_ID': settings.GOOGLE_CLIENT_ID
    }