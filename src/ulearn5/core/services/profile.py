# -*- coding: utf-8 -*-
import logging

from plone import api
from plone.restapi.services import Service
from souper.interfaces import ICatalogFactory
from ulearn5.core.services import (ObjectNotFound, UnknownEndpoint,
                                   check_methods, check_required_params)
from zope.component import ComponentLookupError, getUtilitiesFor, getUtility

logger = logging.getLogger(__name__)


class Profile(Service):
    """
    - Endpoint: @api/profile
    - Method: PUT
        Updates profile.

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

    @check_methods(methods=['PUT'])
    @check_required_params(params=['username'])
    def reply(self):
        username = self.request.form.get('username')
        if not self.is_valid_user(username):
            raise ObjectNotFound(f"User with ID  {username} not found")

        try:
            user = self.get_user(username)
            self.update_user_properties(user, self.request.form)
        except ComponentLookupError as e:
            return self.handle_component_lookup_error(e, username)

        value = f"L'usuari {username} s'ha actualitzat."
        return {"success": value, "code": 200}

    def is_valid_user(self, username):
        mt = api.portal.get_tool(name='portal_membership')
        return mt.getMemberById(username) is not None

    def get_user(self, username):
        return api.user.get(username=username)

    def update_user_properties(self, user, properties):
        user.setMemberProperties(mapping=properties)

    def handle_component_lookup_error(self, e, username):
        user_properties_utility = self.get_user_properties_utility()
        raise ObjectNotFound(
            f"Some properties don't exist. The correct ones are {user_properties_utility.properties}")

    def get_user_properties_utility(self):
        user_properties_utility = getUtility(ICatalogFactory, name='user_properties')
        extender_name = api.portal.get_registry_record(
            'base5.core.controlpanel.core.IBaseCoreControlPanelSettings.user_properties_extender')
        if extender_name in self.get_available_extenders():
            user_properties_utility = getUtility(ICatalogFactory, name=extender_name)
        return user_properties_utility

    def get_available_extenders(self):
        return [a[0] for a in getUtilitiesFor(ICatalogFactory)]
