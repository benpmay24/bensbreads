from django.conf import settings


def sites(request):
    return {
        'SITE_ROLE': settings.SITE_ROLE,
        'MAIN_SITE_URL': settings.MAIN_SITE_URL,
        'PLAYGROUND_SITE_URL': settings.PLAYGROUND_SITE_URL,
    }
