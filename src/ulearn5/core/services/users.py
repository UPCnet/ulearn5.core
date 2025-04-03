# -*- coding: utf-8 -*-
import logging

from plone import api
from plone.restapi.services import Service
from souper.soup import get_soup
from ulearn5.core.services import UnknownEndpoint, check_methods
from ulearn5.core.utils import get_or_initialize_annotation

# from ulearn5.core.controlpanel import IUlearnControlPanelSettings
# from ulearn5.core.utils import calculatePortalTypeOfInternalPath


logger = logging.getLogger(__name__)


class Users(Service):
    """
    - Endpoint: @api/people/users
    - Method: GET
        Returns a list containing all the user IDs
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
        portal = api.portal.get()
        soup = get_soup('user_properties', portal)
        records = [r for r in soup.data.items()]

        result = []
        for record in records:
            result.append(record[1].attrs['id'])

        result.sort()
        return {"data": result, "code": 200}
