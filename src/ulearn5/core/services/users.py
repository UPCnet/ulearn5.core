# -*- coding: utf-8 -*-
import logging

from minimal.core.services import UnknownEndpoint, check_methods
from minimal.core.utils import get_or_initialize_annotation
from plone.restapi.services import Service

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
        user_properties = get_or_initialize_annotation('user_properties')
        result = [record.get('id') for record in user_properties.values() if 'id' in record]

        result.sort()
        return {"data": result, "code": 200}
