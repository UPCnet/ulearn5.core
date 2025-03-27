# -*- coding: utf-8 -*-
import logging

from plone import api
from plone.restapi.services import Service
from souper.interfaces import ICatalogFactory
from souper.soup import get_soup
from zope.component import getUtilitiesFor, getUtility

from ulearn5.core.services import ObjectNotFound, check_methods
from ulearn5.core.services.person import Person
from ulearn5.core.services.sync import Sync
from ulearn5.core.services.users import Users

logger = logging.getLogger(__name__)


class People(Service):
    """
    - Endpoint: @api/people
    - Method: GET
        Returns all Users with their properties

    - Subpaths allowed: YES
    """

    PATH_DICT = {
        "users": Users,
        "sync": Sync
    }

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request

    def handle_subpath(self, subpath):
        """ Function used to spread the request to the corresponding subpath """
        if not subpath:
            return self.reply()

        next_segment = subpath[0]
        handler_class = self.PATH_DICT.get(next_segment)

        if handler_class:
            handler = handler_class(self.context, self.request)
            return handler.handle_subpath(subpath[1:])

        # No subpath is considered wrong, as any user will be
        # updated if it's found, and created otherwise
        # This means any string in its path will be the User id
        kwargs = {'username': next_segment}
        new_handler = Person(self.context, self.request, **kwargs)
        return new_handler.handle_subpath(subpath[1:])

    @check_methods(methods=['GET'])
    def reply(self):
        records = self.get_records()
        result = {}
        extender_name = api.portal.get_registry_record(
            'base5.core.controlpanel.core.IBaseCoreControlPanelSettings.user_properties_extender')
        user_properties_utility = getUtility(ICatalogFactory, name='user_properties')

        for record in records:
            username = record[1].attrs['username']
            user = api.user.get(username=username)

            if not user:
                raise ObjectNotFound(f'User with ID {username} not found')

            rendered_properties = []
            if extender_name in [a[0] for a in getUtilitiesFor(ICatalogFactory)]:
                extended_user_properties_utility = getUtility(
                    ICatalogFactory, name=extender_name)
                rendered_properties = self.extract_properties(extended_user_properties_utility, user)

            else:
                rendered_properties = self.extract_properties(user_properties_utility, user)

            result[record[1].attrs['id']] = rendered_properties
        return {"data": result, "code": 200}

    def extract_properties(self, utility, user):
        # TODO: Mirar si esto hay que hacerlo en ambos casos
        if '@' in user.getId():
                return []

        directory_properties = getattr(utility, 'directory_properties', [])
        public_properties = getattr(utility, 'public_properties', [])
        rendered_properties = []

        for prop in directory_properties:
            if public_properties and prop not in public_properties:
                continue

            user_prop = user.getProperty(prop, '')
            if user_prop:
                check = user.getProperty('check_' + prop, '')
                if check is False:
                    continue

                rendered_properties.append({
                    'name': prop,
                    'value': user_prop,
                    'icon': getattr(utility, 'directory_icons', {}).get(prop, None)
                })

        return rendered_properties

    def get_records(self):
        portal = api.portal.get()
        user_properties = get_soup('user_properties', portal)
        records = [r for r in user_properties.data.items()]
        return records
