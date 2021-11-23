# -*- coding: utf-8 -*-
from plone.restapi.services import Service
from zope.interface import implementer
from zope.publisher.interfaces import IPublishTraverse
# from five import grok
from Products.CMFPlone.interfaces import IPloneSiteRoot
from plone import api
# from ulearn5.core.api.root import APIRoot
import requests

import logging

logger = logging.getLogger(__name__)


@implementer(IPublishTraverse)
class Appconfig(Service):
    """
        /api/appconfig --> Idioma por defecto del site
        /api/appconfig?username=nom.cognom --> Idioma del perfil del usuario

    """
    # grok.adapts(APIRoot, IPloneSiteRoot)
    # grok.require('base.authenticated')

    __ploneteam_restapi_doc_definitions__ = {
        "Appconfig": {
            "properties": {
                "domain": {
                    "type": "string",
                    "example": "domain",
                },
                "hub_server": {
                    "type": "string",
                    "example": "https://hub.ulearn.upcnet.es",
                },
                "max_oauth_server": {
                    "type": "string",
                    "example": "https://oauth.upcnet.es/domain",
                },
                "max_server": {
                    "type": "string",
                    "example": "https://max.upcnet.es/domain",
                },
                "max_server_alias": {
                    "type": "string",
                    "example": "https://ulearn.upcnet.es/domain/max",
                },
                "oauth_server": {
                    "type": "string",
                    "example": "https://max.upcnet.es/domain/info",
                },
                "language": {
                    "type": "string",
                    "example": "ca",
                },
                "main_color": {
                    "type": "string",
                    "example": "#04192D",
                },
                "secondary_color": {
                    "type": "string",
                    "example": "#04192D",
                },
                "show_news_in_app": {
                    "type": "boolean",
                    "description": "Mostrar la vista de noticias o no en la APP",
                    "example": "true",
                },
                "buttonbar_selected": {
                    "type": "string",
                    "description": "Vista principal de la APP",
                    "enum": [
                        "news",
                        "stream",
                        "mycommunities",
                        "sharedwithme"
                    ],
                    "example": "news",
                }
            }
        }
    }
   
    __ploneteam_restapi_doc_service__ = {
        "/appconfig": {
            "get": {
                "tags": [
                    "appconfig"
                ],
                "summary": "Retorna la personalització del client per l'APP uTalk",
                "description": "Quina es la vista principal, colors, si mostra noticies, etc.",
                "operationId": "Appconfig",
                "responses": {
                    "200": {
                        "description": "Successful operation",
                        "schema": {
                            "type": "array",
                            "items": {
                                "$ref": "#/definitions/Appconfig"
                            }
                        }                        
                    },
                    "401": {
                        "description": "Authorization information is missing or invalid."
                    },
                    "5XX": {
                        "description": "Unexpected error."
                    }
                }
            }
        }
    }

    def __init__(self, context, request):
        super(Appconfig, self).__init__(context, request)
        self.params = []
        self.query = self.request.form.copy()

    def publishTraverse(self, request, name):
        # Consume any path segments after /@appconfig as parameters
        self.params.append(name)
        return self

    def render(self):
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

        if 'username' in self.params:
            logger.error('XXX mobile access username {} in domain {}'.format(self.params.get('username'),domain))

        return info
