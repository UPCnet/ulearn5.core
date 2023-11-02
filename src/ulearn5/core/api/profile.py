# -*- coding: utf-8 -*-
from Products.CMFPlone.interfaces import IPloneSiteRoot

from five import grok
from plone import api
from souper.interfaces import ICatalogFactory
from zope.component import ComponentLookupError
from zope.component import getUtilitiesFor
from zope.component import getUtility

from base5.core.utils import json_response
from ulearn5.core.api import ApiResponse
from ulearn5.core.api import REST
from ulearn5.core.api import api_resource
from ulearn5.core.api.root import APIRoot

import json


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


class Profile(REST):
    """
        /api/profile
    """

    grok.adapts(APIRoot, IPloneSiteRoot)
    @json_response
    def PUT(self):
        """ Update profile. """
        body = self.request.get('BODY', False)
        if not body:
            return self.error("Bad Request", "Body are required.", 400)

        data = json.loads(body)
        user = data.get('username', False)
        if not user:
            return self.error("Bad Request", "username in body are required.", 400)

        mt = api.portal.get_tool(name='portal_membership')
        if mt.getMemberById(user) is None:
            return self._error(
                404, "Not Found",
                "The user '{}' was deleted and currently does not exist".format(user)
            )

        try:
            username = api.user.get(username=user)
        except ComponentLookupError:
            return self._error(
                404, "Not Found",
                "The user '{}' does not exist".format(user)
            )
        try:
            username.setMemberProperties(mapping=data)
        except ComponentLookupError:
            user_properties_utility = getUtility(ICatalogFactory, name='user_properties')

            extender_name = api.portal.get_registry_record('base5.core.controlpanel.core.IBaseCoreControlPanelSettings.user_properties_extender')
            if extender_name in [a[0] for a in getUtilitiesFor(ICatalogFactory)]:
                user_properties_utility = getUtility(ICatalogFactory, name=extender_name)

            return self._error(
                404, "Not Found",
                "Some properties aren't exists. The correct ones are {}".format(user_properties_utility.properties)
            )

        value = "L'usuari {} s'ha actualitzat.".format(username)
        return {'success': value}