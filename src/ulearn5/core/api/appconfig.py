# # -*- coding: utf-8 -*-
# from five import grok
# from Products.CMFPlone.interfaces import IPloneSiteRoot
# from plone import api
# from ulearn5.core.api import ApiResponse
# from ulearn5.core.api import REST
# from ulearn5.core.api import api_resource
# from ulearn5.core.api.root import APIRoot
# import requests

# import logging

# logger = logging.getLogger(__name__)


# class Appconfig(REST):
#     """
#         /api/appconfig --> Idioma por defecto del site
#         /api/appconfig?username=nom.cognom --> Idioma del perfil del usuario

#     """
#     grok.adapts(APIRoot, IPloneSiteRoot)
#     grok.require('base.authenticated')

#     __restapi_doc_definition__ = {
#         "Appconfig": {
#             "properties": {
#                 "domain": {
#                     "type": "string"
#                 },
#                 "hub_server": {
#                     "type": "string"
#                 },
#                 "max_oauth_server": {
#                     "type": "string"
#                 },
#                 "max_server": {
#                     "type": "string"
#                 },
#                 "max_server_alias": {
#                     "type": "string"
#                 },
#                 "oauth_server": {
#                     "type": "string"
#                 },
#                 "language": {
#                     "type": "string"
#                 },
#                 "main_color": {
#                     "type": "string"
#                 },
#                 "secondary_color": {
#                     "type": "string"
#                 },
#                 "show_news_in_app": {
#                     "type": "boolean",
#                     "description": "Mostrar la vista de noticias o no en la APP"
#                 },
#                 "buttonbar_selected": {
#                     "type": "string",
#                     "description": "Vista principal de la APP",
#                     "enum": [
#                         "news",
#                         "stream",
#                         "mycommunities",
#                         "sharedwithme"
#                     ]
#                 }
#             }
#         }
#     }

#     __restapi_doc_service__ = {
#         "/api/appconfig": {
#             "get": {
#                 "tags": [
#                     "appconfig"
#                 ],
#                 "summary": "Retorna la personalització del client per l'APP uTalk",
#                 "description": "Quina es la vista principal, colors, si mostra noticies, etc.",
#                 "operationId": "get_appconfig",
#                 "responses": {
#                     "200": {
#                         "description": "Successful operation",
#                         "content": {
#                             "application/json": {
#                                 "schema": {
#                                     "$ref": "#/components/schemas/Appconfig"
#                                 }
#                             }
#                         }
#                     },
#                     "401": {
#                         "description": "Authorization information is missing or invalid."
#                     },
#                     "5XX": {
#                         "description": "Unexpected error."
#                     }
#                 }
#             }
#         }
#     }

#     @api_resource()
#     def GET(self):
#         main_color = api.portal.get_registry_record(name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.main_color')
#         secondary_color = api.portal.get_registry_record(name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.secondary_color')
#         max_server = api.portal.get_registry_record(name='mrs5.max.browser.controlpanel.IMAXUISettings.max_server')
#         max_server_alias = api.portal.get_registry_record(name='mrs5.max.browser.controlpanel.IMAXUISettings.max_server_alias')
#         hub_server = api.portal.get_registry_record(name='mrs5.max.browser.controlpanel.IMAXUISettings.hub_server')
#         domain = api.portal.get_registry_record(name='mrs5.max.browser.controlpanel.IMAXUISettings.domain')
#         oauth_server = max_server + '/info'
#         buttonbar_selected = api.portal.get_registry_record(name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.buttonbar_selected')

#         if 'username' in self.params:
#             username = self.params['username']
#             user = api.user.get(username=username)
#             if hasattr(user, 'language') and user.getProperty('language') != '':
#                 language = user.getProperty('language')
#             else:
#                 language = api.portal.get_default_language()
#         else:
#             language = api.portal.get_default_language()

#         session = requests.Session()
#         resp = session.get(oauth_server)

#         try:
#             max_oauth_server = resp.json()['max.oauth_server']
#         except:
#             max_oauth_server = 'ERROR: UNABLE TO CONNECT TO MAX OAUTH SERVER'

#         show_news_in_app = api.portal.get_registry_record(name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.show_news_in_app')

#         info = dict(main_color=main_color,
#                     secondary_color=secondary_color,
#                     max_server=max_server,
#                     max_server_alias=max_server_alias,
#                     hub_server=hub_server,
#                     domain=domain,
#                     oauth_server=oauth_server,
#                     max_oauth_server=max_oauth_server,
#                     show_news_in_app=show_news_in_app,
#                     buttonbar_selected=buttonbar_selected,
#                     language=language
#                     )

#         if 'username' in self.params:
#             logger.error('XXX mobile access username {} in domain {}'.format(self.params.get('username'),domain))

#         return ApiResponse(info)
