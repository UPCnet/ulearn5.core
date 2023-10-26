# -*- coding: utf-8 -*-
from Products.CMFPlone.interfaces import IPloneSiteRoot

from five import grok
from plone import api
from souper.interfaces import ICatalogFactory
from zope.component import getUtilitiesFor
from zope.component import getUtility

from ulearn5.core.api import ApiResponse
from ulearn5.core.api import REST
from ulearn5.core.api import api_resource
from ulearn5.core.api.root import APIRoot


class ProfileSettings(REST):
    """
        /api/profilesettings

        Returns the user properties values for ushare.

        :param domain
    """

    grok.adapts(APIRoot, IPloneSiteRoot)
    grok.require('base.authenticated')

    @api_resource()
    def GET(self):
        """ Returns the settings for ushare profile. """
        user_properties_utility = getUtility(ICatalogFactory, name='user_properties')

        extender_name = api.portal.get_registry_record('base5.core.controlpanel.core.IBaseCoreControlPanelSettings.user_properties_extender')
        if extender_name in [a[0] for a in getUtilitiesFor(ICatalogFactory)]:
            user_properties_utility = getUtility(ICatalogFactory, name=extender_name)

        result = {
            'fields_readonly': user_properties_utility.profile_properties_ushare_readonly if hasattr(user_properties_utility, 'profile_properties_ushare_readonly') else [],
            'fields_novisible': user_properties_utility.profile_properties_ushare_novisible if hasattr(user_properties_utility, 'profile_properties_ushare_novisible') else [],
            'available_languages': api.portal.get_tool(name='portal_languages').supported_langs
        }

        return ApiResponse(result)