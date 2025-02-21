# -*- coding: utf-8 -*-
import logging

from plone import api
from plone.restapi.services import Service
from ulearn5.core.services import UnknownEndpoint, check_methods, check_roles

logger = logging.getLogger(__name__)


class Folders(Service):
    """
    - Endpoint: @api/folders
    - Method: GET
        Optional params:
            - path: (str) Path to the folder to retrieve.
        Returns navigation for required context

    - Subpaths allowed: NO
    """

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request
        self.path = kwargs.get('path', None)

    def handle_subpath(self, subpath):
        """ Function used to spread the request to the corresponding subpath """
        if subpath:
            return UnknownEndpoint(f'Unknown sub-endpoint: {"/".join(subpath)}')

        return self.reply()

    @check_methods(methods=['GET'])
    @check_roles(roles=['Member', 'Manager', 'Api'])
    def reply(self):
        folder_path = self.get_folder_path()
        brains = self.get_brains(folder_path)
        results = []
        results = [self.get_folder_from_object(brain) for brain in brains]
        return {"data": results, "code": 200}

    def get_folder_path(self):
        portal = api.portal.get()
        folder_path = '/'.join(portal.getPhysicalPath())
        if 'path' in self.request.form:
            folder_path = self.requst.form.get('path')

        return folder_path

    def get_brains(self, folder_path):
        query = {
            'path': {'query': folder_path, 'depth': 1},
            'review_state': ['private', 'intranet', 'published'],
            'sort_order': 'ascending',
            'sort_on': 'sortable_title',
        }
        return api.content.find(**query)

    def get_folder_from_object(self, brain):
        obj = brain.getObject()
        obj_url = brain.getURL()

        internal = True
        type_next_obj = None
        if obj.portal_type == 'Link':
            if 'resolveuid' in obj.remoteUrl:
                uid = obj.remoteUrl.split('/resolveuid/')[1]
                next_obj = api.content.get(UID=uid)
                type_next_obj = next_obj.Type()
                obj_url = next_obj.absolute_url()
            else:
                obj_url = obj.remoteUrl
                internal = False
        elif obj.portal_type == 'External Content':
            obj_url = obj.absolute_url() + '/@@download/' + obj.filename

        return {
            'absolute_url': obj_url,
            'description': obj.Description(),
            'id': obj.id,
            'external_url': not internal,
            'path': '/'.join(obj.getPhysicalPath()),
            'portal_type': obj.portal_type,
            'state': brain.review_state,
            'title': obj.title,
            'type_when_follow_url': type_next_obj,
            'uid': obj.UID()
        }
