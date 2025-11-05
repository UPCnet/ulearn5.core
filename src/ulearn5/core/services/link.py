# -*- coding: utf-8 -*-
import logging

from plone import api
from plone.app.contenttypes.interfaces import ILink
from plone.registry.interfaces import IRegistry
from plone.restapi.services import Service
from ulearn5.core.services import (ObjectNotFound, UnknownEndpoint,
                                   check_methods, check_roles)
from ulearn5.core.services.utils import urlBelongsToCommunity
from ulearn5.core.controlpanel import IUlearnControlPanelSettings
from ulearn5.core.hooks import packages_installed
from ulearn5.core.utils import calculatePortalTypeOfInternalPath
from zope.component import getUtility, queryUtility

logger = logging.getLogger(__name__)


class Link(Service):
    """
    - Endpoint: @api/links/{language}

    - Subpaths allowed: NO
    """

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request
        self.lang = kwargs.get('language', None)
        self.portal_url = ''

    def handle_subpath(self, subpath):
        """ Function used to spread the request to the corresponding subpath """
        if subpath:
            return UnknownEndpoint(f'Unknown sub-endpoint: {"/".join(subpath)}')

        return self.reply()

    @check_roles(roles=['Member', 'Manager', 'Api'])
    @check_methods(methods=['GET'])
    def reply(self):
        self.portal_url = self.get_portal_url()
        results_gestio = {}

        if 'ulearn5.nomines' in packages_installed():
            results_nomines = self.process_nomines()
            results_gestio[results_nomines['title']] = []
            results_gestio[results_nomines['title']].append(results_nomines)

        if 'ulearn5.nominesmedichem' in packages_installed():
            results_medichem = self.process_medichem()
            results_gestio[results_medichem['title']] = []
            results_gestio[results_medichem['title']].append(results_medichem)

        folders = self.check_gestio_menu()
        if folders:
            for folder in folders:
                res = self.get_links_from_gestion_folder(folder)
                results_gestio.update(res)

            if not results_gestio:
                results_gestio = ''

        registry = getUtility(IRegistry)
        settings = registry.forInterface(IUlearnControlPanelSettings, check=False)

        results_controlpanel = []
        if settings.quicklinks_table:
            results_controlpanel = self.get_links_from_controlpanel(settings)

        if not results_controlpanel:
            results_controlpanel = ''

        values = {
            'Menu_Gestion': results_gestio,
            'Menu_Controlpanel': results_controlpanel
        }
        return values

    def get_portal_url(self):
        portal = api.portal.get()
        registry = queryUtility(IRegistry)
        ulearn_tool = registry.forInterface(IUlearnControlPanelSettings)
        if not ulearn_tool.url_site:
            return portal.absolute_url()

        return ulearn_tool.url_site

    def process_nomines(self):
        dni = self.process_dni(should_hash=False)
        return self.process_installed_package(dni)

    def process_medichem(self):
        dni = self.process_dni(should_hash=True)
        return self.process_installed_package(dni)

    def process_dni(self, should_hash=False):
        dni = api.user.get_current().getProperty('dni')

        if should_hash and dni:
            from ulearn5.nominesmedichem.utils import get_str_hash
            return get_str_hash(dni.upper())

        return dni

    def process_installed_package(self, dni):
        portal_properties = api.portal.get_tool('portal_properties')
        json_properties = getattr(portal_properties, 'nomines_properties', None)
        if not json_properties:
            raise ObjectNotFound('Nomines_properties not found!')
        title_nomines = json_properties.getProperty(f'app_link_{self.lang}')

        nomines_folder_name = json_properties.getProperty('nominas_folder_name').lower()
        url_nomines = f'{api.portal.get().absolute_url()}/{nomines_folder_name}/{dni}'

        return {
            'id': dni,
            'internal': True,
            'is_community_belonged': False,
            'link': url_nomines,
            'title': title_nomines,
            'type_when_follow_url': 'privateFolder',
            'url': url_nomines
        }

    def check_gestio_menu(self):
        portal = api.portal.get()
        try:
            path = portal['gestion']['menu'][self.lang]
            folders = api.content.find(context=path, portal_type=(
                'Folder', 'privateFolder'), depth=1)
            return folders
        except:
            logger.error('Folders not found')
            return []

    def get_links_from_gestion_folder(self, folder):
        res = {}
        res[folder.Title] = []
        folder_items = list(folder.getObject().items())
        for item in folder_items:
            id, obj = item
            menu_items = self.process_gestion_menu_items(obj, id)
            res[folder.Title].append(menu_items)

        return res

    def process_gestion_menu_items(self, obj, id):
        if ILink.providedBy(obj):
            url = obj.remoteUrl
        else:
            url = obj.absolute_url()

        internal = url.startswith(self.portal_url)

        if internal:
            url = url.replace('#', '')
            obj_type = calculatePortalTypeOfInternalPath(url, self.portal_url)
            belong = urlBelongsToCommunity(url, self.portal_url)
        else:
            obj_type = None
            belong = False

        return {
            'id': id,
            'internal': internal,
            'is_community_belonged': belong,
            'link': url,
            'title': obj.title,
            'type_when_follow_url': obj_type,
            'url': url
        }

    def get_links_from_controlpanel(self, settings):
        res = []
        for item in settings.quicklinks_table:
            res.append({
                'id': None,
                'internal': False,  # Debe ser siempre false?
                'icon': item['icon'],
                'link': item['link'],
                'title': item['text'],
                'type_when_follow_url': '',  # Debe tener valor?
                'url': item['link']
            })

        return res
