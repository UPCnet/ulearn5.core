# -*- coding: utf-8 -*-
import logging

from plone.restapi.services import Service
from ulearn5.core.services import UnknownEndpoint, check_methods
from ulearn5.core.utils import get_or_initialize_annotation
from repoze.catalog.query import Eq
from souper.soup import get_soup

logger = logging.getLogger(__name__)


class GroupCommunities(Service):
    """
    - Endpoint: @api/groups/{group}/communities
    - Method: GET
        Returns information about the communities of a group

    - Subpaths allowed: NO
    """

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request
        self.obj = kwargs.get('obj', None)

    def handle_subpath(self, subpath):
        """ Function used to spread the request to the corresponding subpath """
        if subpath:
            return UnknownEndpoint(f'Unknown sub-endpoint: {"/".join(subpath)}')

        return self.reply()

    @check_methods(methods=['GET'])
    def reply(self):
        """ Returns navigation for required context. """
        records = self.get_records()
        result = []
        for record in records:
            users = [user['id'] for user in record.attrs['acl']['users']]
            result.append(dict(
                url=record.attrs['hash'],
                groups=record.attrs['groups'],
                users=users,
                path=record.attrs['path'],
            ))
        return {"data": result, "code": 200}

    def get_records(self):
        portal = api.portal.get()
        soup = get_soup('communities_acl', portal)
        records = [r for r in soup.query(Eq('groups', self.params['group']))]
        return records
