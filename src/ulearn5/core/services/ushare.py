# -*- coding: utf-8 -*-
import logging

from plone import api
from plone.restapi.services import Service
from souper.interfaces import ICatalogFactory
from ulearn5.core.services import (ObjectNotFound, UnknownEndpoint,
                                   check_methods)
from ulearn5.core.services.utils import lookup_user
from zope.component import getUtilitiesFor, getUtility

# from ulearn5.core.controlpanel import IUlearnControlPanelSettings
# from ulearn5.core.utils import calculatePortalTypeOfInternalPath


logger = logging.getLogger(__name__)


class Ushare(Service):
    """
    - Endpoint: @api/people/{username}/ushare
    - Method: GET
        - Optional params
            - domain (str)

        Returns the user properties values for ushare.
    - Subpaths allowed: NO
    """

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request
        self.username = kwargs.get('username', None)

    def handle_subpath(self, subpath):
        """ Function used to spread the request to the corresponding subpath """
        if subpath:
            return UnknownEndpoint(f'Unknown sub-endpoint: {"/".join(subpath)}')

        return self.reply()

    @check_methods(methods=['GET'])
    def reply(self):
        if '@' in self.username:
            raise ObjectNotFound('Invalid username')

        user = lookup_user(self.username, raisable=True)
        ts = api.portal.get_tool(name='translation_service')
        domain = 'ulearn5.' + domain if domain else 'ulearn'
        lang = self.get_user_language()

        user_properties_utility = self.get_user_properties_utility()

        try:
            extender_name = self.get_extender_name()
            if extender_name in self.get_available_extenders():
                user_properties_utility = getUtility(
                    ICatalogFactory, name=extender_name)

            rendered_properties = self.get_rendered_properties(
                user, user_properties_utility, ts, domain, lang)

            result = {
                'username': user.id,
                'fullname': user.getProperty('fullname', ''),
                'email': user.getProperty('email', ''),
                'language': user.getProperty('language', 'ca'),
                'more_info': rendered_properties
            }

        except Exception as e:
            raise ObjectNotFound('Something went wrong') from e
        return {"data": result, "code": 200}

    def get_user_language(self):
        current = api.user.get_current()
        return current.getProperty('language')

    def get_user_properties_utility(self):
        return getUtility(ICatalogFactory, name='user_properties')

    def get_extender_name(self):
        return api.portal.get_registry_record(
            'base5.core.controlpanel.core.IBaseCoreControlPanelSettings.user_properties_extender')

    def get_available_extenders(self):
        return [a[0] for a in getUtilitiesFor(ICatalogFactory)]

    def get_rendered_properties(self, user, user_properties_utility, ts, domain, lang):
        rendered_properties = []
        hasPublicProp = hasattr(user_properties_utility, 'public_properties')
        for prop in user_properties_utility.directory_properties:
            if prop not in ['fullname', 'email']:
                if not hasPublicProp or (
                        hasPublicProp
                        and
                        prop in user_properties_utility.
                        public_properties):
                    userProp = user.getProperty(prop, '')
                    if userProp:
                        check = user.getProperty('check_' + prop, '')
                        if check == '' or check:
                            rendered_properties.append(
                                dict(
                                    key=prop, name=ts.translate(
                                        prop, context=self.request,
                                        domain=domain, target_language=lang),
                                    value=userProp,))
        return rendered_properties
