# -*- coding: utf-8 -*-
from five import grok
from Products.CMFPlone.interfaces import IPloneSiteRoot
from plone import api
from ulearn5.core.api import ApiResponse
from ulearn5.core.api import REST
from ulearn5.core.api import api_resource
from ulearn5.core.api.root import APIRoot
from zope.component import getUtility
from plone.registry.interfaces import IRegistry
from ulearn5.core.controlpanel import IUlearnControlPanelSettings
from plone.app.contenttypes.interfaces import ILink


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
