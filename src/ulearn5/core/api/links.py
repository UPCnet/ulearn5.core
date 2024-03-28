# -*- coding: utf-8 -*-
from Acquisition import aq_inner
from Products.CMFPlone.interfaces import IPloneSiteRoot

from five import grok
from plone import api
from plone.app.contenttypes.interfaces import ILink
from plone.app.layout.navigation.root import getNavigationRootObject
from plone.registry.interfaces import IRegistry
from zope.component import getUtility
from zope.component import queryUtility

from ulearn5.core.api import ApiResponse
from ulearn5.core.api import REST
from ulearn5.core.api import api_resource
from ulearn5.core.api.root import APIRoot
from ulearn5.core.content.community import ICommunity
from ulearn5.core.controlpanel import IUlearnControlPanelSettings
from ulearn5.core.hooks import packages_installed
from ulearn5.core.utils import calculatePortalTypeOfInternalPath
import logging


logger = logging.getLogger(__name__)


class Links(REST):
    """
        /api/links
    """
    placeholder_type = 'link'
    placeholder_id = 'language'

    grok.adapts(APIRoot, IPloneSiteRoot)
    grok.require('base.authenticated')


class Link(REST):
    """
        /api/links/{language}

        http://localhost:8090/Plone/api/links/es

    """
    grok.adapts(Links, IPloneSiteRoot)
    grok.require('base.authenticated')

    @api_resource(required=['language'])
    def GET(self):
        """ Return the links from Menu Gestion folder and Menu ControlPanel """
        language = self.params['language']
        portal = api.portal.get()
        registry = queryUtility(IRegistry)
        ulearn_tool = registry.forInterface(IUlearnControlPanelSettings)
        if ulearn_tool.url_site == None or ulearn_tool.url_site == '':
            portal_url = portal.absolute_url()
        else:
            portal_url = ulearn_tool.url_site

        resultsGestion = {}

        installed = packages_installed()
        if 'ulearn5.nomines' in installed:
            dni = api.user.get_current().getProperty('dni')
            if dni or dni != "":
                JSONproperties = api.portal.get_tool(
                    name='portal_properties').nomines_properties

                titleNomines = JSONproperties.getProperty('app_link_en')
                if language == 'ca':
                    titleNomines = JSONproperties.getProperty('app_link_ca')
                elif language == 'es':
                    titleNomines = JSONproperties.getProperty('app_link_es')

                nominas_folder_name = JSONproperties.getProperty(
                    'nominas_folder_name').lower()
                urlNomines = api.portal.get().absolute_url() + '/' + nominas_folder_name + '/' + dni
                nominesLink = dict(
                    id=dni,
                    internal=True,
                    is_community_belonged=False,
                    link=urlNomines,
                    title=titleNomines,
                    type_when_follow_url="privateFolder",
                    url=urlNomines  # UTALK, Miranza APP
                )

                resultsGestion[titleNomines] = []
                resultsGestion[titleNomines].append(nominesLink)

        if 'ulearn5.nominesmedichem' in installed:
            from ulearn5.nominesmedichem.utils import get_str_hash
            dni = api.user.get_current().getProperty('dni')
            if dni or dni != "":
                dni_hashed = get_str_hash(dni.upper())
                JSONproperties = api.portal.get_tool(
                    name='portal_properties').nomines_properties

                titleNomines = JSONproperties.getProperty('app_link_en')
                if language == 'ca':
                    titleNomines = JSONproperties.getProperty('app_link_ca')
                elif language == 'es':
                    titleNomines = JSONproperties.getProperty('app_link_es')

                nominas_folder_name = JSONproperties.getProperty(
                    'nominas_folder_name').lower()
                urlNomines = api.portal.get().absolute_url() + '/' + nominas_folder_name + '/' + dni_hashed

                nominesLink = dict(
                    id=dni_hashed,
                    internal=True,
                    is_community_belonged=False,
                    link=urlNomines,
                    title=titleNomines,
                    type_when_follow_url="privateFolder",
                    url=urlNomines  # UTALK, Miranza APP
                )

                resultsGestion[titleNomines] = []
                resultsGestion[titleNomines].append(nominesLink)

        try:
            # fixed en code... always in this path
            path = portal['gestion']['menu'][language]
            folders = api.content.find(context=path, portal_type=(
                'Folder', 'privateFolder'), depth=1)
            found = True
        except:
            # 'Menu Gestion not configured or Language not found.'
            resultsGestion = ''
            found = False

        if found:
            # Links from gestion folder
            for folder in folders:
                resultsGestion[folder.Title] = []
                menufolder = folder.getObject().items()
                for item in menufolder:
                    id, obj = item
                    internal = True if obj.remoteUrl.startswith(portal_url) else False
                    if internal:
                        url = obj.remoteUrl.replace('#', '')
                        obj_type = calculatePortalTypeOfInternalPath(url, portal_url)
                        belong = self.urlBelongsToCommunity(url, portal_url)
                    else:
                        url = obj.remoteUrl
                        obj_type = None
                        belong = False
                    if ILink.providedBy(obj):
                        menuLink = dict(
                            id=id,
                            internal=internal,
                            is_community_belonged=belong,
                            link=url,
                            title=obj.title,
                            type_when_follow_url=obj_type,
                            url=url,  # UTALK, Miranza APP
                        )
                        resultsGestion[folder.Title].append(menuLink)

            if not resultsGestion:
                # 'No Menu Gestion configured in this Site.'
                resultsGestion = ''

        registry = getUtility(IRegistry)
        settings = registry.forInterface(IUlearnControlPanelSettings, check=False)

        # Links from controlpanel
        resultsControlPanel = []

        # Candidato a eliminar en futura migración igual que la funcionalidad en el controlpanel.
        if settings.quicklinks_table:
            for item in settings.quicklinks_table:
                quickLink = dict(
                    id=None,
                    internal=internal,
                    icon=item['icon'],
                    link=item['link'],
                    title=item['text'],
                    type_when_follow_url=obj_type,
                    url=item['link'],  # UTALK, Miranza APlogger = logging.getLogger(__name__)P
                )
                resultsControlPanel.append(quickLink)

        if not resultsControlPanel:
            # 'Menu Quicklinks not configured in the ControlPanel.'
            resultsControlPanel = ''

        values = {'Menu_Gestion': resultsGestion,
                  'Menu_Controlpanel': resultsControlPanel}

        return ApiResponse(values)

    def urlBelongsToCommunity(self, url, portal_url):
        tree_site = api.portal.get()
        partial_path = url.split(portal_url)[1]
        partial_path.replace('#', '')  # Sanitize if necessary
        if partial_path.endswith('/view/'):
            partial_path = partial_path.split('/view/')[0]
        elif partial_path.endswith('/view'):
            partial_path = partial_path.split('/view')[0]
        partial_path = partial_path.encode('utf-8')
        segments = partial_path.split('/')
        leafs = [segment for segment in segments if segment]
        for leaf in leafs:
            try:
                obj = aq_inner(tree_site.unrestrictedTraverse(leaf))
            except:
                logger.error('Error in retrieving object: %s' % url)
            if (ICommunity.providedBy(obj)):
                return True
            else:
                tree_site = obj

        return False
