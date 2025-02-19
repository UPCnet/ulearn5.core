# -*- coding: utf-8 -*-
import logging

from minimal.core.services import UnknownEndpoint, check_methods
from plone import api
from plone.restapi.services import Service

logger = logging.getLogger(__name__)


class Count(Service):
    """
    - Endpoint: @api/count
    - Method: GET
        Returns number of communities
    - Subpaths allowed: NO
    """

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request
        self.community_type = kwargs.get('community_type', None)

    def handle_subpath(self, subpath):
        """ Function used to spread the request to the corresponding subpath """
        if subpath:
            return UnknownEndpoint(f'Unknown sub-endpoint: {"/".join(subpath)}')

        return self.reply()

    @check_methods(methods=['GET'])
    def reply(self):
        pc = api.portal.get_tool('portal_catalog')

        if self.community_type:
            results = pc.unrestrictedSearchResults(
                portal_type='ulearn.community', community_type=self.community_type)
        else:
            results = pc.unrestrictedSearchResults(portal_type='ulearn.community')

        return {"data": len(results), "code": 200}
