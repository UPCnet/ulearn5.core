# -*- coding: utf-8 -*-
from plone import api
from plone.restapi.services import Service
from souper.interfaces import ICatalogFactory
from zope.component import getUtilitiesFor, getUtility

from ulearn5.core.services import (ObjectNotFound, UnknownEndpoint, check_methods)
from ulearn5.core.services.utils import lookup_user

import logging

logger = logging.getLogger(__name__)


class All(Service):
    """
    - Endpoint: @api/people/{username}/all
    - Method: GET
        Returns the user all properties values.
    - Subpaths allowed: NO
    """

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request
        self.username = kwargs.get('username')

    def handle_subpath(self, subpath):
        """ Function used to spread the request to the corresponding subpath """
        if subpath:
            return UnknownEndpoint(f'Unknown sub-endpoint: {"/".join(subpath)}')

        return self.reply()

    @check_methods(methods=['GET'])
    def reply(self):
        try:
            user = lookup_user(self.username, raisable=True)
            rendered_properties = {self.username: {}}

            extender_name = self.get_extender_name()
            if extender_name and extender_name in self.get_available_extenders():
                extended_user_properties_utility = getUtility(
                    ICatalogFactory, name=extender_name)
                self.update_rendered_properties(
                    rendered_properties, extended_user_properties_utility, user)
            else:
                self.update_rendered_properties(rendered_properties, getUtility(
                    ICatalogFactory, name='user_properties'), user)

            return rendered_properties
        except Exception as e:
            return {"error": str(e), "code": 404}

    def get_extender_name(self):
        return api.portal.get_registry_record(
            'base5.core.controlpanel.core.IBaseCoreControlPanelSettings.user_properties_extender')

    def get_available_extenders(self):
        return [a[0] for a in getUtilitiesFor(ICatalogFactory)]

    def update_rendered_properties(self, rendered_properties, properties_utility, user):
        for prop in properties_utility.properties:
            userProp = user.getProperty(prop, '')
            if userProp:
                rendered_properties[self.username].update({prop: userProp})
