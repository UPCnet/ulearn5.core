# -*- coding: utf-8 -*-
import logging

import requests
from plone import api
from plone.restapi.services import Service
from ulearn5.core.services import UnknownEndpoint, check_methods

logger = logging.getLogger(__name__)


class AppConfig(Service):
    """
    - Endpoint: @api/appconfig
    - Method: GET
        Optional params:
            - username: (str) Used to obtain the profile language.
        Returns a dict containing some configuration values.

    - Subpaths allowed: NO
    """

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request
        self.username = kwargs.get('username', None)

    def handle_subpath(self, subpath):
        """ Function used to spread the request to the corresponding subpath """
        if subpath:
            return UnknownEndpoint(f'Unknown sub-endpoint: {"/".join(subpath)}')

        return self.reply()

    @check_methods(methods=['GET'])
    def reply(self):
        registry_records = self.get_registry_records()

        language = self.check_lang_for_username(self.username)

        max_oauth_server = self.check_oauth_max_server(registry_records['oauth_server'])

        info = {
            **registry_records,
            'max_oauth_server': max_oauth_server,
            'language': language
        }

        # If there's a username, log their access
        if self.username:
            logger.error(
                f"XXX mobile access username {self.username} in domain {registry_records['domain']}")

        return {"data": info, "code": 200}

    def get_registry_records(self):
        """ Obtain the registry records for the appconfig service """
        main_color = api.portal.get_registry_record(
            name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.main_color')
        secondary_color = api.portal.get_registry_record(
            name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.secondary_color')
        max_server = api.portal.get_registry_record(
            name='mrs5.max.browser.controlpanel.IMAXUISettings.max_server')
        max_server_alias = api.portal.get_registry_record(
            name='mrs5.max.browser.controlpanel.IMAXUISettings.max_server_alias')
        hub_server = api.portal.get_registry_record(
            name='mrs5.max.browser.controlpanel.IMAXUISettings.hub_server')
        domain = api.portal.get_registry_record(
            name='mrs5.max.browser.controlpanel.IMAXUISettings.domain')
        oauth_server = max_server + '/info'
        buttonbar_selected = api.portal.get_registry_record(
            name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.buttonbar_selected')
        show_news_in_app = api.portal.get_registry_record(
            name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.show_news_in_app')

        return {
            'main_color': main_color,
            'secondary_color': secondary_color,
            'max_server': max_server,
            'max_server_alias': max_server_alias,
            'hub_server': hub_server,
            'domain': domain,
            'oauth_server': oauth_server,
            'buttonbar_selected': buttonbar_selected,
            'show_news_in_app': show_news_in_app
        }

    def check_lang_for_username(self, username):
        """ Use the language of the user if it exists, otherwise use the default language """
        if username:
            user = api.user.get(username=username)
            if hasattr(user, 'language') and user.getProperty('language'):
                return user.getProperty('language')

        return api.portal.get_default_language()

    def check_oauth_max_server(self, oauth_server):
        """ Check the connection to the OAuth server """
        session = requests.Session()
        resp = session.get(oauth_server)
        try:
            max_oauth_server = resp.json().get('max.oauth_server',
                                               'ERROR: UNABLE TO CONNECT TO MAX OAUTH SERVER')
        except Exception:
            max_oauth_server = 'ERROR: UNABLE TO CONNECT TO MAX OAUTH SERVER'

        return max_oauth_server
