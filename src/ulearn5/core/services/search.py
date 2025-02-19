# -*- coding: utf-8 -*-
import logging

from minimal.core.services import UnknownEndpoint, check_methods, check_roles
from plone import api
from plone.restapi.services import Service

logger = logging.getLogger(__name__)


class Search(Service):
    """
    - Endpoint: @api/communities/{community}/search
    - Method: GET
        Optional params:
            - q: (str) Text.
        Returns navigation for the required context

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
    @check_roles(roles=['Member', 'Manager', 'Api'])
    def reply(self):
        """ Returns navigation for required context. """
        path = self.get_physical_path()
        text = self.request.form.get('q', None)
        result = []

        if text:
            text = self.parse_text(text)
            brains = self.get_brains(path, text)

            for brain in brains:
                obj = brain.getObject()
                result.append({
                    'id': obj.id,
                    'title': obj.title,
                    'url': brain.getURL(),
                    'path': obj.absolute_url_path(),
                    'type': obj.Type(),
                    'state': brain.review_state if brain.review_state else None
                })

        return {"data": result, "code": 200}

    def get_physical_path(self):
        portal = api.portal.get()
        return '/'.join(portal.getPhysicalPath()
                        ) + '/' + self.request.form.pop('community', None) + '/documents'

    def get_brains(self, path, text):
        query = {
            'path': {'query': path},
            'SearchableText': text,
            'sort_order': 'ascending',
            'sort_on': 'sortable_title',
        }
        return api.content.find(**query)

    def parse_text(self, text):
        multispace = '\u3000'.encode('utf-8')

        for char in ('?', '-', '+', '*', multispace):
            text = text.replace(char, ' ')

        text = text.split()
        text = " AND ".join(text)
        text = self.quote_bad_chars(text) + '*'

    def quotestring(self, s):
        return '"%s"' % s

    def quote_bad_chars(self, s):
        bad_chars = ["(", ")"]
        for char in bad_chars:
            s = s.replace(char, self.quotestring(char))
        return s
