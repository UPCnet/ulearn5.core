# -*- coding: utf-8 -*-
import logging

from plone import api
from plone.restapi.services import Service
from ulearn5.core.services import UnknownEndpoint, check_methods
from ulearn5.core.services.link import Link

logger = logging.getLogger(__name__)


class Links(Service):
    """
    - Endpoint: @api/links
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
        # May be an available language? -> Delegate to Link
        if self.is_language_available(next_segment):
            kwargs = {'lang': next_segment}
            link_handler = Link(self.context, self.request, **kwargs)
            return link_handler.handle_subpath(subpath[1:])

        raise UnknownEndpoint(f"Language not installed: {next_segment}")

    @check_methods(methods=['GET'])
    def reply(self):
        raise NotImplementedError("This endpoint is not implemented.")

    def is_language_available(self, language):
        portal_langs = api.portal.get_tool('portal_languages')
        available_langs = portal_langs.getSupportedLanguages()
        return language in available_langs
