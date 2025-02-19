# -*- coding: utf-8 -*-
import logging

from minimal.core.services import UnknownEndpoint, check_methods
from minimal.core.services.group import Group
from minimal.core.services.utils import lookup_group
from plone.restapi.services import Service

logger = logging.getLogger(__name__)


class Groups(Service):
    """
    - Endpoint: @api/groups
    - Method: GET
        Endpoint NOT IMPLEMENTED

    - Subpaths allowed: YES
    """

    PATH_DICT = {}

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
        
        # There's a subpath, but there's no handler for it
        # May be a group? -> Delegate to Group
        group = lookup_group(next_segment)
        if group:
            kwargs = {'obj': group}
            group_handler = Group(self.context, self.request, **kwargs)
            return group_handler.handle_subpath(subpath[1:])

        raise UnknownEndpoint(f"Unknown sub-endpoint: {next_segment}")

    @check_methods(methods=['GET'])
    def reply(self):
        raise NotImplementedError("This endpoint is not implemented.")
