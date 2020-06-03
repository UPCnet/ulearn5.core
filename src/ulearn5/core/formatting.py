# -*- coding: utf-8 -*-
import json
import re
import requests
import urllib2
from plone import api
from ulearn5.core.controlpanel import IUlearnControlPanelSettings

FIND_URL_REGEX = r'https?\:\/\/[^\"\']+'

def formatMessageEntities(text):
    """
        function that shearches for elements in the text that have to be formatted.
        Currently shortens urls.
    """

    def shorten(matchobj):
        url = matchobj.group(0)        
        bitly_username = api.portal.get_registry_record(name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.bitly_username')
        bitly_api_key = api.portal.get_registry_record(name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.bitly_api_key')

        return shortenURL(url, bitly_username, bitly_api_key, secure=False)

    shortened = re.sub(FIND_URL_REGEX, shorten, text, flags=re.IGNORECASE)

    return shortened


def shortenURL(url, bitly_username, bitly_api_key, secure=False):
    """
        Shortens a url using bitly API. Keeps the original url in case
        something goes wrong with the api call
    """
    # FOR DEBUGGING !! if localhost present in the domain part of the url,
    # substitute with a fake domain
    # to allow bitly shortening in development environments
    # (localhost/ port not allowed in URI by bitly api)
    
    shortened_url = re.sub(r'(.*://)(localhost:[0-9]{4,5})(.*)', r'\1foo.bar\3', url)

    params = {'api_url': 'http://api.bitly.com',
              'login': 'apiKey=%s&login=%s' % (bitly_api_key, bitly_username),
              'version': 'v3',
              'endpoint': 'shorten',
              'endpoint_params': 'longUrl=%s' % (urllib2.quote(url))
              }

    queryurl = '%(api_url)s/%(version)s/%(endpoint)s?%(login)s&%(endpoint_params)s' % params

    req = requests.get(queryurl)

    try:
        response = json.loads(req.content)
        if response.get('status_code', None) == 200:
            shortened_url = response.get('data', {}).get('url', queryurl)
            if secure:
                shortened_url = shortened_url.replace('http://', 'https://')
    except:
        shortened_url = url

    return shortened_url
