# -*- coding: utf-8 -*-
import logging

from plone.restapi.services import Service
from ulearn5.core.services import UnknownEndpoint, check_methods
from ulearn5.core.utils import get_or_initialize_annotation

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
            users = [user['id'] for user in record.get('acl', {}).get('users', [])]

            result.append({
                'url': record.get('hash'),
                'groups': record.get('groups'),
                'users': users,
                'path': record.get('path')
            })
        return {"data": result, "code": 200}
    
    def get_records(self):
        communities_acl = get_or_initialize_annotation('communities_acl', {})
        return [
            record 
            for record in communities_acl.values() 
            if self.obj.id in record.get('groups', [])
        ]
