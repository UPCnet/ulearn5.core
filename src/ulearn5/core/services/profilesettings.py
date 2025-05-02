# -*- coding: utf-8 -*-
import logging

from plone import api
from plone.restapi.services import Service
from souper.interfaces import ICatalogFactory
from ulearn5.core.services import UnknownEndpoint, check_methods
from zope.component import getUtilitiesFor, getUtility

logger = logging.getLogger(__name__)


class ProfileSettings(Service):
    """
    - Endpoint: @api/profilesettings
    - Method: GET
        Optional params:
            - domain (str)
        Returns the settings for ushare profile.

    - Subpaths allowed: NO
    """

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request

    def handle_subpath(self, subpath):
        """ Function used to spread the request to the corresponding subpath """
        if subpath:
            return UnknownEndpoint(f'Unknown sub-endpoint: {"/".join(subpath)}')

        return self.reply()

    @check_methods(methods=['GET'])
    def reply(self):
        user_properties_utility = self.get_user_properties_utility()

        result = {'fields_readonly': self.get_profile_properties(
            user_properties_utility, 'profile_properties_ushare_readonly'),
            'fields_novisible': self.get_profile_properties(
            user_properties_utility, 'profile_properties_ushare_novisible'),
            'available_languages': self.get_available_languages()}

        return result

    def get_user_properties_utility(self):
        user_properties_utility = getUtility(ICatalogFactory, name='user_properties')
        extender_name = api.portal.get_registry_record(
            'base5.core.controlpanel.core.IBaseCoreControlPanelSettings.user_properties_extender')
        if extender_name in [a[0] for a in getUtilitiesFor(ICatalogFactory)]:
            user_properties_utility = getUtility(ICatalogFactory, name=extender_name)
        return user_properties_utility

    def get_profile_properties(self, user_properties_utility, property_name):
        return getattr(user_properties_utility, property_name, [])

    def get_available_languages(self):
        return api.portal.get_tool(name='portal_languages').supported_langs
