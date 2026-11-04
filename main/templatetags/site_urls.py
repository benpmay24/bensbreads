"""Reverse URLs on either site, whichever site is rendering the template.

    {% load site_urls %}
    <a href="{% main_url 'recipes' %}">Recipes</a>
    <a href="{% playground_url 'blog' %}">Blog</a>

Links to the site currently being served stay relative; links to the other site
are made absolute using MAIN_SITE_URL / PLAYGROUND_SITE_URL.
"""
from django import template
from django.conf import settings
from django.urls import reverse

register = template.Library()

_SITES = {
    'main': ('bensbreads.urls', 'MAIN_SITE_URL'),
    'playground': ('bensbreads.urls_playground', 'PLAYGROUND_SITE_URL'),
}


def _site_url(site, view_name, *args, **kwargs):
    urlconf, base_setting = _SITES[site]
    path = reverse(view_name, urlconf=urlconf, args=args, kwargs=kwargs)
    if settings.SITE_ROLE == site:
        return path
    return getattr(settings, base_setting) + path


@register.simple_tag
def main_url(view_name, *args, **kwargs):
    return _site_url('main', view_name, *args, **kwargs)


@register.simple_tag
def playground_url(view_name, *args, **kwargs):
    return _site_url('playground', view_name, *args, **kwargs)
