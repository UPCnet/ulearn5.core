# -*- coding: utf-8 -*-
from five import grok
from Products.CMFPlone.interfaces import IPloneSiteRoot
from plone import api
from ulearn5.core.api import ApiResponse
from ulearn5.core.api import REST
from ulearn5.core.api import api_resource
from ulearn5.core.api.root import APIRoot
import requests


class Appconfig(REST):
    """
        /api/appconfig --> Idioma por defecto del site
        /api/appconfig?username=nom.cognom --> Idioma del perfil del usuario

    """
    grok.adapts(APIRoot, IPloneSiteRoot)
    grok.require('base.authenticated')

    @api_resource()
    def GET(self):
        main_color = api.portal.get_registry_record(name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.main_color')
        secondary_color = api.portal.get_registry_record(name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.secondary_color')
        max_server = api.portal.get_registry_record(name='mrs5.max.browser.controlpanel.IMAXUISettings.max_server')
        max_server_alias = api.portal.get_registry_record(name='mrs5.max.browser.controlpanel.IMAXUISettings.max_server_alias')
        hub_server = api.portal.get_registry_record(name='mrs5.max.browser.controlpanel.IMAXUISettings.hub_server')
        domain = api.portal.get_registry_record(name='mrs5.max.browser.controlpanel.IMAXUISettings.domain')
        oauth_server = max_server + '/info'
        buttonbar_selected = api.portal.get_registry_record(name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.buttonbar_selected')

        if 'username' in self.params:
            username = self.params['username']
            user = api.user.get(username=username)
            if hasattr(user, 'language') and user.getProperty('language') != '':
                language = user.getProperty('language')
            else:
                language = api.portal.get_default_language()
        else:
            language = api.portal.get_default_language()

        session = requests.Session()
        resp = session.get(oauth_server)

        try:
            max_oauth_server = resp.json()['max.oauth_server']
        except:
            max_oauth_server = 'ERROR: UNABLE TO CONNECT TO MAX OAUTH SERVER'

        show_news_in_app = api.portal.get_registry_record(name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.show_news_in_app')

        info = dict(main_color=main_color,
                    secondary_color=secondary_color,
                    max_server=max_server,
                    max_server_alias=max_server_alias,
                    hub_server=hub_server,
                    domain=domain,
                    oauth_server=oauth_server,
                    max_oauth_server=max_oauth_server,
                    show_news_in_app=show_news_in_app,
                    buttonbar_selected=buttonbar_selected,
                    language=language
                    )
        return ApiResponse(info)
