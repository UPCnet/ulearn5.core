# -*- coding: utf-8 -*-
import logging

from minimal.core.services import UnknownEndpoint, check_methods
from minimal.core.services.group_communities import GroupCommunities
from plone.restapi.services import Service

logger = logging.getLogger(__name__)


class Group(Service):
    """
    - Endpoint: @api/groups/{group}
    - Method: GET
        Endpoint NOT IMPLEMENTED

    - Subpaths allowed: YES
    """

    PATH_DICT = {
        'communitites': GroupCommunities
    }

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request
        self.obj = kwargs.get('obj', None)

    def handle_subpath(self, subpath):
        """ Function used to spread the request to the corresponding subpath """
        if not subpath:
            return self.reply()

        next_segment = subpath[0]
        handler_class = self.PATH_DICT.get(next_segment)

        if handler_class:
            kwargs = {'obj': self.obj}
            handler = handler_class(self.context, self.request, **kwargs)
            return handler.handle_subpath(subpath[1:])

        raise UnknownEndpoint(f"Unknown sub-endpoint: {next_segment}")

    @check_methods(methods=['GET'])
    def reply(self):
        raise NotImplementedError("This endpoint is not implemented.")
