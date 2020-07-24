# -*- coding: utf-8 -*-
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.interfaces import IPloneSiteRoot

from five import grok
from plone import api
from plone.app.contenttypes.interfaces import ILink
from plone.registry.interfaces import IRegistry
from zope.component import getUtility

from ulearn5.core.api import ApiResponse
from ulearn5.core.api import REST
from ulearn5.core.api import api_resource
from ulearn5.core.api.root import APIRoot
from ulearn5.core.controlpanel import IUlearnControlPanelSettings
from ulearn5.core.hooks import packages_installed


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

        resultsGestion = {}

        installed = packages_installed()
        if 'ulearn5.nomines' in installed:
            dni = api.user.get_current().getProperty('dni')
            if dni or dni != "":
                JSONproperties = getToolByName(self, 'portal_properties').nomines_properties

                titleNomines = JSONproperties.getProperty('app_link_en')
                if language == 'ca':
                    titleNomines = JSONproperties.getProperty('app_link_ca')
                elif language == 'es':
                    titleNomines = JSONproperties.getProperty('app_link_es')

                nominas_folder_name = JSONproperties.getProperty('nominas_folder_name').lower()
                urlNomines = api.portal.get().absolute_url() + '/' + nominas_folder_name + '/' + dni

                nominesLink = dict(title=titleNomines,
                                   url=urlNomines
                                   )

                resultsGestion[titleNomines] = []
                resultsGestion[titleNomines].append(nominesLink)

        try:
            path = portal['gestion']['menu'][language]  # fixed en code... always in this path
            folders = api.content.find(context=path, portal_type=('Folder', 'privateFolder'), depth=1)
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
                    if ILink.providedBy(item[1]):
                        menuLink = dict(url=item[1].remoteUrl,
                                        title=item[1].title,
                                        )
                        resultsGestion[folder.Title].append(menuLink)

            if not resultsGestion:
                # 'No Menu Gestion configured in this Site.'
                resultsGestion = ''

        registry = getUtility(IRegistry)
        settings = registry.forInterface(IUlearnControlPanelSettings, check=False)

        # Links from controlpanel
        resultsControlPanel = []

        # installed = packages_installed()
        # if 'ulearn5.nomines' in installed:
        #     dni = api.user.get_current().getProperty('dni')
        #     if dni or dni != "":
        #         JSONproperties = getToolByName(self, 'portal_properties').nomines_properties

        #         titleNomines = JSONproperties.getProperty('app_link_en')
        #         if language == 'ca':
        #             titleNomines = JSONproperties.getProperty('app_link_ca')
        #         elif language == 'es':
        #             titleNomines = JSONproperties.getProperty('app_link_es')

        #         nominas_folder_name = JSONproperties.getProperty('nominas_folder_name').lower()
        #         urlNomines = api.portal.get().absolute_url() + '/' + nominas_folder_name + '/' + dni

        #         nominesLink = dict(title=titleNomines,
        #                            url=urlNomines,
        #                            icon='fa-file-text-o',
        #                            )

        #         resultsControlPanel.append(nominesLink)

        if settings.quicklinks_table:
            for item in settings.quicklinks_table:
                quickLink = dict(title=item['text'],
                                 url=item['link'],
                                 icon=item['icon'],
                                 )
                resultsControlPanel.append(quickLink)

        if not resultsControlPanel:
            # 'Menu Quicklinks not configured in the ControlPanel.'
            resultsControlPanel = ''

        values = {'Menu_Gestion': resultsGestion, 'Menu_Controlpanel': resultsControlPanel}

        return ApiResponse(values)
